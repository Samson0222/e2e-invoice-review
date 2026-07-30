"""FastAPI application factory: wiring, CORS, and the health check."""

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.accounting.routes import router as accounting_router
from app.auth.dependencies import require_auth
from app.auth.routes import router as auth_router
from app.config import APP_CONFIG, settings
from app.database import build_database
from app.invoices.models import Base
from app.invoices.routes import router as invoices_router
from app.pipeline import build_default_pipeline
from app.providers.azure_openai_correction_email import CorrectionEmailDrafter

_STATIC_DIR = Path(__file__).resolve().parent / "static"


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
    app.include_router(auth_router)
    app.include_router(invoices_router, dependencies=[Depends(require_auth)])
    app.include_router(accounting_router, dependencies=[Depends(require_auth)])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="frontend")

    return app
