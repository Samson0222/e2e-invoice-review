"""Run the full golden corpus (`samples/manifest.json`) through the live pipeline and check
it against the Northstar policy this project promises: right document type, right extracted
fields, and exactly the issue codes each scenario expects.

Cost: 13 documents, each making one Document Intelligence analyze call and two Azure OpenAI
calls (independent review + GL suggestion) -- 13 DI calls and 26 OpenAI calls total against
whatever tier `backend/.env` points at. Nothing is written to the app's database; this script
builds its own throwaway pipeline and an in-memory duplicate check.

Usage (from `backend/`):

    uv run --locked --no-sync python scripts/evaluate_corpus.py
"""

import json
import logging
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import APP_CONFIG, settings  # noqa: E402
from app.invoices.validation import (  # noqa: E402
    normalize_name,
    normalize_vat,
    status_for_issues,
    validate_invoice,
    validate_receipt,
)
from app.pipeline import PipelineResult  # noqa: E402
from app.pipeline.models import RawDocument  # noqa: E402
from app.pipeline.pipeline import build_default_pipeline  # noqa: E402
from app.schemas.common import Money  # noqa: E402
from app.schemas.invoice import Invoice  # noqa: E402
from app.schemas.receipt import Receipt  # noqa: E402 -- all app imports need the sys.path fix above

logging.basicConfig(level=logging.WARNING)

_SAMPLES_DIR = _BACKEND_DIR.parent / "samples"
_MANIFEST_PATH = _SAMPLES_DIR / "manifest.json"


@dataclass
class CaseResult:
    filename: str
    passed: bool
    problems: list[str]


def _money_str(money: Money | None) -> str | None:
    if money is None or money.amount is None:
        return None
    return f"{Decimal(str(money.amount)):.2f}"


def _date_str(value) -> str | None:
    return value.isoformat() if value else None


def _extracted_fields(result: PipelineResult) -> dict[str, str | None]:
    data = result.data
    if isinstance(data, Invoice):
        return {
            "currency": data.invoice_total.currency_code if data.invoice_total else None,
            "customer_name": data.customer_name,
            "customer_vat_id": data.customer_tax_id,
            "document_type": "invoice",
            "due_date": _date_str(data.due_date),
            "invoice_date": _date_str(data.invoice_date),
            "invoice_number": data.invoice_id,
            "invoice_total": _money_str(data.invoice_total),
            "purchase_order": data.purchase_order,
            "subtotal": _money_str(data.subtotal),
            "total_tax": _money_str(data.total_tax),
            "vendor_name": data.vendor_name,
            "vendor_vat_id": data.vendor_tax_id,
        }
    assert isinstance(data, Receipt)
    return {
        "currency": data.total.currency_code if data.total else None,
        "customer_name": None,
        "customer_vat_id": None,
        "document_type": "receipt",
        "due_date": None,
        "invoice_date": _date_str(data.transaction_date),
        "invoice_number": None,
        "invoice_total": _money_str(data.total),
        "purchase_order": None,
        "subtotal": _money_str(data.subtotal),
        "total_tax": _money_str(data.total_tax),
        "vendor_name": data.merchant_name,
        "vendor_vat_id": None,
    }


_VAT_FIELDS = {"vendor_vat_id", "customer_vat_id"}
_NAME_FIELDS = {"vendor_name", "customer_name"}


def _values_match(field: str, expected: str | None, actual: str | None) -> bool:
    if expected is None or actual is None:
        return expected == actual
    if field in {"invoice_total", "subtotal", "total_tax"}:
        try:
            return Decimal(expected) == Decimal(actual)
        except InvalidOperation:
            return expected == actual
    if field in _VAT_FIELDS:
        # OCR sometimes keeps the source document's spacing (e.g. "NL 123456782B90");
        # the app's own validation normalizes VAT ids the same way before comparing them.
        return normalize_vat(expected) == normalize_vat(actual)
    if field in _NAME_FIELDS:
        # Casing varies with the source document's own styling (e.g. all-caps letterhead);
        # the app's own validation compares names case-insensitively too.
        return normalize_name(expected) == normalize_name(actual)
    return expected.strip() == actual.strip()


def _normalize_duplicate_key(value: str) -> str:
    return " ".join(value.casefold().split())


def evaluate_case(
    entry: dict, result: PipelineResult, seen_invoice_keys: set[tuple[str, str]]
) -> CaseResult:
    problems: list[str] = []

    if result.document_type != entry["document_type"]:
        problems.append(
            f"document_type: expected {entry['document_type']!r}, got {result.document_type!r}"
        )

    actual_fields = _extracted_fields(result)
    for field, expected_value in entry["expected"].items():
        actual_value = actual_fields.get(field)
        if not _values_match(field, expected_value, actual_value):
            problems.append(f"{field}: expected {expected_value!r}, got {actual_value!r}")

    is_duplicate = False
    if isinstance(result.data, Invoice) and result.data.vendor_name and result.data.invoice_id:
        key = (
            _normalize_duplicate_key(result.data.vendor_name),
            _normalize_duplicate_key(result.data.invoice_id),
        )
        is_duplicate = key in seen_invoice_keys
        seen_invoice_keys.add(key)

    if isinstance(result.data, Invoice):
        issues = validate_invoice(
            result.data,
            expected_customer_name=APP_CONFIG.expected_customer_name,
            expected_customer_vat_id=APP_CONFIG.expected_customer_vat_id,
            min_confidence=APP_CONFIG.min_field_confidence,
            is_duplicate=is_duplicate,
        )
    else:
        issues = validate_receipt(result.data, min_confidence=APP_CONFIG.min_field_confidence)

    actual_codes = {issue.code for issue in issues if issue.severity == "error"}
    expected_codes = {
        code
        for code in entry["expected_issue_codes"]
        if code not in {"purchase_order_missing", "low_confidence"}
    }
    if actual_codes != expected_codes:
        problems.append(
            f"issue codes: expected {sorted(expected_codes)}, got {sorted(actual_codes)}"
        )

    status = status_for_issues(issues)
    expected_status = "needs_review" if expected_codes else "ready"
    if status != expected_status:
        problems.append(f"status: expected {expected_status!r}, got {status!r}")

    return CaseResult(filename=entry["filename"], passed=not problems, problems=problems)


def main() -> int:
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    pipeline = build_default_pipeline(settings)
    seen_invoice_keys: set[tuple[str, str]] = set()

    results: list[CaseResult] = []
    for entry in manifest:
        file_path = _SAMPLES_DIR / "generated" / entry["filename"]
        file_bytes = file_path.read_bytes()
        print(f"Evaluating {entry['filename']} ({entry['scenario']})...", flush=True)
        try:
            result = pipeline.run(RawDocument(filename=entry["filename"], file_bytes=file_bytes))
        except Exception as error:  # noqa: BLE001 -- report and continue past provider failures
            results.append(
                CaseResult(
                    filename=entry["filename"],
                    passed=False,
                    problems=[f"pipeline error: {error}"],
                )
            )
            continue
        results.append(evaluate_case(entry, result, seen_invoice_keys))

    print("\n=== Results ===")
    failures = 0
    for case in results:
        if case.passed:
            print(f"PASS  {case.filename}")
        else:
            failures += 1
            print(f"FAIL  {case.filename}")
            for problem in case.problems:
                print(f"       - {problem}")

    print(f"\n{len(results) - failures}/{len(results)} documents passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
