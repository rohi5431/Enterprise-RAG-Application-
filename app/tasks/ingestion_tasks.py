"""
Celery tasks for document ingestion pipeline
"""
from __future__ import annotations

import logging
from typing import Optional

from celery import Task
from tenacity import retry, stop_after_attempt, wait_exponential

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class BaseIngestionTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("task_failed", task_id=task_id, error=str(exc))
        # Update document status to failed
        try:
            doc_id = args[0] if args else kwargs.get("doc_id")
            if doc_id:
                from app.db.session import get_db_context
                from app.repositories.document_repository import DocumentRepository
                with get_db_context() as db:
                    DocumentRepository(db).update_status(
                        doc_id, "failed", error_message=str(exc)
                    )
        except Exception:
            pass


@celery_app.task(
    bind=True,
    base=BaseIngestionTask,
    name="app.tasks.ingestion_tasks.ingest_document_task",
    max_retries=3,
    default_retry_delay=60,
)
def ingest_document_task(self, doc_id: int, file_path: str, file_type: str) -> dict:
    """
    Full document ingestion pipeline:
    Load → Chunk → Embed → Store in Qdrant → Update DB
    """
    logger.info("ingest_start", doc_id=doc_id, file_path=file_path)

    try:
        from app.db.session import get_db_context
        from app.repositories.document_repository import DocumentRepository
        from rag.ingestion.document_loader import DocumentLoader
        from rag.chunking.text_chunker import TextChunker
        from rag.embeddings.bge_embedder import BGEEmbedder
        from rag.vectorstore.qdrant_store import QdrantVectorStore
        from app.core.config import settings

        with get_db_context() as db:
            repo = DocumentRepository(db)
            repo.update_status(doc_id, "processing")

        # 1. Load document
        loader = DocumentLoader()
        pages = loader.load(file_path, file_type)
        full_text = "\n\n".join(p["text"] for p in pages)

        # 2. Chunk
        chunker = TextChunker(
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )
        chunks = chunker.chunk(full_text, doc_id=doc_id, pages=pages)

        if not chunks:
            raise ValueError("No chunks extracted from document")

        # 3. Embed
        embedder = BGEEmbedder()
        texts = [c["text"] for c in chunks]
        embeddings = embedder.embed_batch(texts)

        # 4. Store in Qdrant
        store = QdrantVectorStore()
        store.ensure_collection()
        point_ids = store.upsert_chunks(doc_id=doc_id, chunks=chunks, embeddings=embeddings)

        # 5. Update DB
        with get_db_context() as db:
            repo = DocumentRepository(db)
            # Save chunk records
            chunk_records = repo.create_chunks_batch([
                {
                    "document_id": doc_id,
                    "text": c["text"],
                    "sequence_number": c["sequence_number"],
                    "page_number": c.get("page_number"),
                    "token_count": c.get("token_count", 0),
                    "tags": c.get("tags", []),
                    "chunk_metadata": c.get("metadata", {}),
                }
                for c in chunks
            ])
            # Link Qdrant IDs
            for chunk_rec, pid in zip(chunk_records, point_ids):
                repo.update_chunk_qdrant_id(chunk_rec.id, str(pid))
            # Update document
            repo.update_status(doc_id, "success")
            repo.update_chunks_count(doc_id, len(chunks), len(point_ids))

            doc = repo.get(doc_id)
            if doc:
                doc.content = full_text[:50000]  # store first 50k chars
                doc.content_length = len(full_text)
                doc.page_count = len(pages)
                db.commit()

        logger.info("ingest_complete", doc_id=doc_id, chunks=len(chunks))
        return {"doc_id": doc_id, "chunks": len(chunks), "vectors": len(point_ids), "status": "success"}

    except Exception as exc:
        logger.error("ingest_error", doc_id=doc_id, error=str(exc))
        try:
            with get_db_context() as db:
                DocumentRepository(db).update_status(doc_id, "failed", error=str(exc))
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
