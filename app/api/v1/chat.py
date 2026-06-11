from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, CitationResponse, SessionCreate, SessionResponse, MessageResponse
from app.services.analytics_service import AnalyticsService
from app.services.conversation_service import ConversationService
from app.services.feedback_service import FeedbackService
from rag.pipelines.rag_pipeline import get_rag_pipeline
from rag.retrieval.schemas import MetadataFilter, RetrievalMode

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
def send_message(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Multi-turn RAG chat endpoint.
    - Loads or creates a session
    - Builds conversation context
    - Runs hybrid RAG pipeline
    - Saves turn to DB
    - Pre-allocates feedback slot
    - Logs analytics
    """
    t_start = time.perf_counter()
    conv_svc = ConversationService(db)
    feedback_svc = FeedbackService(db)
    analytics_svc = AnalyticsService(db)

    # 1. Session management
    session = conv_svc.get_or_create_session(
        user_id=current_user.id,
        session_id=req.session_id,
    )

    # 2. Build conversation context
    context_prefix = conv_svc.build_context_prompt(session, req.query)
    enriched_query = f"{context_prefix}\n\nCurrent question: {req.query}" if context_prefix else req.query

    # 3. Build metadata filters
    filters = MetadataFilter(user_id=current_user.id)
    if req.filters:
        if "doc_ids" in req.filters:
            filters.doc_ids = req.filters["doc_ids"]
        if "tags" in req.filters:
            filters.tags = req.filters["tags"]

    # 4. Run RAG pipeline
    t_rag = time.perf_counter()
    cache_hit = False
    try:
        pipeline = get_rag_pipeline()
        result = pipeline.run(
            query=enriched_query,
            top_k=req.top_k,
            final_top_k=req.final_top_k,
            filters=filters,
        )
    except Exception as exc:
        analytics_svc.record_query(
            query_text=req.query,
            user_id=current_user.id,
            session_id=session.id,
            total_latency_ms=(time.perf_counter() - t_start) * 1000,
            success=False,
            error_message=str(exc),
        )
        raise

    t_rag_done = time.perf_counter()
    meta = result.get("retrieval_meta", {})
    retrieval_ms = meta.get("latency_ms", {}).get("total_ms", 0.0)
    llm_ms = meta.get("llm_ms", 0.0)
    total_ms = (t_rag_done - t_start) * 1000

    # 5. Build citations
    sources = result.get("sources", [])
    citations = [
        CitationResponse(
            citation_number=s["citation_number"],
            chunk_id=str(s.get("chunk_id", "")),
            doc_id=s.get("doc_id", 0),
            doc_title=s.get("doc_title"),
            doc_filename=s.get("doc_filename"),
            filename=s.get("doc_filename"),
            page_number=s.get("page_number"),
            text_snippet=s.get("text_snippet", ""),
            score=s.get("score", 0.0),
            rerank_score=s.get("rerank_score"),
        )
        for s in sources
    ]

    # Confidence score from top rerank score
    confidence = 0.0
    if sources:
        top = sources[0]
        confidence = top.get("rerank_score") or top.get("score", 0.0)

    # 6. Pre-allocate feedback
    feedback_id = feedback_svc.create_slot(
        user_id=current_user.id,
        session_id=session.id,
        message_id=None,
        query_text=req.query,
        answer_text=result.get("answer", ""),
    )

    # 7. Save conversation turn
    msg = conv_svc.save_turn(
        session=session,
        query=req.query,
        answer=result.get("answer", ""),
        sources=[c.model_dump() for c in citations],
        feedback_id=feedback_id,
        retrieval_ms=int(retrieval_ms),
        llm_ms=int(llm_ms),
        confidence=int(confidence * 100),
    )

    # 8. Log analytics
    analytics_svc.record_query(
        query_text=req.query,
        user_id=current_user.id,
        session_id=session.id,
        retrieval_latency_ms=retrieval_ms,
        llm_latency_ms=llm_ms,
        total_latency_ms=total_ms,
        rerank_latency_ms=meta.get("latency_ms", {}).get("rerank_ms", 0.0),
        num_sources=len(sources),
        vector_candidates=meta.get("vector_candidates", 0),
        bm25_candidates=meta.get("bm25_candidates", 0),
        top_score=float(confidence),
        cache_hit=cache_hit,
        success=True,
        retrieval_mode=meta.get("mode"),
        expanded_queries=meta.get("expanded_queries", []),
    )

    return ChatResponse(
        answer=result.get("answer", ""),
        query=req.query,
        session_id=session.id,
        message_id=msg.id,
        feedback_id=feedback_id,
        confidence=round(confidence, 4),
        citations=citations,
        num_sources=len(citations),
        retrieval_latency_ms=retrieval_ms,
        llm_latency_ms=llm_ms,
        total_latency_ms=round(total_ms, 2),
        cache_hit=cache_hit,
    )


@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(
    req: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    session = ConversationService(db).get_or_create_session(
        user_id=current_user.id, title=req.title
    )
    return session


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all chat sessions for the current user."""
    return ConversationService(db).get_user_sessions(current_user.id, skip, limit)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all messages in a session."""
    return ConversationService(db).get_session_messages(session_id, current_user.id)
