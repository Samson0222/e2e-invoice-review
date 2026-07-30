"""Azure OpenAI adapter for the independent document review: one pass over the raw file
that classifies it and extracts a standalone set of fields. pydantic-ai/OpenAI SDK types
stop here -- the rest of the app only sees `LlmExtraction`."""

import logging
import mimetypes

from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.azure import AzureProvider

from app.schemas.llm_extraction import LlmExtraction

logger = logging.getLogger(__name__)

_MODEL = "gpt-5.6-terra"
_INSTRUCTIONS = (
    "You independently review European invoices and receipts for a finance team. Classify "
    "the document as invoice or receipt, then extract every field you can read directly from "
    "the page as plain text. Leave a field null if it is not visibly present on the page -- "
    "do not guess or infer a value. Report dates as YYYY-MM-DD and amounts as plain decimal "
    "numbers without currency symbols or thousands separators."
)
_PROMPT = "Review this financial document."


class DocumentReviewer:
    """Runs one independent Azure OpenAI pass over the raw uploaded file."""

    def __init__(self, endpoint: str, api_key: str) -> None:
        model = OpenAIResponsesModel(
            _MODEL,
            provider=AzureProvider(azure_endpoint=endpoint, api_key=api_key),
        )
        self._agent = Agent(model, output_type=LlmExtraction, instructions=_INSTRUCTIONS)

    def review(self, file_bytes: bytes, filename: str) -> LlmExtraction:
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        result = self._agent.run_sync(
            [_PROMPT, BinaryContent(data=file_bytes, media_type=media_type)]
        )
        return result.output
