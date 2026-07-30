"""SQLite access for saved document reviews. No business logic lives here."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.invoices.models import DocumentRecord


def normalize_duplicate_key(value: str) -> str:
    return " ".join(value.casefold().split())


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, record: DocumentRecord) -> DocumentRecord:
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def get(self, document_id: str) -> DocumentRecord | None:
        return self._session.get(DocumentRecord, document_id)

    def list(self) -> list[DocumentRecord]:
        statement = select(DocumentRecord).order_by(DocumentRecord.created_at.desc())
        return list(self._session.scalars(statement))

    def duplicate_exists(
        self, vendor_name: str, invoice_number: str, *, exclude_id: str | None = None
    ) -> bool:
        statement = select(DocumentRecord.id).where(
            DocumentRecord.normalized_vendor_name == normalize_duplicate_key(vendor_name),
            DocumentRecord.normalized_invoice_number == normalize_duplicate_key(invoice_number),
            DocumentRecord.status != "rejected",
        )
        if exclude_id is not None:
            statement = statement.where(DocumentRecord.id != exclude_id)
        return self._session.scalars(statement).first() is not None

    def delete(self, record: DocumentRecord) -> None:
        self._session.delete(record)
        self._session.commit()
