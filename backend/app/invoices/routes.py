"""Upload, list, fetch, correct, decide on, and delete saved document reviews."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import APP_CONFIG
from app.correction_email.schemas import CorrectionEmailDraft
from app.invoices.repository import DocumentRepository
from app.invoices.schemas import (
    DecisionRequest,
    DocumentCorrectionRequest,
    DocumentResponse,
    GLAccountSelectionRequest,
)
from app.invoices.service import (
    DocumentNotFoundError,
    DocumentProcessingError,
    DocumentReviewConflictError,
    DocumentService,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_repository(session: Annotated[Session, Depends(get_session)]) -> DocumentRepository:
    return DocumentRepository(session)


def build_service(request: Request, repository: DocumentRepository) -> DocumentService:
    return DocumentService(
        repository=repository,
        upload_dir=APP_CONFIG.upload_dir,
        pipeline=request.app.state.pipeline,
        correction_email_drafter=request.app.state.correction_email_drafter,
        expected_customer_name=APP_CONFIG.expected_customer_name,
        expected_customer_vat_id=APP_CONFIG.expected_customer_vat_id,
        min_confidence=APP_CONFIG.min_field_confidence,
    )


def to_response(record) -> DocumentResponse:
    response = DocumentResponse.model_validate(record)
    return response


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> list[DocumentResponse]:
    return [to_response(record) for record in repository.list()]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    service = build_service(request, repository)
    try:
        return to_response(service.get(document_id))
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{document_id}/file")
def get_document_file(
    document_id: str,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> FileResponse:
    service = build_service(request, repository)
    try:
        record = service.get(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    path = APP_CONFIG.upload_dir / Path(record.stored_filename).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored document file was not found.")
    return FileResponse(
        path,
        media_type=record.content_type,
        filename=record.original_filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> None:
    service = build_service(request, repository)
    try:
        service.delete(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put("/{document_id}", response_model=DocumentResponse)
def correct_document(
    document_id: str,
    corrections: DocumentCorrectionRequest,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    service = build_service(request, repository)
    try:
        return to_response(service.correct(document_id, corrections))
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentReviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put("/{document_id}/accounting", response_model=DocumentResponse)
def select_gl_account(
    document_id: str,
    body: GLAccountSelectionRequest,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    service = build_service(request, repository)
    try:
        return to_response(service.select_gl_account(document_id, body.gl_account_code))
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentReviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{document_id}/decision", response_model=DocumentResponse)
def decide_document(
    document_id: str,
    body: DecisionRequest,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    service = build_service(request, repository)
    try:
        return to_response(service.decide(document_id, body.decision))
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentReviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{document_id}/correction-email", response_model=CorrectionEmailDraft)
def draft_correction_email(
    document_id: str,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> CorrectionEmailDraft:
    service = build_service(request, repository)
    try:
        return service.draft_correction_email(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentReviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
    file: Annotated[UploadFile, File()],
) -> DocumentResponse:
    content_type = file.content_type or "application/octet-stream"
    suffix = ALLOWED_CONTENT_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(status_code=415, detail="Use a PDF, JPEG, or PNG document.")

    payload = file.file.read(APP_CONFIG.max_upload_bytes + 1)
    if not payload:
        raise HTTPException(status_code=422, detail="Uploaded document is empty.")
    if len(payload) > APP_CONFIG.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Documents are limited to 4 MB.")

    original_filename = Path(file.filename or "document").name[:255]
    service = build_service(request, repository)
    try:
        record = service.process(
            original_filename=original_filename,
            content_type=content_type,
            content=payload,
            suffix=suffix,
        )
    except DocumentProcessingError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return to_response(record)
