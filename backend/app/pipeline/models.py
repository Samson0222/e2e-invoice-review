"""Value objects threaded through the review -> extract -> merge -> GL-suggest pipeline.

Validation and status live in `app.invoices.validation` / `app.invoices.service`, not here:
duplicate detection needs database access the pipeline doesn't have, so the pipeline's job
ends at a merged, provenance-tracked document plus an advisory GL suggestion."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from app.schemas.invoice import Invoice
from app.schemas.llm_extraction import LlmExtraction
from app.schemas.receipt import Receipt

DocumentType = Literal["invoice", "receipt"]
FieldSource = Literal["document_intelligence", "llm_fallback"]


@dataclass(frozen=True)
class RawDocument:
    """Pipeline input: an unclassified file straight from upload."""

    filename: str
    file_bytes: bytes


@dataclass(frozen=True)
class ReviewedDocument:
    """Output of the independent LLM review: classification plus a standalone extraction."""

    filename: str
    file_bytes: bytes
    document_type: DocumentType
    classification_confidence: float
    classification_reasoning: str
    llm_extraction: LlmExtraction


@dataclass(frozen=True)
class ExtractedDocument:
    """Output of extraction: the Document Intelligence result mapped onto a typed schema."""

    filename: str
    document_type: DocumentType
    data: Invoice | Receipt
    classification_confidence: float
    classification_reasoning: str
    llm_extraction: LlmExtraction


class FieldConflict(BaseModel):
    """A field where Document Intelligence and the independent LLM extraction disagree.
    Surfaced to the reviewer, never auto-resolved."""

    field: str
    document_intelligence_value: str
    llm_value: str


@dataclass(frozen=True)
class MergedDocument:
    """Output of the merge step: Document Intelligence values filled from the LLM extraction
    only where DI found nothing, with provenance per field and any conflicts surfaced."""

    filename: str
    document_type: DocumentType
    data: Invoice | Receipt
    classification_confidence: float
    classification_reasoning: str
    field_sources: dict[str, FieldSource]
    conflicts: list[FieldConflict]


class GLClassification(BaseModel):
    """A GL account suggestion from the fixed Northstar catalog, with room for reviewer override."""

    suggested_account_code: str
    suggested_account_name: str
    rationale: str
    confidence: float
    reviewer_override_code: str | None = None

    @property
    def final_account_code(self) -> str:
        """The code that should actually be booked: the reviewer's override if one was set."""
        return self.reviewer_override_code or self.suggested_account_code


@dataclass(frozen=True)
class PipelineResult:
    """Final pipeline output: merged, provenance-tracked data plus an advisory GL suggestion."""

    filename: str
    document_type: DocumentType
    data: Invoice | Receipt
    classification_confidence: float
    classification_reasoning: str
    field_sources: dict[str, FieldSource]
    conflicts: list[FieldConflict]
    gl_classification: GLClassification | None = None
