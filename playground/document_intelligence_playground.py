"""Run the Document Intelligence surface against a sample invoice and inspect the output.

From the playground folder:

    uv run --project ../backend python document_intelligence_playground.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.services.document_intelligence_service import DocumentIntelligenceService  # noqa: E402

SAMPLE_INVOICE_PATH = REPO_ROOT / "samples" / "generated" / "01-en-happy-classic.pdf"


def main() -> None:
    service = DocumentIntelligenceService(
        endpoint=settings.azure_document_intelligence_endpoint,
        key=settings.azure_document_intelligence_key,
    )
    result = service.analyze_invoice(SAMPLE_INVOICE_PATH.read_bytes())
    print(json.dumps(result.as_dict(), indent=2, default=str))
    result.content


if __name__ == "__main__":
    main()
