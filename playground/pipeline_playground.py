"""Run the full classify -> extract -> validate pipeline against sample documents.

From the playground folder:

    uv run --project ../backend python pipeline_playground.py
"""

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("app.pipeline").setLevel(logging.INFO)

from app.config import settings  # noqa: E402
from app.pipeline import RawDocument, build_default_pipeline  # noqa: E402

SAMPLES_DIR = REPO_ROOT / "samples" / "generated"
SAMPLE_FILES = [
    "01-en-happy-classic.pdf",
    "05-nl-missing-vendor-vat.pdf",
    "06-de-invalid-vendor-vat.pdf",
    "07-fr-wrong-customer-vat.pdf",
    "08-en-total-mismatch.pdf",
    "13-nl-fuel-receipt.png",
]


def main() -> None:
    pipeline = build_default_pipeline(settings)
    for filename in SAMPLE_FILES:
        raw = RawDocument(filename=filename, file_bytes=(SAMPLES_DIR / filename).read_bytes())
        result = pipeline.run(raw)
        print(f"\n=== {filename} ({result.document_type}) ===")
        print(f"valid: {result.is_valid}")
        for issue in result.issues:
            print(f"  - [{issue.field}] {issue.message}")
        if result.gl_classification:
            gl = result.gl_classification
            print(f"GL account: {gl.suggested_account_code} - {gl.suggested_account_name}")
            print(f"  rationale: {gl.rationale}")
        print(json.dumps(result.data.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
