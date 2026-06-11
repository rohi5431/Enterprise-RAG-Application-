from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.user_repository import UserRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.models.document import Document
from sqlalchemy import desc


class AdminService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.analytics = AnalyticsRepository(db)
        self.users = UserRepository(db)
        self.feedback = FeedbackRepository(db)

    def get_platform_stats(self) -> dict:
        return self.analytics.get_platform_stats()

    def get_users(
        self, skip: int = 0, limit: int = 50
    ) -> dict:
        users = self.users.get_users_with_activity(skip, limit)
        total = self.users.total_count()
        return {"users": users, "total": total, "page": skip // limit + 1, "page_size": limit}

    def get_documents(
        self, skip: int = 0, limit: int = 50, status: str | None = None
    ) -> dict:
        q = self.db.query(Document)
        if status:
            q = q.filter(Document.processing_status == status)
        total = q.count()
        docs = q.order_by(desc(Document.created_at)).offset(skip).limit(limit).all()
        return {
            "documents": docs,
            "total": total,
            "page": skip // limit + 1,
            "page_size": limit,
        }

    def get_queries(
        self, skip: int = 0, limit: int = 50, days: int = 30
    ) -> dict:
        from app.models.query_log import QueryLog
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(days=days)
        q = self.db.query(QueryLog).filter(QueryLog.created_at >= since)
        total = q.count()
        logs = q.order_by(desc(QueryLog.created_at)).offset(skip).limit(limit).all()
        return {"queries": logs, "total": total}

    def get_feedback(
        self, skip: int = 0, limit: int = 50
    ) -> dict:
        feedbacks = self.feedback.list_feedback(skip, limit)
        stats = self.feedback.get_stats()
        return {"feedback": feedbacks, "stats": stats}

    def get_query_analytics(self, days: int = 30) -> dict:
        stats = self.analytics.get_query_stats(days)
        top_docs = self.analytics.get_top_documents(10)
        return {"query_stats": stats, "top_documents": top_docs}
