# API endpoints and pipeline

This document describes the current Invoice Review HTTP API and how `POST /api/documents`
runs the document pipeline. It reflects what is actually implemented on this branch today --
see `docs/build-along.md` for what's deferred to later checkpoints.

Base URL (local dev, via `./scripts/dev.sh`): `http://localhost:8420`

Interactive docs while the API is running:

- Swagger UI: `http://localhost:8420/docs`
- OpenAPI JSON: `http://localhost:8420/openapi.json`

CORS is fixed to allow the Vite app at `http://localhost:5173` (`APP_CONFIG.allowed_origin` in
`backend/app/config.py`).

---

## Endpoint summary

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness check |
| `GET` | `/api/accounting/gl-accounts` | Fixed Northstar GL catalog |
| `POST` | `/api/documents` | Upload a document and run the full pipeline |
| `GET` | `/api/documents` | List saved reviews (newest first) |
| `GET` | `/api/documents/{document_id}` | Fetch one saved review |
| `GET` | `/api/documents/{document_id}/file` | Stream the original uploaded file |
| `PUT` | `/api/documents/{document_id}` | Correct extracted fields and re-validate |
| `PUT` | `/api/documents/{document_id}/accounting` | Override the suggested GL account |
| `POST` | `/api/documents/{document_id}/decision` | Approve or reject a review |
| `POST` | `/api/documents/{document_id}/correction-email` | Draft a supplier correction email |
| `DELETE` | `/api/documents/{document_id}` | Delete a saved review and its upload file |

Deferred (not implemented, and out of scope per `AGENTS.md`): auth, batch processing, sending
the correction email, live VIES VAT lookup.

---

## `GET /health`

Returns `{"status": "ok"}`. No dependencies checked -- just confirms the process is up.

---

## `GET /api/accounting/gl-accounts`

Returns the fixed, ten-account Northstar chart of accounts used for GL suggestions. Source of
truth: `backend/app/accounting/catalog.py`. The pipeline's GL step
(`backend/app/pipeline/gl_classification.py`) imports this same catalog, so the codes offered
here always match what the model is allowed to suggest.

---

## `POST /api/documents`

Uploads one file and runs it through the full pipeline synchronously -- the request blocks
until review, extraction, merging, and GL suggestion all finish, validation runs, and the
result is persisted.

**Request**: `multipart/form-data` with a single `file` field.

- Accepted content types: `application/pdf`, `image/jpeg`, `image/png` -> **415** otherwise.
- Empty body -> **422**.
- Larger than 4 MB -> **413** (client-brief limit, checked in `backend/app/invoices/routes.py`
  before any Azure call is made).
- A pipeline exception (Azure/Document Intelligence/OpenAI failure) is still persisted as a
  `"failed"` row, and the request itself returns **502**.

**Response** (`201`, `DocumentResponse`):

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string (UUID) | Stable review id |
| `original_filename` | string | Filename from the upload |
| `content_type` | string | `application/pdf`, `image/jpeg`, or `image/png` |
| `status` | string | `"ready"`, `"needs_review"`, `"approved"`, `"rejected"`, or `"failed"` |
| `document_type` | string \| null | `"invoice"` or `"receipt"` |
| `classification_confidence` | number \| null | The independent LLM review's confidence (0-1) in the invoice/receipt label |
| `classification_reasoning` | string \| null | Short model-provided justification for that label |
| `data` | object \| null | The merged Invoice or Receipt fields |
| `field_sources` | object | Per-field provenance: `"document_intelligence"` or `"llm_fallback"` |
| `conflicts` | array | Fields where Document Intelligence and the LLM extraction disagreed |
| `issues` | array | `ValidationIssue` list: `{code, field, severity, message}` |
| `gl_classification` | object \| null | `{suggested_account_code, suggested_account_name, rationale, confidence, reviewer_override_code}` |
| `error_message` | string \| null | Set when `status` is `"failed"` |
| `created_at` / `updated_at` | ISO datetime | Persistence timestamps |

Status logic: `"needs_review"` when any issue has `severity == "error"`, `"ready"` otherwise
(warnings alone don't block review). There is no `"processing"` state -- the whole pipeline
runs inline before the response is sent.

---

## `GET /api/documents` and `GET /api/documents/{id}`

List returns all saved reviews, newest first, in the same `DocumentResponse` shape as upload.
Fetch-by-id returns **404** if the id doesn't exist.

## `GET /api/documents/{id}/file`

Streams the originally uploaded file (by its stored content type) so the review UI can show it
next to the extracted fields. **404** if the id or the stored file doesn't exist.

## `PUT /api/documents/{id}`

Body: `DocumentCorrectionRequest` -- any subset of the flat invoice/receipt fields (e.g.
`vendor_tax_id`, `invoice_total_amount`). Only fields present in the request body are changed;
an explicit `null` clears a field. Corrected fields are marked `field_sources: "human"`, the
document is re-validated (including a fresh duplicate check), and `status` is recomputed.
**409** if the document has already been approved or rejected.

## `PUT /api/documents/{id}/accounting`

Body: `{"gl_account_code": "5700"}`. Sets `gl_classification.reviewer_override_code`, validated
against the fixed catalog. **422** for an unknown code, **409** if already decided or if the
review has no GL suggestion to override.

## `POST /api/documents/{id}/decision`

Body: `{"decision": "approved" | "rejected"}`. Rejecting is always allowed (this is how a
supplier error becomes an actionable outcome). Approving requires zero `severity == "error"`
issues and a valid selected GL account. **409** if already decided, if the document isn't in a
reviewable state, or if approval preconditions aren't met.

## `POST /api/documents/{id}/correction-email`

Drafts a supplier correction email (`{recipient_name, subject, body}`) via Azure OpenAI,
covering only the issues in `app/correction_email/eligibility.py`'s supplier-fixable list.
**409** if there's no extracted data yet or no supplier-fixable issue on the review. The app
never sends this draft -- the UI only offers Copy and Close.

## `DELETE /api/documents/{id}`

Deletes the SQLite row and the stored upload file under `backend/data/uploads/`. Returns
**204**, or **404** if the id doesn't exist.

---

## How the pipeline works

`build_default_pipeline(settings)` in `backend/app/pipeline/pipeline.py` wires four steps into
one chain using the generic `Step[TIn, TOut]` abstraction (`backend/app/pipeline/base.py`):
each step implements `run(value) -> result`, and `.then()` composes two steps into one that
feeds the first step's output into the second. `app/main.py` builds this chain **once**, at
app startup, and stores it on `app.state.pipeline` -- it isn't rebuilt per request.

```
RawDocument -> ReviewStep -> ExtractStep -> MergeStep -> ClassifyGLStep -> PipelineResult
```

1. **`ReviewStep`** (`pipeline/review.py`) -- one independent Azure OpenAI call
   (`app/providers/azure_openai_review.py`) that both classifies the document (`"invoice"` or
   `"receipt"`, with a confidence and reasoning) and extracts a standalone set of fields
   directly from the page. This has to run before Document Intelligence because there's no
   single prebuilt model that reliably distinguishes invoice from receipt, and running one
   combined call here (rather than a separate classify-only call) avoids a redundant second
   LLM pass over the same file.

2. **`ExtractStep`** (`pipeline/extraction.py`) -- based on that label, calls the matching
   Azure Document Intelligence prebuilt model (`prebuilt-invoice` or `prebuilt-receipt`) via
   `app/providers/azure_document_intelligence.py` and maps its raw field output onto the typed
   `Invoice`/`Receipt` Pydantic schemas (`app/schemas/invoice.py`, `app/schemas/receipt.py`).

3. **`MergeStep`** (`pipeline/merge.py`) -- pure, offline, no network calls. Document
   Intelligence stays primary: a field is only filled from the independent LLM extraction when
   DI found nothing there. Every filled field is recorded in `field_sources`, and any field
   where DI and the LLM extraction *disagree* (DI has a value, but it doesn't match the LLM's)
   is surfaced as a `conflict` rather than silently resolved.

4. **`ClassifyGLStep`** (`pipeline/gl_classification.py`) -- sends the merged fields (not the
   original file) to Azure OpenAI again (`app/providers/azure_openai_gl.py`), asking it to pick
   one account from the fixed Northstar catalog with a rationale and a confidence score. The
   suggestion is advisory: `GLClassification.reviewer_override_code` can be set later via
   `PUT /api/documents/{id}/accounting`.

**Validation happens after the pipeline, not inside it**
(`backend/app/invoices/validation.py`, `backend/app/invoices/service.py`), because duplicate
detection needs a database lookup the pipeline's singleton instance doesn't have access to.
`DocumentService.process()` runs the pipeline, checks `DocumentRepository.duplicate_exists()`
for invoices, then calls `validate_invoice()`/`validate_receipt()` to produce the full
Northstar policy findings (`docs/client-brief.md`'s rule list) before persisting.

**Orchestration and persistence** (`backend/app/invoices/service.py`,
`DocumentService`): writes the uploaded bytes to `backend/data/uploads/`, runs the pipeline,
validates, and maps the result -- success or exception -- onto a `DocumentRecord` row
(`backend/app/invoices/models.py`) via `DocumentRepository` (`repository.py`). Routes
(`routes.py`) only handle HTTP concerns: content-type/size checks and status-code translation.
`DocumentService` also owns the post-processing review actions: field corrections
(`correct()`), GL overrides (`select_gl_account()`), and the approve/reject decision
(`decide()`).

---

## Evaluating against the golden corpus

`backend/scripts/evaluate_corpus.py` runs all 13 documents in `samples/manifest.json` through
a live pipeline build and checks document type, merged field values, and validation issue
codes against each manifest entry -- see `samples/README.md` for the exact command and its
Azure call budget.
