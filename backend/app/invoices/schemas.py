"""API request/response shapes and the validation-issue type for the invoices module."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.pipeline.models import FieldConflict, GLClassification

IssueSeverity = Literal["error", "warning"]
Decision = Literal["approved", "rejected"]


class ValidationIssue(BaseModel):
    code: str
    field: str | None
    severity: IssueSeverity
    message: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    content_type: str
    status: str
    document_type: str | None = None
    classification_confidence: float | None = None
    classification_reasoning: str | None = None
    data: dict[str, Any] | None = None
    field_sources: dict[str, str] = {}
    conflicts: list[FieldConflict] = []
    issues: list[ValidationIssue] = []
    gl_classification: GLClassification | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentCorrectionRequest(BaseModel):
    """Field-by-field corrections Maya makes during review. Unset fields are left alone;
    a field explicitly set to null clears it."""

    model_config = ConfigDict(extra="forbid")

    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    customer_name: str | None = None
    customer_tax_id: str | None = None
    invoice_id: str | None = None
    purchase_order: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    currency_code: str | None = None
    subtotal_amount: float | None = None
    total_tax_amount: float | None = None
    invoice_total_amount: float | None = None
    merchant_name: str | None = None
    transaction_date: str | None = None
    total_amount: float | None = None


class GLAccountSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gl_account_code: str


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision
