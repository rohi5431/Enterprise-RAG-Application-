"""
Advanced RAG Pipeline
======================
Replaces the old single-retriever pipeline with the full
Query Expansion → Hybrid Retrieval → Reranking → LLM flow.

Flow
----
  Question
    ↓
  QueryExpander        (produces N expanded queries)
    ↓
  VectorRetriever  ─┐
                    ├─ HybridRetriever (fuses via RRF)
  BM25Retriever   ─┘
    ↓
  CrossEncoderReranker
    ↓
  Top-K Chunks + Citations
    ↓
  OllamaClient
    ↓
  Answer + Sources

The pipeline is fully injectable: pass custom components to ``__init__``
for testing or to swap out models.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, List, Optional

from app.core.config import settings
from rag.llm.ollama_client import OllamaClient
from rag.llm.prompt_templates import get_rag_prompt
from rag.retrieval.bm25_manager import get_bm25
from rag.memory.conversation_memory import ConversationMemory
from rag.prompts.prompt_builder import PromptBuilder
from rag.retrieval.analytics import RetrievalEvent, get_analytics
from rag.retrieval.bm25_retriever import BM25Retriever
from rag.retrieval.hybrid_retriever import HybridRetriever
from rag.retrieval.query_expander import QueryExpander
from rag.retrieval.schemas import (
    MetadataFilter,
    RetrievalMode,
    RetrievalRequest,
    RetrievalResult,
    RetrievedChunk,
)
from rag.retrieval.vector_retriever import VectorRetriever
from rag.reranking.cross_encoder_reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


class AdvancedRAGPipeline:
    """
    Production-grade RAG pipeline with hybrid retrieval.

    Parameters
    ----------
    query_expander:
        :class:`~rag.retrieval.query_expander.QueryExpander` instance.
    hybrid_retriever:
        :class:`~rag.retrieval.hybrid_retriever.HybridRetriever` instance.
    llm:
        :class:`~rag.llm.ollama_client.OllamaClient` instance.
    mode:
        Default retrieval mode.  Can be overridden per-query.
    """

    def __init__(
        self,
        query_expander: Optional[QueryExpander] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        llm: Optional[OllamaClient] = None,
        mode: RetrievalMode = RetrievalMode.HYBRID_RERANKED,
    ) -> None:
        self._expander = query_expander or QueryExpander(n_expansions=3)
        self._retriever = hybrid_retriever or HybridRetriever()
        self._llm = llm or OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )
        self._default_mode = mode
        self._analytics = get_analytics()
        
        # Conversation memory
        self._memory = ConversationMemory()
        self._prompt_builder = PromptBuilder()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run(
        self,
        query: str,
        *,
        top_k: int = 10,
        final_top_k: int = 3,
        mode: Optional[RetrievalMode] = None,
        filters: Optional[MetadataFilter] = None,
        expand_query: bool = True,
    ) -> Dict:
        """
        Execute the full pipeline for *query*.

        Parameters
        ----------
        query:
            The raw user question.
        top_k:
            Candidates fetched per retriever.
        final_top_k:
            Chunks passed to the LLM (after reranking).
        mode:
            Override the default retrieval mode.
        filters:
            Metadata filter applied to Qdrant and BM25.
        expand_query:
            Whether to run query expansion.

        Returns
        -------
        dict with keys: query, answer, sources, retrieval_meta
        """
        query_id = str(uuid.uuid4())[:8]
        t_total = time.perf_counter()
        error_msg: Optional[str] = None

        logger.info("[%s] Pipeline start: %r", query_id, query[:80])

        # ── 1. Query expansion ─────────────────────────────────────────
        expanded: List[str] = [query]
        if expand_query:
            try:
                expanded = self._expander.expand(query)
                print("\n===== QUERY EXPANSION =====")

                for i, q in enumerate(expanded):
                    print(f"{i+1}. {q}")
                logger.debug("[%s] Expanded to %d queries", query_id, len(expanded))
            except Exception as exc:
                logger.warning("[%s] Query expansion failed: %s", query_id, exc)

        # ── 2. Build retrieval request ─────────────────────────────────
        print("\n===== RAG PIPELINE =====")
        print("expand_query =", expand_query)
        request = RetrievalRequest(
            query=query,
            mode=mode or self._default_mode,
            top_k=top_k,
            final_top_k=final_top_k,
            filters=filters,
            expand_query=expand_query,
            expanded_queries=expanded,
        )

        # ── 3. Hybrid retrieval (vector + BM25 + rerank) ───────────────
        try:
            result: RetrievalResult = self._retriever.retrieve(request)

            print("\n===== RETRIEVAL RESULT =====")
            print("VECTOR CANDIDATES =", result.vector_candidates)
            print("BM25 CANDIDATES =", result.bm25_candidates)
            print("CHUNKS AFTER RETRIEVAL =", len(result.chunks))
            
            chunks = result.chunks

            print("\n===== CHUNKS FOUND =====")
            print("COUNT =", len(chunks))
            
            for i, c in enumerate(chunks[:10]):
               print(f"\nChunk {i+1}")
               print("Source =", c.retriever_source)
               print("Doc =", c.doc_id)
               print("Vector =", c.vector_score)
               print("BM25 =", c.bm25_score)
               print("Rerank =", c.rerank_score)
               print("Final =", c.score)
               print("Text =", c.text[:300])
        except Exception as exc:
            logger.error("[%s] Retrieval failed: %s", query_id, exc)
            error_msg = str(exc)
            result = RetrievalResult(
                query=query,
                expanded_queries=expanded,
                chunks=[],
                mode=request.mode,
            )
            chunks = []

        # ── 4. Build context for LLM ───────────────────────────────────
        if not chunks:
            answer = "I couldn't find relevant information to answer your question."
            sources = []
        else: 
            prompt = self._prompt_builder.build(
                query=query,
                chunks=chunks,
                conversation_history=self._memory.get_context(),
            )

            try:
                # print("\n===== CONTEXT SENT TO OLLAMA =====")
                print("\n===== MEMORY =====")
                print(self._memory.get_context())
                
                print("\n===== PROMPT SENT TO OLLAMA =====")
                print(prompt[:5000])
                print("\nPROMPT LENGTH =", len(prompt))
                print("\n===== MEMORY =====")
                print(self._memory.get_context())
                answer = self._llm.generate(prompt)

            #    self._memory.add_user(query)
            #    self._memory.add_assistant(answer)

                # Save conversation
                self._memory.add_user(query)
                self._memory.add_assistant(answer)
            except Exception as exc:
                logger.error("[%s] LLM generation failed: %s", query_id, exc)
                answer = f"Error generating answer: {exc}"
                error_msg = str(exc)

            sources = self._build_sources(chunks)

        total_ms = (time.perf_counter() - t_total) * 1000

        # ── 5. Record analytics ────────────────────────────────────────
        event = RetrievalEvent(
            query=query,
            mode=str(request.mode),
            user_id=filters.user_id if filters else None,
            vector_candidates=result.vector_candidates,
            bm25_candidates=result.bm25_candidates,
            chunks_returned=len(chunks),
            latency_total_ms=total_ms,
            latency_breakdown=result.latency_ms,
            tags_filter=filters.tags if (filters and filters.tags) else [],
            expanded_query_count=len(expanded) - 1,
            error=error_msg,
        )
        self._analytics.record(event)

        logger.info(
            "[%s] Pipeline complete: %d chunks | %.0f ms",
            query_id, len(chunks), total_ms,
        )

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "num_sources": len(sources),
            "retrieval_meta": {
                "mode": str(request.mode),
                "expanded_queries": expanded[1:],  # exclude original
                "vector_candidates": result.vector_candidates,
                "bm25_candidates": result.bm25_candidates,
                "chunks_after_fusion": result.chunks_after_fusion,
                "chunks_after_rerank": result.chunks_after_rerank,
                "latency_ms": result.latency_ms,
                "total_latency_ms": round(total_ms, 2),
            },
        }

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_context(chunks: List[RetrievedChunk]) -> str:
        """Format chunks into a numbered context block."""
        parts = []
        for i, chunk in enumerate(chunks, start=1):
            source = chunk.doc_title or chunk.doc_filename or f"Doc {chunk.doc_id}"
            parts.append(f"[{i}] ({source})\n{chunk.text}")
        context = "\n\n---\n\n".join(parts)
        return context[:1000]

    @staticmethod
    def _build_sources(chunks: List[RetrievedChunk]) -> List[Dict]:
        """Convert RetrievedChunk list to serialisable citation dicts."""
        return [
            {
                "citation_number": i + 1,
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "doc_title": chunk.doc_title,
                "doc_filename": chunk.doc_filename,
                "text_snippet": chunk.text[:300] + ("…" if len(chunk.text) > 300 else ""),
                "score": round(chunk.score, 4),
                "rerank_score": round(chunk.rerank_score, 4) if chunk.rerank_score else None,
                "vector_score": round(chunk.vector_score, 4) if chunk.vector_score else None,
                "bm25_score": round(chunk.bm25_score, 4) if chunk.bm25_score else None,
                "page_number": chunk.page_number,
                "tags": chunk.tags,
                "retriever_source": chunk.retriever_source,
            }
            for i, chunk in enumerate(chunks)
        ]
    
    def run_stream(
        self,
        query: str,
):    
        expanded = [query]
    
        try:
            expanded = self._expander.expand(query)
        except Exception as exc:
            logger.warning("Query expansion failed: %s", exc)
    
        request = RetrievalRequest(
            query=query,
            mode=self._default_mode,
            top_k=5,
            final_top_k=3,
            expanded_queries=expanded,
        )
    
        result = self._retriever.retrieve(request)
        chunks = result.chunks
    
        if not chunks:
            yield "No relevant information found."
            return
    
        prompt = self._prompt_builder.build(
            query=query,
            chunks=chunks,
            conversation_history=self._memory.get_context(),
        )
    
        full_answer = ""
    
        for token in self._llm.generate_stream(prompt):
            full_answer += token
            yield token
    
        self._memory.add_user(query)
        self._memory.add_assistant(full_answer)
    

# ---------------------------------------------------------------------------
# Module-level singleton + legacy compatibility
# ---------------------------------------------------------------------------

_pipeline: Optional[AdvancedRAGPipeline] = None


def get_rag_pipeline(
    bm25_retriever: Optional[BM25Retriever] = None,
) -> AdvancedRAGPipeline:
    """Return (or create) the process-wide RAG pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        vector = VectorRetriever()
        from rag.retrieval.bm25_manager import get_bm25

        bm25 = bm25_retriever or get_bm25()
        reranker = CrossEncoderReranker()
        hybrid = HybridRetriever(
            vector_retriever=vector,
            bm25_retriever=bm25,
            reranker=reranker,
        )
        _pipeline = AdvancedRAGPipeline(hybrid_retriever=hybrid)
    return _pipeline


def run_rag(
    query: str,
    filters: Optional[MetadataFilter] = None,
    mode: Optional[RetrievalMode] = None,
    expand_query: bool = True,
) -> Dict:
    """
    Legacy-compatible entry point — wraps AdvancedRAGPipeline.run().
    """
    return get_rag_pipeline().run(query, filters=filters, mode=mode,expand_query=expand_query)

def run_rag_stream(
    query: str,
):
    yield from get_rag_pipeline().run_stream(query)