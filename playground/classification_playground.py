"""Classify sample documents as invoice or receipt before picking a Document Intelligence model.

From the playground folder:

    uv run --project ../backend python classification_playground.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.pipeline.classification import DocumentClassifier  # noqa: E402

SAMPLES_DIR = REPO_ROOT / "samples" / "generated"
SAMPLE_FILES = [
    "01-en-happy-classic.pdf",
    "12-en-two-page.pdf",
    "13-nl-fuel-receipt.png",
]


def main() -> None:
    classifier = DocumentClassifier(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )
    for filename in SAMPLE_FILES:
        file_bytes = (SAMPLES_DIR / filename).read_bytes()
        classification = classifier.classify(file_bytes, filename)
        print(f"{filename}: {classification.document_type}")


if __name__ == "__main__":
    main()
