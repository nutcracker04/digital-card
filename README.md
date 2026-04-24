# digital-card (FastAPI + optional Mongo + PWA)

- **API** (e.g. on Render): tap URLs and stored passes.
- **PWA** ([`frontend/`](frontend/)) is also served by the **same** FastAPI process: open `https://<your-service>.onrender.com/` after deploy. The “Pass server (orchestrator)” in settings defaults to **this origin** (`location.origin`) so the UI talks to the app without extra configuration. You can still host the PWA elsewhere (Netlify, etc.) and set the orchestrator URL to your API base.

## Stable NFC (one tag URL)

Program the tag with:

`https://<your-host>/v1/tap/current` (alias: `/v1/card/current`)

That always resolves the **active** pass in Mongo (set in the PWA: **Set active** on a pass, or `PUT /api/settings/active-pass`). It does not require reprogramming when you switch passes. Per–pass direct URLs remain `GET /v1/tap/<24-hex ObjectId>`.

## Deploy (Render)

Build: `pip install --upgrade pip && pip install .`  
Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Environment (dashboard):**

| Variable | Notes |
|----------|--------|
| `WALLETWALLET_API_KEY` | Required: upstream WalletWallet for `POST /api/passes` |
| `MONGODB_URI` | Required for server-backed passes, settings, and `/v1/tap/*` for ObjectIds and `/v1/tap/current` |
| `MONGO_DB_NAME` | Optional, default `digital_card` |
| `CORS_ORIGINS` | `*` is fine for same-Render deploy; or list your PWA origin if you split frontend and API across hosts. |

## Notable API routes

- `GET /v1/tap/current` — stable NFC: serves active pass (same as `/v1/tap/{id}` for that id).
- `GET /api/passes` — list pass metadata.
- `POST /api/passes` — create (WalletWallet + store in Mongo).
- `GET /api/passes/{id}/pkpass` — download stored `.pkpass` for the PWA.
- `GET /api/settings`, `PUT /api/settings/active-pass` — `{"active_pass_id": "<id>" | null }`.

**Security:** `POST/GET/PUT` are unprotected in the default app; do not expose to the public internet without your own auth or network controls if the data is sensitive.

## Local

```bash
cd digital-card
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e .
# copy env from .env.example
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Frontend

With the current app, the repo’s `frontend/` folder is mounted at **`/`** by the server (static files, `index.html` as default). A separate static site on Render is not required. For a pure static build elsewhere, upload the `frontend/` files and set **Pass server** to your API’s base URL.
