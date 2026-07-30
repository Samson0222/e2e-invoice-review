"""Pipeline step: run the type-appropriate Document Intelligence model and map its
output onto the Invoice/Receipt Pydantic schemas."""

import logging

from azure.ai.documentintelligence.models import AnalyzeResult

from app.pipeline.base import Step
from app.pipeline.models import ExtractedDocument, ReviewedDocument
from app.providers.azure_document_intelligence import DocumentIntelligenceService
from app.schemas.invoice import Invoice
from app.schemas.receipt import Receipt

logger = logging.getLogger(__name__)


class ExtractionError(RuntimeError):
    """Raised when Document Intelligence returns no analyzed document to map."""


class ExtractStep(Step[ReviewedDocument, ExtractedDocument]):
    def __init__(self, service: DocumentIntelligenceService) -> None:
        self._service = service

    def run(self, value: ReviewedDocument) -> ExtractedDocument:
        logger.info("[extract] %s: running prebuilt-%s model", value.filename, value.document_type)
        if value.document_type == "invoice":
            result = self._service.analyze_invoice(value.file_bytes)
            data = Invoice.from_document(_first_document(result, value.filename))
        else:
            result = self._service.analyze_receipt(value.file_bytes)
            data = Receipt.from_document(_first_document(result, value.filename))
        logger.info(
            "[extract] %s: mapped %d line item(s), confidence %.2f",
            value.filename,
            len(data.items),
            data.confidence,
        )
        return ExtractedDocument(
            filename=value.filename,
            document_type=value.document_type,
            data=data,
            classification_confidence=value.classification_confidence,
            classification_reasoning=value.classification_reasoning,
            llm_extraction=value.llm_extraction,
        )


def _first_document(result: AnalyzeResult, filename: str):
    if not result.documents:
        raise ExtractionError(f"Document Intelligence found no documents in {filename!r}")
    return result.documents[0]
