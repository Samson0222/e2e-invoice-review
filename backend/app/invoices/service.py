"""Orchestrates upload -> pipeline -> validation -> persistence, plus Maya's review actions:
field corrections, GL account selection, and the approve/reject decision."""

import logging
import uuid
from pathlib import Path
from typing import Any

from app.accounting.catalog import GL_ACCOUNT_NAMES
from app.correction_email.eligibility import supplier_fixable_issues
from app.correction_email.schemas import CorrectionEmailDraft
from app.invoices.models import DocumentRecord
from app.invoices.repository import DocumentRepository, normalize_duplicate_key
from app.invoices.schemas import DocumentCorrectionRequest, ValidationIssue
from app.invoices.validation import has_blocking_errors, validate_invoice, validate_receipt
from app.pipeline import PipelineResult, RawDocument, Step
from app.providers.azure_openai_correction_email import CorrectionEmailDrafter
from app.schemas.common import Money
from app.schemas.invoice import Invoice
from app.schemas.receipt import Receipt

logger = logging.getLogger(__name__)

_DECIDED_STATUSES = {"approved", "rejected"}


class DocumentNotFoundError(RuntimeError):
    """Raised when no saved review exists for the given id."""


class DocumentProcessingError(RuntimeError):
    """Raised when the pipeline fails to process an uploaded document."""


class DocumentReviewConflictError(RuntimeError):
    """Raised when an action is not allowed given the document's current status."""


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        upload_dir: Path,
        pipeline: Step[RawDocument, PipelineResult],
        correction_email_drafter: CorrectionEmailDrafter,
        *,
        expected_customer_name: str,
        expected_customer_vat_id: str,
        min_confidence: float,
    ) -> None:
        self._repository = repository
        self._upload_dir = upload_dir
        self._pipeline = pipeline
        self._correction_email_drafter = correction_email_drafter
        self._expected_customer_name = expected_customer_name
        self._expected_customer_vat_id = expected_customer_vat_id
        self._min_confidence = min_confidence

    def process(
        self,
        *,
        original_filename: str,
        content_type: str,
        content: bytes,
        suffix: str,
    ) -> DocumentRecord:
        document_id = str(uuid.uuid4())
        stored_filename = f"{document_id}{suffix}"
        (self._upload_dir / stored_filename).write_bytes(content)

        try:
            result = self._pipeline.run(
                RawDocument(filename=original_filename, file_bytes=content)
            )
        except Exception as error:
            logger.exception("Pipeline failed for %s", original_filename)
            record = DocumentRecord(
                id=document_id,
                original_filename=original_filename,
                content_type=content_type,
                stored_filename=stored_filename,
                status="failed",
                error_message=str(error),
            )
            self._repository.add(record)
            raise DocumentProcessingError(str(error)) from error

        vendor_name, invoice_number = _duplicate_key_fields(result.data)
        is_duplicate = bool(
            vendor_name
            and invoice_number
            and self._repository.duplicate_exists(vendor_name, invoice_number)
        )
        issues = self._validate(result.data, is_duplicate=is_duplicate)

        record = DocumentRecord(
            id=document_id,
            original_filename=original_filename,
            content_type=content_type,
            stored_filename=stored_filename,
            document_type=result.document_type,
            classification_confidence=result.classification_confidence,
            classification_reasoning=result.classification_reasoning,
            status="needs_review" if has_blocking_errors(issues) else "ready",
            data=result.data.model_dump(mode="json"),
            normalized_vendor_name=normalize_duplicate_key(vendor_name) if vendor_name else None,
            normalized_invoice_number=(
                normalize_duplicate_key(invoice_number) if invoice_number else None
            ),
            field_sources=dict(result.field_sources),
            conflicts=[conflict.model_dump(mode="json") for conflict in result.conflicts],
            issues=[issue.model_dump(mode="json") for issue in issues],
            gl_classification=(
                result.gl_classification.model_dump(mode="json")
                if result.gl_classification
                else None
            ),
        )
        return self._repository.add(record)

    def _validate(self, data: Invoice | Receipt, *, is_duplicate: bool) -> list[ValidationIssue]:
        if isinstance(data, Invoice):
            return validate_invoice(
                data,
                expected_customer_name=self._expected_customer_name,
                expected_customer_vat_id=self._expected_customer_vat_id,
                min_confidence=self._min_confidence,
                is_duplicate=is_duplicate,
            )
        return validate_receipt(data, min_confidence=self._min_confidence)

    def list(self) -> list[DocumentRecord]:
        return self._repository.list()

    def get(self, document_id: str) -> DocumentRecord:
        record = self._repository.get(document_id)
        if record is None:
            raise DocumentNotFoundError(f"No document review found for id {document_id!r}")
        return record

    def correct(self, document_id: str, corrections: DocumentCorrectionRequest) -> DocumentRecord:
        record = self.get(document_id)
        if record.status in _DECIDED_STATUSES:
            raise DocumentReviewConflictError("A decided document cannot be edited.")
        if record.data is None or record.document_type is None:
            raise DocumentReviewConflictError("This review has no extracted data to correct.")

        changes = corrections.model_dump(exclude_unset=True)
        model_type = Invoice if record.document_type == "invoice" else Receipt
        data = model_type.model_validate(record.data)
        updated_fields, touched = _apply_corrections(data, changes)
        data = data.model_copy(update=updated_fields)

        field_sources = dict(record.field_sources)
        for field_name in touched:
            field_sources[field_name] = "human"

        vendor_name, invoice_number = _duplicate_key_fields(data)
        is_duplicate = bool(
            vendor_name
            and invoice_number
            and self._repository.duplicate_exists(vendor_name, invoice_number, exclude_id=record.id)
        )
        issues = self._validate(data, is_duplicate=is_duplicate)

        record.data = data.model_dump(mode="json")
        record.field_sources = field_sources
        record.normalized_vendor_name = (
            normalize_duplicate_key(vendor_name) if vendor_name else None
        )
        record.normalized_invoice_number = (
            normalize_duplicate_key(invoice_number) if invoice_number else None
        )
        record.issues = [issue.model_dump(mode="json") for issue in issues]
        record.status = "needs_review" if has_blocking_errors(issues) else "ready"
        record.correction_email_draft = None
        return self._repository.add(record)

    def draft_correction_email(self, document_id: str) -> CorrectionEmailDraft:
        record = self.get(document_id)
        if record.data is None:
            raise DocumentReviewConflictError("This review has no extracted data yet.")
        eligible_issues = supplier_fixable_issues(record.issues)
        if not eligible_issues:
            raise DocumentReviewConflictError("This review has no supplier-fixable issues.")
        if record.correction_email_draft is not None:
            return CorrectionEmailDraft.model_validate(record.correction_email_draft)
        draft = self._correction_email_drafter.draft(
            record.document_type, record.data, eligible_issues
        )
        record.correction_email_draft = draft.model_dump(mode="json")
        self._repository.add(record)
        return draft

    def select_gl_account(self, document_id: str, gl_account_code: str) -> DocumentRecord:
        record = self.get(document_id)
        if record.status in _DECIDED_STATUSES:
            raise DocumentReviewConflictError("A decided document cannot be edited.")
        if record.gl_classification is None:
            raise DocumentReviewConflictError("This review has no GL suggestion to override.")
        if gl_account_code not in GL_ACCOUNT_NAMES:
            raise ValueError(f"Unknown GL account: {gl_account_code}")

        gl_classification = dict(record.gl_classification)
        gl_classification["reviewer_override_code"] = gl_account_code
        record.gl_classification = gl_classification
        return self._repository.add(record)

    def decide(self, document_id: str, decision: str) -> DocumentRecord:
        record = self.get(document_id)
        if record.status in _DECIDED_STATUSES:
            raise DocumentReviewConflictError("This document already has a decision.")
        if record.status in {"failed"}:
            raise DocumentReviewConflictError("Only a completed review can receive a decision.")
        if decision == "approved":
            issues = [ValidationIssue.model_validate(item) for item in record.issues]
            if has_blocking_errors(issues):
                raise DocumentReviewConflictError("Resolve all validation errors before approval.")
            gl_code = (record.gl_classification or {}).get("reviewer_override_code") or (
                record.gl_classification or {}
            ).get("suggested_account_code")
            if gl_code not in GL_ACCOUNT_NAMES:
                raise DocumentReviewConflictError("Select a valid GL account before approval.")

        record.status = decision
        return self._repository.add(record)

    def delete(self, document_id: str) -> None:
        record = self.get(document_id)
        (self._upload_dir / record.stored_filename).unlink(missing_ok=True)
        self._repository.delete(record)


