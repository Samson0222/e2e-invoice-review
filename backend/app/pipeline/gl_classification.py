"""Pipeline step: suggest a general ledger account for an invoice or receipt from a fixed
chart of accounts. Runs as the pipeline's final step, after merging, for both document types.
The suggestion is advisory -- a reviewer can override it later via
`GLClassification.reviewer_override_code`."""

import logging

from app.accounting.catalog import GL_ACCOUNT_NAMES
from app.pipeline.base import Step
from app.pipeline.models import GLClassification, MergedDocument, PipelineResult
from app.providers.azure_openai_gl import GLClassifier

logger = logging.getLogger(__name__)


class ClassifyGLStep(Step[MergedDocument, PipelineResult]):
    """Pipeline's final step: suggests a Northstar GL account for the merged document."""

    def __init__(self, classifier: GLClassifier) -> None:
        self._classifier = classifier

    def run(self, value: MergedDocument) -> PipelineResult:
        logger.info("[gl-classify] %s: suggesting GL account", value.filename)
        suggestion = self._classifier.classify(value.data)
        logger.info(
            "[gl-classify] %s: suggested %s (%s)",
            value.filename,
            suggestion.gl_account_code,
            GL_ACCOUNT_NAMES[suggestion.gl_account_code],
        )
        return PipelineResult(
            filename=value.filename,
            document_type=value.document_type,
            data=value.data,
            classification_confidence=value.classification_confidence,
            classification_reasoning=value.classification_reasoning,
            field_sources=value.field_sources,
            conflicts=value.conflicts,
            gl_classification=GLClassification(
                suggested_account_code=suggestion.gl_account_code,
                suggested_account_name=GL_ACCOUNT_NAMES[suggestion.gl_account_code],
                rationale=suggestion.rationale,
                confidence=suggestion.confidence,
            ),
        )
