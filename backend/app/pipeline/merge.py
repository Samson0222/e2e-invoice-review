"""Pipeline step: deterministically merge Document Intelligence's extraction with the
independent LLM extraction. Document Intelligence stays primary -- an LLM value only fills
a field DI left empty; it never replaces a DI value. Runs entirely offline, no network calls.
Fields where both extractions disagree are surfaced as conflicts, never auto-resolved."""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from app.pipeline.base import Step
from app.pipeline.models import ExtractedDocument, FieldConflict, FieldSource, MergedDocument
from app.schemas.common import Money
from app.schemas.invoice import Invoice
from app.schemas.llm_extraction import LlmExtraction
from app.schemas.receipt import Receipt

logger = logging.getLogger(__name__)


class MergeStep(Step[ExtractedDocument, MergedDocument]):
    def run(self, value: ExtractedDocument) -> MergedDocument:
        logger.info(
            "[merge] %s: filling gaps from the independent LLM extraction", value.filename
        )
        if isinstance(value.data, Invoice):
            data, sources, conflicts = _merge_invoice(value.data, value.llm_extraction)
        else:
            data, sources, conflicts = _merge_receipt(value.data, value.llm_extraction)
        logger.info(
            "[merge] %s: %d field(s) filled from the LLM, %d conflict(s)",
            value.filename,
            len(sources),
            len(conflicts),
        )
        return MergedDocument(
            filename=value.filename,
            document_type=value.document_type,
            data=data,
            classification_confidence=value.classification_confidence,
            classification_reasoning=value.classification_reasoning,
            field_sources=sources,
            conflicts=conflicts,
        )


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _normalize_identifier(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _parse_amount(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.strip().replace(",", "."))
    except InvalidOperation:
        return None


def _fill_text(
    field_name: str,
    primary: str | None,
    llm_value: str | None,
    sources: dict[str, FieldSource],
    conflicts: list[FieldConflict],
    *,
    normalize=_normalize_text,
) -> str | None:
    if primary:
        if llm_value and normalize(primary) != normalize(llm_value):
            conflicts.append(
                FieldConflict(
                    field=field_name, document_intelligence_value=primary, llm_value=llm_value
                )
            )
        return primary
    if llm_value:
        sources[field_name] = "llm_fallback"
        return llm_value
    return None


def _fill_date(
    field_name: str,
    primary: date | None,
    llm_value: str | None,
    sources: dict[str, FieldSource],
    conflicts: list[FieldConflict],
) -> date | None:
    parsed = _parse_date(llm_value)
    if primary:
        if parsed and parsed != primary:
            conflicts.append(
                FieldConflict(
                    field=field_name,
                    document_intelligence_value=primary.isoformat(),
                    llm_value=llm_value or "",
                )
            )
        return primary
    if parsed:
        sources[field_name] = "llm_fallback"
        return parsed
    return None


def _fill_money(
    field_name: str,
    primary: Money | None,
    llm_value: str | None,
    llm_currency: str | None,
    sources: dict[str, FieldSource],
    conflicts: list[FieldConflict],
) -> Money | None:
    parsed = _parse_amount(llm_value)
    if primary and primary.amount is not None:
        if parsed is not None and abs(Decimal(str(primary.amount)) - parsed) > Decimal("0.01"):
            conflicts.append(
                FieldConflict(
                    field=field_name,
                    document_intelligence_value=str(primary.amount),
                    llm_value=llm_value or "",
                )
            )
        return primary
    if parsed is None:
        return primary
    sources[field_name] = "llm_fallback"
    return Money(amount=float(parsed), currency_code=llm_currency)


def _merge_invoice(
    data: Invoice, llm: LlmExtraction
) -> tuple[Invoice, dict[str, FieldSource], list[FieldConflict]]:
    sources: dict[str, FieldSource] = {}
    conflicts: list[FieldConflict] = []
    updated = data.model_copy(
        update={
            "vendor_name": _fill_text(
                "vendor_name", data.vendor_name, llm.vendor_name, sources, conflicts
            ),
            "vendor_tax_id": _fill_text(
                "vendor_tax_id",
                data.vendor_tax_id,
                llm.vendor_tax_id,
                sources,
                conflicts,
                normalize=_normalize_identifier,
            ),
            "customer_name": _fill_text(
                "customer_name", data.customer_name, llm.customer_name, sources, conflicts
            ),
            "customer_tax_id": _fill_text(
                "customer_tax_id",
                data.customer_tax_id,
                llm.customer_tax_id,
                sources,
                conflicts,
                normalize=_normalize_identifier,
            ),
            "invoice_id": _fill_text(
                "invoice_id",
                data.invoice_id,
                llm.invoice_id,
                sources,
                conflicts,
                normalize=_normalize_identifier,
            ),
            "purchase_order": _fill_text(
                "purchase_order",
                data.purchase_order,
                llm.purchase_order,
                sources,
                conflicts,
                normalize=_normalize_identifier,
            ),
            "invoice_date": _fill_date(
                "invoice_date", data.invoice_date, llm.invoice_date, sources, conflicts
            ),
            "due_date": _fill_date("due_date", data.due_date, llm.due_date, sources, conflicts),
            "subtotal": _fill_money(
                "subtotal", data.subtotal, llm.subtotal, llm.currency_code, sources, conflicts
            ),
            "total_tax": _fill_money(
                "total_tax", data.total_tax, llm.total_tax, llm.currency_code, sources, conflicts
            ),
            "invoice_total": _fill_money(
                "invoice_total",
                data.invoice_total,
                llm.invoice_total,
                llm.currency_code,
                sources,
                conflicts,
            ),
        }
    )
    return updated, sources, conflicts


def _merge_receipt(
    data: Receipt, llm: LlmExtraction
) -> tuple[Receipt, dict[str, FieldSource], list[FieldConflict]]:
    sources: dict[str, FieldSource] = {}
    conflicts: list[FieldConflict] = []
    updated = data.model_copy(
        update={
            "merchant_name": _fill_text(
                "merchant_name", data.merchant_name, llm.vendor_name, sources, conflicts
            ),
            "transaction_date": _fill_date(
                "transaction_date", data.transaction_date, llm.invoice_date, sources, conflicts
            ),
            "subtotal": _fill_money(
                "subtotal", data.subtotal, llm.subtotal, llm.currency_code, sources, conflicts
            ),
            "total_tax": _fill_money(
                "total_tax", data.total_tax, llm.total_tax, llm.currency_code, sources, conflicts
            ),
            "total": _fill_money(
                "total", data.total, llm.invoice_total, llm.currency_code, sources, conflicts
            ),
        }
    )
    return updated, sources, conflicts
