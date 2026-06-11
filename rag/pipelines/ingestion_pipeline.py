"""
Standalone Ingestion Pipeline — utility functions to ingest documents from files directly
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Any

from rag.ingestion.document_loader import DocumentLoader
from rag.chunking.text_chunker import TextChunker
from rag.embeddings.bge_embedder import BGEEmbedder
from rag.vectorstore.qdrant_store import QdrantVectorStore
from app.core.config import settings

logger = logging.getLogger(__name__)


def ingest_document(file_path: str, doc_type: str = "pdf") -> Dict[str, Any]:
    """Ingest a single document and store its embeddings in Qdrant (standalone utility)."""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")

        # 1. Load document
        loader = DocumentLoader()
        pages = loader.load(file_path, doc_type)
        full_text = "\n\n".join(p["text"] for p in pages)

        if not full_text.strip():
            raise ValueError("Document is empty or contains no extractable text")

        # 2. Chunk document
        chunker = TextChunker(
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )
        chunks = chunker.chunk(full_text, doc_id=0, pages=pages)

        if not chunks:
            raise ValueError("Could not extract any chunks from the document")

        # 3. Generate embeddings
        embedder = BGEEmbedder()
        texts = [c["text"] for c in chunks]
        embeddings = embedder.embed_batch(texts)

        # 4. Store in Qdrant
        store = QdrantVectorStore()
        store.ensure_collection()
        point_ids = store.upsert_chunks(doc_id=0, chunks=chunks, embeddings=embeddings)

        return {
            "status": "success",
            "path": file_path,
            "chunks_created": len(chunks),
            "chunks_stored": len(point_ids),
            "text_length": len(full_text),
        }

    except Exception as e:
        logger.error("Failed to ingest document %s: %s", file_path, e)
        return {
            "status": "error",
            "path": file_path,
            "error": str(e),
        }


def ingest_multiple_documents(file_paths: List[str], doc_type: str = "pdf") -> List[Dict[str, Any]]:
    """Ingest a list of documents in batch."""
    results = []
    for path in file_paths:
        result = ingest_document(path, doc_type)
        results.append(result)
    return results