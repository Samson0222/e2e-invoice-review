"""Map Document Intelligence output onto the Invoice/Receipt Pydantic models and inspect it.

From the playground folder:

    uv run --project ../backend python schema_playground.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.schemas.invoice import Invoice  # noqa: E402
from app.schemas.receipt import Receipt  # noqa: E402
from app.services.document_intelligence_service import DocumentIntelligenceService  # noqa: E402

SAMPLES_DIR = REPO_ROOT / "samples" / "generated"
INVOICE_SAMPLES = ["01-en-happy-classic.pdf", "12-en-two-page.pdf"]
RECEIPT_SAMPLES = ["13-nl-fuel-receipt.png"]


def main() -> None:
    service = DocumentIntelligenceService(
        endpoint=settings.azure_document_intelligence_endpoint,
        key=settings.azure_document_intelligence_key,
    )

    for filename in INVOICE_SAMPLES:
        print(f"\n=== invoice: {filename} ===")
        result = service.analyze_invoice((SAMPLES_DIR / filename).read_bytes())
        invoice = Invoice.from_document(result.documents[0])
        print(json.dumps(invoice.model_dump(mode="json"), indent=2))

    for filename in RECEIPT_SAMPLES:
        print(f"\n=== receipt: {filename} ===")
        result = service.analyze_receipt((SAMPLES_DIR / filename).read_bytes())
        receipt = Receipt.from_document(result.documents[0])
        print(json.dumps(receipt.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