def _duplicate_key_fields(data: Invoice | Receipt) -> tuple[str | None, str | None]:
    if isinstance(data, Invoice):
        return data.vendor_name, data.invoice_id
    return None, None


def _apply_corrections(
    data: Invoice | Receipt, changes: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Map the flat correction request onto the nested Invoice/Receipt fields it touches."""
    updates: dict[str, Any] = {}
    touched: list[str] = []

    def _set(field_name: str, value: Any) -> None:
        updates[field_name] = value
        touched.append(field_name)

    new_currency = changes.get("currency_code")

    def _set_money(field_name: str, amount_key: str) -> None:
        amount_changed = amount_key in changes
        if not amount_changed and new_currency is None:
            return
        existing: Money | None = getattr(data, field_name, None)
        amount = changes[amount_key] if amount_changed else (existing.amount if existing else None)
        currency_code = new_currency if new_currency is not None else (
            existing.currency_code if existing else None
        )
        money = Money(amount=amount, currency_code=currency_code) if amount is not None else None
        _set(field_name, money)

    if isinstance(data, Invoice):
        simple_fields = (
            "vendor_name",
            "vendor_tax_id",
            "customer_name",
            "customer_tax_id",
            "invoice_id",
            "purchase_order",
        )
        for field_name in simple_fields:
            if field_name in changes:
                _set(field_name, changes[field_name])
        if "invoice_date" in changes:
            _set("invoice_date", changes["invoice_date"])
        if "due_date" in changes:
            _set("due_date", changes["due_date"])
        _set_money("subtotal", "subtotal_amount")
        _set_money("total_tax", "total_tax_amount")
        _set_money("invoice_total", "invoice_total_amount")
    else:
        if "merchant_name" in changes:
            _set("merchant_name", changes["merchant_name"])
        if "transaction_date" in changes:
            _set("transaction_date", changes["transaction_date"])
        _set_money("subtotal", "subtotal_amount")
        _set_money("total_tax", "total_tax_amount")
        _set_money("total", "total_amount")

    return updates, touched
