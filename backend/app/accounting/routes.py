"""Read-only access to the fixed Northstar GL catalog."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.accounting.catalog import NORTHSTAR_GL_CATALOG

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


class GLAccount(BaseModel):
    code: str
    name: str


@router.get("/gl-accounts", response_model=list[GLAccount])
def list_gl_accounts() -> list[GLAccount]:
    return [GLAccount(code=code, name=name) for code, name in NORTHSTAR_GL_CATALOG]
