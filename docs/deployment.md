# Azure deployment

The app is deployed to Azure as a single container: one Docker image serves both the built
React frontend (as static files) and the FastAPI backend (under `/api/*`) from one process on
one port. It runs on **Azure Container Apps (ACA)**, in the existing resource group
`rg-invoice-review`.

Live URL: `https://ca-invoice-review.ambitiousgrass-0fe56c4f.northeurope.azurecontainerapps.io/`

The app is password-gated (see [Password gate](#password-gate) below) -- ask whoever set it up
for the password, or read it from the `app-password` secret on the Container App.

---

## Resources

| Resource | Name | Region | Purpose |
|---|---|---|---|
| Resource group | `rg-invoice-review` | westeurope | Existing group everything lives in |
| Container Registry | `acrinvoicereview` | northeurope | Holds the built image |
| Storage Account | `stinvoicereview` | northeurope | Backs the file share |
| File Share | `invoice-data` | -- | Persistent storage for uploaded documents |
| Container Apps Environment | `cae-invoice-review` | northeurope | Hosting environment (+ auto-created Log Analytics workspace) |
| Container App | `ca-invoice-review` | northeurope | The running app |

**Why `northeurope` and not `westeurope`:** the resource group is in `westeurope`, but at
deploy time Azure rejected new storage accounts there for this subscription
(`RequestDisallowedByAzure: The selected region is currently not accepting new customers`).
Storage, the ACA environment, and the app were created in `northeurope` instead, so the file
share mount stays low-latency (same region as the app). The resource group's own region is just
metadata and doesn't need to match.

---

## Single-container build

`Dockerfile` (repo root) is a two-stage build:

1. `node:22-alpine` -- runs `pnpm install` + `pnpm build` in `frontend/`, with
   `VITE_API_BASE_URL=""` baked in at build time. An empty base URL means the built frontend
   calls same-origin relative paths (e.g. `/api/documents`), which works because it's served
   from the same container as the API.
2. `python:3.12-slim` -- `uv sync --locked --no-dev` for the backend, then copies the frontend's
   `dist/` output into `backend/app/static/`.

`backend/app/main.py` mounts that `static/` directory at `/` with `StaticFiles(html=True)`,
*after* the API routers are registered. Starlette matches routes in registration order, so
`/api/*` always resolves to the routers, and everything else falls through to the frontend's
`index.html` (the frontend has no client-side router, so no SPA-fallback logic is needed). The
mount is guarded by `_STATIC_DIR.exists()`, so local dev (`uv run uvicorn ...` without a built
`static/` folder) is unaffected.

Build context is the repo root (needs both `backend/` and `frontend/`); see `.dockerignore` for
what's excluded (`.venv`, `node_modules`, `backend/data`, `.env` files, etc.).

---

## Password gate

Deliberately minimal: one shared password, no accounts, no user table.

- `backend/app/auth/service.py` -- issues a session as `{expiry_timestamp}.{hmac_signature}`,
  signed with `sha256(APP_PASSWORD)`. Stateless: no server-side session store, so it survives
  container restarts without any DB.
- `backend/app/auth/routes.py` -- `POST /api/auth/login`, `POST /api/auth/logout`,
  `GET /api/auth/status`, all unauthenticated (they're the gate itself).
- `backend/app/auth/dependencies.py` -- `require_auth`, applied to the invoices and accounting
  routers in `main.py` via `app.include_router(..., dependencies=[Depends(require_auth)])`. A
  no-op whenever `APP_PASSWORD` is unset (e.g. local dev), so the gate never gets in the way
  unless it's explicitly configured.
- Cookie is `HttpOnly`, `SameSite=Lax`, 7-day expiry. Frontend (`frontend/src/App.tsx`,
  `frontend/src/components/LoginGate.tsx`) checks `/api/auth/status` on load and renders a
  password screen until it gets a session.

The frontend's static files themselves are *not* gated (they have to be reachable to render the
login screen at all) -- real protection is enforced server-side on every `/api/*` call.

---

## Persistence: what survives a restart and what doesn't

The original plan (per project requirements) was to put the SQLite database file itself on the
Azure Files share for full persistence. **That doesn't work**: SQLite requires OS-level file
locks it can't reliably get over a network filesystem (Azure Files is SMB-backed), and the
container crashed on first boot with `sqlite3.OperationalError: database is locked` the moment
`Base.metadata.create_all()` tried to create the first table. This matches SQLite's own
documented guidance against network filesystems -- it's not a "not recommended for production"
caveat, it's a hard failure even for a single writer on first use.

**What's actually deployed:**

- The Azure Files share (`invoice-data`) is mounted at `/app/data/uploads` only.
- The SQLite database (`/app/data/invoice_review.db`, one level up, outside the mount) sits on
  the container's local/ephemeral disk.
- `backend/app/config.py` was not changed for this -- `APP_CONFIG.upload_dir` and
  `APP_CONFIG.database_url` already pointed at sibling paths under `data/`, so scoping the mount
  to just the `uploads/` subfolder needed no code change, only the volume mount's `mountPath` in
  the Container Apps manifest.

**Net effect, confirmed by an actual restart test:** uploaded PDF/image files persist across
restarts and redeploys. Review records (status, extracted fields, GL suggestions, decisions) do
not -- a restart resets them, same as a fresh install. The uploaded files remain on the share
but become orphaned (no DB row points at them) until re-uploaded.

**If full persistence is needed later:** replace SQLite with a real network-friendly database,
e.g. Azure Database for PostgreSQL Flexible Server. That's a real infrastructure change (new
resource, connection string, `sqlalchemy` dialect swap, small monthly cost) -- deliberately not
done here to keep the deployment simple, per the "keep it simple" instruction this was built
under.

---

## Secrets and configuration

Set as Container App secrets (`az containerapp secret list -g rg-invoice-review -n
ca-invoice-review`), referenced by the container's env vars via `secretRef` -- never baked into
the image:

| Secret | Backing env var |
|---|---|
| `doc-intel-key` | `AZURE_DOCUMENT_INTELLIGENCE_KEY` |
| `openai-key` | `AZURE_OPENAI_API_KEY` |
| `app-password` | `APP_PASSWORD` |
| `acr-password` | (registry pull credential, not app-visible) |

Non-secret env vars (`AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`, `AZURE_OPENAI_ENDPOINT`) are set as
plain values. `backend/app/config.py`'s `Settings.app_password` is `str | None`, defaulting to
`None` -- unset locally, so local dev never needs to configure it (see
`backend/.env.example`).

Scale is pinned to **min replicas = 1, max replicas = 1**. This is required, not just a cost
choice: the SQLite DB file is a single local file with no concurrent-writer support, so running
more than one replica would risk corruption.

---

## Redeploying a new version

Docker Desktop must be running locally (`az acr build` -- the no-local-Docker cloud build path
-- is blocked on this subscription with `TasksOperationsNotAllowed`; local build + push is the
working path here).

```bash
# from the repo root
az acr login --name acrinvoicereview

docker build -t acrinvoicereview.azurecr.io/invoice-review:v2 -f Dockerfile .
docker push acrinvoicereview.azurecr.io/invoice-review:v2

az containerapp update \
  -g rg-invoice-review -n ca-invoice-review \
  --image acrinvoicereview.azurecr.io/invoice-review:v2
```

Bump the tag each time (`v2`, `v3`, ...) so the revision history stays meaningful; `:latest`
makes it harder to tell what's actually running.

To change secrets or the volume mount, regenerate the full YAML manifest (see
`az containerapp show -g rg-invoice-review -n ca-invoice-review -o yaml` for the current spec as
a starting point) and apply with `az containerapp update --yaml <file>` -- CLI flags are ignored
when `--yaml` is passed.

---

## Diagnostics

```bash
# health / logs / revisions
curl https://ca-invoice-review.ambitiousgrass-0fe56c4f.northeurope.azurecontainerapps.io/health
az containerapp logs show -g rg-invoice-review -n ca-invoice-review --tail 100
az containerapp revision list -g rg-invoice-review -n ca-invoice-review -o table

# what's actually on the persistent file share
az storage file list --account-name stinvoicereview --share-name invoice-data --path "" -o table
```

---

## Teardown

Everything above lives in `rg-invoice-review` except the resource group itself, which predates
this deployment and likely holds other things -- don't delete the group blindly. To remove just
what this deployment added:

```bash
az containerapp delete -g rg-invoice-review -n ca-invoice-review --yes
az containerapp env delete -g rg-invoice-review -n cae-invoice-review --yes
az acr delete -g rg-invoice-review -n acrinvoicereview --yes
az storage account delete -g rg-invoice-review -n stinvoicereview --yes
```

Deleting the storage account deletes the file share and any uploaded documents still on it.
