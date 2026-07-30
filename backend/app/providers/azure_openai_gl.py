"""Azure OpenAI adapter for suggesting a Northstar GL account. pydantic-ai/OpenAI SDK types
stop here -- the rest of the app only sees `GLAccountSuggestion`."""

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.azure import AzureProvider

from app.accounting.catalog import NORTHSTAR_GL_CATALOG, GLAccountCode
from app.schemas.invoice import Invoice
from app.schemas.receipt import Receipt

_MODEL = "gpt-5.6-terra"

_CATALOG_TEXT = "\n".join(f"{code} - {name}" for code, name in NORTHSTAR_GL_CATALOG)
_PROMPT = (
    "Suggest the single best-fit general ledger account for this financial document, "
    "chosen strictly from the Northstar chart of accounts below. Base the choice on the "
    "vendor/merchant name and the line-item descriptions. Provide a confidence between "
    "0 and 1 for the suggestion.\n\n"
    f"{_CATALOG_TEXT}\n\n"
    "Document data:\n{document_json}"
)


class GLAccountSuggestion(BaseModel):
    gl_account_code: GLAccountCode
    rationale: str
    confidence: float


class GLClassifier:
    def __init__(self, endpoint: str, api_key: str) -> None:
        model = OpenAIResponsesModel(
            _MODEL,
            provider=AzureProvider(azure_endpoint=endpoint, api_key=api_key),
        )
        self._agent = Agent(model, output_type=GLAccountSuggestion)

    def classify(self, data: Invoice | Receipt) -> GLAccountSuggestion:
        prompt = _PROMPT.format(document_json=data.model_dump_json(exclude_none=True))
        result = self._agent.run_sync(prompt)
        return result.output
