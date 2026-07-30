"""The single boundary for reading backend configuration from the environment."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    azure_document_intelligence_endpoint: str
    azure_document_intelligence_key: str

    azure_openai_endpoint: str
    azure_openai_api_key: str


settings = Settings()


@dataclass(frozen=True)
class AppConfig:
    """Fixed application policy. Not read from the environment: see backend/AGENTS.md."""

    upload_dir: Path
    database_url: str
    allowed_origin: str
    max_upload_bytes: int
    expected_customer_name: str
    expected_customer_vat_id: str
    min_field_confidence: float


APP_CONFIG = AppConfig(
    upload_dir=_BACKEND_DIR / "data" / "uploads",
    database_url=f"sqlite:///{_BACKEND_DIR / 'data' / 'invoice_review.db'}",
    allowed_origin="http://localhost:5173",
    max_upload_bytes=4 * 1024 * 1024,
    expected_customer_name="Northstar Facilities B.V.",
    expected_customer_vat_id="NL00449544B01",
    min_field_confidence=0.80,
)
