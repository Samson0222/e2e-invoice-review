"""Schema for the independent Azure OpenAI extraction used to fill Document Intelligence gaps."""

from typing import Literal

from pydantic import BaseModel, Field


class LlmExtraction(BaseModel):
    """One independent LLM pass over the raw file: classification plus best-effort fields.

    Every extracted field is a string (or null) because the model reads it off the page as
    text; parsing into the right type happens in the deterministic merge step.
    """

    document_type: Literal["invoice", "receipt"]
    classification_confidence: float = Field(ge=0.0, le=1.0)
    classification_reasoning: str

    vendor_name: str | None
    vendor_tax_id: str | None
    customer_name: str | None
    customer_tax_id: str | None
    invoice_id: str | None
    invoice_date: str | None
    due_date: str | None
    purchase_order: str | None
    currency_code: str | None
    subtotal: str | None
    total_tax: str | None
    invoice_total: str | None
