"""FastAPI application factory: wiring, CORS, and the health check."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.accounting.routes import router as accounting_router
from app.config import APP_CONFIG, settings
from app.database import build_database
from app.invoices.models import Base
from app.invoices.routes import router as invoices_router
from app.pipeline import build_default_pipeline
from app.providers.azure_openai_correction_email import CorrectionEmailDrafter


def create_app() -> FastAPI:
    APP_CONFIG.upload_dir.mkdir(parents=True, exist_ok=True)

    engine, session_factory = build_database(APP_CONFIG.database_url)
    Base.metadata.create_all(engine)

    app = FastAPI(title="Invoice Review API", version="0.1.0")
    app.state.session_factory = session_factory
    app.state.pipeline = build_default_pipeline(settings)
    app.state.correction_email_drafter = CorrectionEmailDrafter(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[APP_CONFIG.allowed_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(invoices_router)
    app.include_router(accounting_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
