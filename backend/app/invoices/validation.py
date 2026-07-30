"""Northstar's deterministic finance policy: what must be true before a document can be
approved. Pure functions only -- no network calls, no persistence. See docs/client-brief.md
for the rule descriptions this module implements."""

from decimal import Decimal

from stdnum.eu import vat as eu_vat

from app.invoices.schemas import ValidationIssue
from app.schemas.common import Money
from app.schemas.invoice import Invoice
from app.schemas.receipt import Receipt

_RECONCILIATION_TOLERANCE = Decimal("0.01")


def _issue(
    code: str, field: str | None, message: str, *, severity: str = "error"
) -> ValidationIssue:
    return ValidationIssue(code=code, field=field, severity=severity, message=message)


def normalize_vat(value: str) -> str:
    return value.replace(" ", "").replace("-", "").replace(".", "").upper()


def _is_valid_eu_vat(tax_id: str) -> bool:
    candidate = normalize_vat(tax_id)
    country_code = candidate[:2].lower()
    if country_code not in eu_vat.MEMBER_STATES:
        return True  # not formatted as an EU VAT number; the offline check doesn't apply
    return eu_vat.is_valid(candidate)


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _invoice_currency(data: Invoice) -> str | None:
    if data.invoice_total and data.invoice_total.currency_code:
        return data.invoice_total.currency_code
    if data.subtotal and data.subtotal.currency_code:
        return data.subtotal.currency_code
    return None


def _reconcile_totals(
    subtotal: Money | None, tax: Money | None, total: Money | None, *, code: str, field: str
) -> list[ValidationIssue]:
    if subtotal is None or subtotal.amount is None or total is None or total.amount is None:
        return []
    tax_amount = Decimal(str(tax.amount)) if tax and tax.amount is not None else Decimal("0")
    expected_total = Decimal(str(subtotal.amount)) + tax_amount
    actual_total = Decimal(str(total.amount))
    if abs(expected_total - actual_total) <= _RECONCILIATION_TOLERANCE:
        return []
    return [
        _issue(
            code,
            field,
            f"subtotal ({subtotal.amount}) + VAT ({tax_amount}) = {expected_total} does not "
            f"match total ({actual_total}).",
        )
    ]


def validate_invoice(
    data: Invoice,
    *,
    expected_customer_name: str,
    expected_customer_vat_id: str,
    min_confidence: float,
    is_duplicate: bool,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not data.vendor_name:
        issues.append(_issue("vendor_name_required", "vendor_name", "Supplier name is required."))

    if not data.vendor_tax_id:
        issues.append(
            _issue("vendor_vat_id_required", "vendor_tax_id", "Supplier VAT number is required.")
        )
    elif not _is_valid_eu_vat(data.vendor_tax_id):
        issues.append(
            _issue(
                "vendor_vat_id_invalid",
                "vendor_tax_id",
                f"{data.vendor_tax_id!r} is not a valid EU VAT number.",
            )
        )

    if not data.customer_name:
        issues.append(
            _issue("customer_name_required", "customer_name", "Customer name is required.")
        )
    elif normalize_name(data.customer_name) != normalize_name(expected_customer_name):
        issues.append(
            _issue(
                "customer_name_mismatch",
                "customer_name",
                f"Customer must be {expected_customer_name}.",
            )
        )

    if not data.customer_tax_id:
        issues.append(
            _issue(
                "customer_vat_id_required", "customer_tax_id", "Customer VAT number is required."
            )
        )
    elif normalize_vat(data.customer_tax_id) != normalize_vat(expected_customer_vat_id):
        issues.append(
            _issue(
                "customer_vat_id_mismatch",
                "customer_tax_id",
                "Customer VAT number does not match Northstar's registered VAT number.",
            )
        )

    if not data.invoice_id:
        issues.append(
            _issue("invoice_number_required", "invoice_id", "Invoice number is required.")
        )
    if data.invoice_date is None:
        issues.append(
            _issue("invoice_date_required", "invoice_date", "Invoice date is required.")
        )

    if data.invoice_total is None or data.invoice_total.amount is None:
        issues.append(
            _issue("invoice_total_required", "invoice_total", "Invoice total is required.")
        )
    elif data.invoice_total.amount <= 0:
        issues.append(
            _issue(
                "invoice_total_non_positive",
                "invoice_total",
                "Invoice total must be greater than zero.",
            )
        )

    if _invoice_currency(data) is None:
        issues.append(_issue("currency_required", "invoice_total", "Currency is required."))

    if (
        data.invoice_date is not None
        and data.due_date is not None
        and data.due_date < data.invoice_date
    ):
        issues.append(
            _issue(
                "due_date_before_invoice_date",
                "due_date",
                "Due date cannot be before the invoice date.",
            )
        )

    issues += _reconcile_totals(
        data.subtotal,
        data.total_tax,
        data.invoice_total,
        code="invoice_total_mismatch",
        field="invoice_total",
    )

    if is_duplicate:
        issues.append(
            _issue(
                "duplicate_invoice",
                "invoice_id",
                "A saved invoice with this supplier and invoice number already exists.",
            )
        )

    if not data.purchase_order:
        issues.append(
            _issue(
                "purchase_order_missing",
                "purchase_order",
                "Purchase-order reference is missing.",
                severity="warning",
            )
        )

    if data.confidence < min_confidence:
        issues.append(
            _issue(
                "low_confidence",
                None,
                f"Document Intelligence confidence ({data.confidence:.0%}) is below "
                f"{min_confidence:.0%}.",
                severity="warning",
            )
        )

    return issues


def validate_receipt(data: Receipt, *, min_confidence: float) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not data.merchant_name:
        issues.append(
            _issue("merchant_name_required", "merchant_name", "Merchant name is required.")
        )
    if data.transaction_date is None:
        issues.append(
            _issue("transaction_date_required", "transaction_date", "Transaction date is required.")
        )
    if data.total is None or data.total.currency_code is None:
        issues.append(_issue("receipt_currency_required", "total", "Receipt currency is required."))
    if data.total is None or data.total.amount is None:
        issues.append(_issue("receipt_total_required", "total", "Receipt total is required."))
    elif data.total.amount <= 0:
        issues.append(
            _issue(
                "receipt_total_non_positive", "total", "Receipt total must be greater than zero."
            )
        )
    if data.total_tax is None or data.total_tax.amount is None:
        issues.append(_issue("receipt_vat_required", "total_tax", "Receipt VAT total is required."))

    issues += _reconcile_totals(
        data.subtotal, data.total_tax, data.total, code="receipt_total_mismatch", field="total"
    )

    if data.confidence < min_confidence:
        issues.append(
            _issue(
                "low_confidence",
                None,
                f"Document Intelligence confidence ({data.confidence:.0%}) is below "
                f"{min_confidence:.0%}.",
                severity="warning",
            )
        )

    return issues


def has_blocking_errors(issues: list[ValidationIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


def status_for_issues(issues: list[ValidationIssue]) -> str:
    return "needs_review" if has_blocking_errors(issues) else "ready"
