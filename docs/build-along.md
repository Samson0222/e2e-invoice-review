# Build-along guide

The complete guided build lives at <https://learn.datalumina.com/docs/invoice-review>. This local guide records the first checkpoint represented by the `main` branch.

## Starter outcome

The repository installs reproducibly, starts a minimal FastAPI service and React interface, and includes the business brief plus fictional source documents.

## Why this boundary exists

The starter removes the completed workflow while preserving every prerequisite needed to build it. You begin with the user, the source documents, and explicit service boundaries instead of reverse-engineering a finished application.

## Commands

```bash
cd backend
uv sync --locked

cd ../frontend
pnpm install --frozen-lockfile

cd ..
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
./scripts/dev.sh --check
./scripts/dev.sh
```

## Important locations

- `docs/client-brief.md`: the recurring finance problem and definition of done
- `docs/architecture.md`: the intended boundaries and data flow
- `samples/`: the fictional evaluation corpus and manifest
- `backend/app/main.py`: the initial API boundary
- `frontend/src/App.tsx`: the initial interface boundary

## What you should observe

- `GET http://localhost:8000/health` returns `{"status":"ok"}`.
- `http://localhost:5173` shows the Invoice Review starter screen.
- No Azure request occurs at this checkpoint.

## Checkpoint

- [ ] Locked backend and frontend installs succeed.
- [ ] Backend lint passes.
- [ ] Frontend type-check, lint, and production build pass.
- [ ] `./scripts/dev.sh --check` reports that Invoice Review is ready to start.
- [ ] The health endpoint and starter screen load locally.

Continue with the [online tutorial](https://learn.datalumina.com/docs/invoice-review).

## Full review loop

This slice closes the loop the client brief describes: upload -> independent Azure OpenAI
review + Document Intelligence extraction -> deterministic merge with provenance -> the full
Northstar policy (`docs/client-brief.md`) -> Maya corrects fields, picks a GL account, and
approves, rejects, or drafts a supplier correction email.

### Why

The starter intentionally stopped at a health check. Everything Maya's user story needs --
the hybrid extraction, the complete rule set (including duplicate detection), and the
decision loop -- was still missing, so the app couldn't yet do what `docs/client-brief.md`
promises.

### What changed

- `backend/app/providers/`: Azure Document Intelligence and Azure OpenAI (review, GL
  suggestion, correction email) adapters -- SDK types stop here.
- `backend/app/pipeline/`: `ReviewStep -> ExtractStep -> MergeStep -> ClassifyGLStep`, ending
  at a `PipelineResult` with merged data, per-field provenance, and any DI/LLM conflicts.
- `backend/app/invoices/validation.py`: the full invoice and receipt policy from the client
  brief, including duplicate detection.
- `backend/app/invoices/{service,routes,schemas,models}.py`: field corrections, GL account
  override, and the approve/reject decision, plus serving the original file for preview.
- `backend/app/correction_email/`: eligibility rules and the draft schema for the on-demand
  correction email (Copy and Close only -- the app never sends it).
- `frontend/src/components/DocumentReview.tsx`, `DocumentInbox.tsx`,
  `CorrectionEmailDialog.tsx`: the review, history, and correction-email UI.
- `backend/scripts/evaluate_corpus.py`: checks the full pipeline against every scenario in
  `samples/manifest.json`.

### Commands

```bash
cd backend
uv run --locked --no-sync ruff check app scripts

cd ../frontend
npx tsc -b && npx eslint . && npx vite build

cd ..
./scripts/dev.sh
```

### What you should observe

- Uploading a happy-path sample (e.g. `01-en-happy-classic.pdf`) reaches `"ready"` with no
  issues and an enabled Approve button.
- Uploading `05-nl-missing-vendor-vat.pdf` reaches `"needs_review"` with a
  `vendor_vat_id_required` error; correcting the VAT field and saving clears it and enables
  Approve.
- Uploading `10-de-duplicate.pdf` after its non-duplicate counterpart raises
  `duplicate_invoice`.
- `uv run --locked --no-sync python backend/scripts/evaluate_corpus.py` reports all 13
  documents passing (13 Document Intelligence calls + 26 Azure OpenAI calls against the
  configured resource).

### Checkpoint

- [ ] Backend lint passes; frontend type-check, lint, and build pass.
- [ ] The manual walkthrough above (happy path, missing-VAT correction, duplicate detection)
      works against a live Azure resource.
- [ ] `backend/scripts/evaluate_corpus.py` passes all 13 documents.

## Review page polish

### Why

The review screen's document preview stretched to match whatever the tallest sidebar card
happened to be, sometimes filling most of the viewport. The correction-email dialog silently
called Azure OpenAI again every time it was reopened, so Maya couldn't recall a draft she'd
already copied. The GL account dropdown could render blank -- with the suggestion text still
visible below it -- whenever the one-time GL catalog fetch on app start failed, since nothing
retried or surfaced the failure.

### What changed

- `frontend/src/components/DocumentReview.tsx`: the document preview is capped to a moderate,
  still-readable height (`lg:max-h-[560px]`) instead of stretching to match the sidebar.
- `backend/app/invoices/models.py`, `service.py`, `routes.py`: the correction-email draft is
  now persisted on the document record. Reopening the dialog returns the stored draft instead
  of calling Azure OpenAI again; saving a field correction invalidates the stored draft so the
  next request regenerates one that reflects the corrected data.
- `frontend/src/App.tsx`, `DocumentReview.tsx`: the GL account catalog fetch now has proper
  error handling. A failed fetch surfaces a retry affordance in the GL account card instead of
  leaving the dropdown silently empty.

### Commands

```bash
cd backend
uv run --locked --no-sync ruff check app scripts

cd ../frontend
npx tsc -b && npx eslint . && npx vite build

cd ..
rm backend/data/invoice_review.db  # no migrations: the new column needs a fresh table
./scripts/dev.sh
```

### What you should observe

- Opening any review keeps the document preview to a moderate height on desktop widths; the
  embedded PDF viewer's own scroll/zoom still reaches the rest of the page.
- Requesting a correction email twice in a row (without editing fields) returns the identical
  draft instantly the second time. Correcting a field and reopening the dialog produces a new
  draft that reflects the correction.
- The GL account dropdown populates normally on a fresh load; if the GL catalog request is
  blocked or fails, the card shows an error message and a working Retry button instead of a
  blank select.

### Checkpoint

- [ ] Backend lint passes; frontend type-check, lint, and build pass.
- [ ] The manual walkthrough above (preview sizing, correction-email persistence and
      invalidation, GL account error/retry) works locally.
