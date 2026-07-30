"""Pipeline step: run one independent Azure OpenAI pass to classify the document and
extract a standalone set of fields, ahead of Document Intelligence extraction."""

import logging

from app.pipeline.base import Step
from app.pipeline.models import RawDocument, ReviewedDocument
from app.providers.azure_openai_review import DocumentReviewer

logger = logging.getLogger(__name__)


class ReviewStep(Step[RawDocument, ReviewedDocument]):
    """Pipeline entry point: decides which Document Intelligence model runs next."""

    def __init__(self, reviewer: DocumentReviewer) -> None:
        self._reviewer = reviewer

    def run(self, value: RawDocument) -> ReviewedDocument:
        logger.info("[review] %s: running independent LLM review", value.filename)
        extraction = self._reviewer.review(value.file_bytes, value.filename)
        logger.info(
            "[review] %s: classified as %s (confidence=%.2f)",
            value.filename,
            extraction.document_type,
            extraction.classification_confidence,
        )
        return ReviewedDocument(
            filename=value.filename,
            file_bytes=value.file_bytes,
            document_type=extraction.document_type,
            classification_confidence=extraction.classification_confidence,
            classification_reasoning=extraction.classification_reasoning,
            llm_extraction=extraction,
        )
