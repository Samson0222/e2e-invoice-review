"""Wires the review -> extract -> merge -> GL-classify steps into the default document
pipeline."""

from app.config import Settings
from app.pipeline.base import Step
from app.pipeline.extraction import ExtractStep
from app.pipeline.gl_classification import ClassifyGLStep
from app.pipeline.merge import MergeStep
from app.pipeline.models import PipelineResult, RawDocument
from app.pipeline.review import ReviewStep
from app.providers.azure_document_intelligence import DocumentIntelligenceService
from app.providers.azure_openai_gl import GLClassifier
from app.providers.azure_openai_review import DocumentReviewer


def build_default_pipeline(settings: Settings) -> Step[RawDocument, PipelineResult]:
    reviewer = DocumentReviewer(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )
    document_intelligence = DocumentIntelligenceService(
        endpoint=settings.azure_document_intelligence_endpoint,
        key=settings.azure_document_intelligence_key,
    )
    gl_classifier = GLClassifier(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )
    return (
        ReviewStep(reviewer)
        .then(ExtractStep(document_intelligence))
        .then(MergeStep())
        .then(ClassifyGLStep(gl_classifier))
    )
