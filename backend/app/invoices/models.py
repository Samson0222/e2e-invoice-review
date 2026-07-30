"""SQLite persistence model for a saved document review."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index(
            "ix_documents_duplicate_key",
            "normalized_vendor_name",
            "normalized_invoice_number",
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    original_filename: Mapped[str]
    content_type: Mapped[str]
    stored_filename: Mapped[str]
    document_type: Mapped[str | None] = mapped_column(default=None)
    classification_confidence: Mapped[float | None] = mapped_column(default=None)
    classification_reasoning: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str]
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    normalized_vendor_name: Mapped[str | None] = mapped_column(default=None)
    normalized_invoice_number: Mapped[str | None] = mapped_column(default=None)
    field_sources: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    conflicts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    gl_classification: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    correction_email_draft: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    error_message: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
