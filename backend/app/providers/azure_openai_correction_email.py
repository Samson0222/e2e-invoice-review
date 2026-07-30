"""Azure OpenAI adapter that drafts a supplier correction email from the review's
supplier-fixable issues. pydantic-ai/OpenAI SDK types stop here. The draft is always
presented with Copy and Close in the UI -- nothing is ever sent automatically."""

import json
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.azure import AzureProvider

from app.correction_email.schemas import CorrectionEmailDraft

_MODEL = "gpt-5.6-terra"
_INSTRUCTIONS = (
    "You draft short, polite correction-request emails from a Northstar Facilities B.V. "
    "finance administrator to a supplier, asking them to fix specific problems found on an "
    "invoice or receipt they sent. Reference the document's own vendor/merchant name and "
    "invoice number if present. List each issue as a clear, specific ask. Keep the body under "
    "150 words and sign off as 'Northstar Facilities Finance Team'."
)
_PROMPT = (
    "Document type: {document_type}\n"
    "Document data:\n{document_json}\n\n"
    "Issues to raise with the supplier:\n{issues_text}"
)


class CorrectionEmailDrafter:
    def __init__(self, endpoint: str, api_key: str) -> None:
        model = OpenAIResponsesModel(
            _MODEL,
            provider=AzureProvider(azure_endpoint=endpoint, api_key=api_key),
        )
        self._agent = Agent(model, output_type=CorrectionEmailDraft, instructions=_INSTRUCTIONS)

    def draft(
        self,
        document_type: str,
        data: dict[str, Any],
        issues: list[dict[str, Any]],
    ) -> CorrectionEmailDraft:
        issues_text = "\n".join(f"- {issue['message']}" for issue in issues)
        prompt = _PROMPT.format(
            document_type=document_type,
            document_json=json.dumps(data, default=str),
            issues_text=issues_text,
        )
        result = self._agent.run_sync(prompt)
        return result.output
