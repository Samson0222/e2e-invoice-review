"""Which Northstar policy issues are the supplier's to fix, versus Maya's own data entry.
Drives whether the "request correction" action is offered at all."""

from typing import Any

SUPPLIER_FIXABLE_CODES = {
    "vendor_name_required",
    "vendor_vat_id_required",
    "vendor_vat_id_invalid",
    "customer_name_required",
    "customer_name_mismatch",
    "customer_vat_id_required",
    "customer_vat_id_mismatch",
    "invoice_number_required",
    "invoice_date_required",
    "invoice_total_required",
    "invoice_total_non_positive",
    "currency_required",
    "due_date_before_invoice_date",
    "invoice_total_mismatch",
    "purchase_order_missing",
    "merchant_name_required",
    "transaction_date_required",
    "receipt_currency_required",
    "receipt_total_required",
    "receipt_total_non_positive",
    "receipt_vat_required",
    "receipt_total_mismatch",
}


def supplier_fixable_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [issue for issue in issues if issue.get("code") in SUPPLIER_FIXABLE_CODES]
