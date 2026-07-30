"""Provider-independent draft model for a supplier correction email. The app only ever
offers Copy and Close for this draft -- it never sends anything."""

from pydantic import BaseModel, ConfigDict


class CorrectionEmailDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_name: str
    subject: str
    body: str
