
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.db_mongo import passes_collection
from app.device import classify_user_agent
from app.deps import walletwallet_api_key
from app.registry import load_walletwallet_body, normalize_slug
from app.routers.passes import router as passes_router
from app.routers.pwa import router as pwa_router
from app.routers.settings import read_active_pass_id
from app.routers.settings import router as settings_router
from app.walletwallet_client import fetch_pkpass_or_raise


def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    cwd = Path.cwd()
    if (cwd / "frontend" / "index.html").is_file():
        return cwd
    for base in (here.parent.parent, cwd.parent):
        if (base / "frontend" / "index.html").is_file() and (base / "app" / "main.py").is_file():
            return base
    return here.parent.parent


PROJECT_ROOT = _find_project_root()

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("wallet.tap")

app = FastAPI(title="NFC Wallet Orchestrator", version="0.4.0")
app.include_router(passes_router)
app.include_router(settings_router)
app.include_router(pwa_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)


def _is_object_id_hex(s: str) -> bool:
    t = s.strip()
    if len(t) != 24:
        return False
    return bool(ObjectId.is_valid(t))


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    return response


def _log_tap(
    request: Request,
    *,
    slug: str,
    device: str,
    status_code: int,
    backend: str = "walletwallet",
) -> None:
    line = json.dumps(
        {
            "event": "tap_resolve",
            "request_id": getattr(request.state, "request_id", None),
            "slug": slug,
            "device": device,
            "backend": backend,
            "status": status_code,
        },
        separators=(",", ":"),
    )
    logger.info(line)


def _resolve_tap_from_mongo(
    pass_id: str, request: Request, *, col
) -> Response | JSONResponse:
    doc = col.find_one({"_id": ObjectId(pass_id.strip())})
    if not doc or "pkpass" not in doc:
        raise HTTPException(status_code=404, detail="Pass not found")

    slug = pass_id.strip()
    device = classify_user_agent(request.headers.get("user-agent"))
    raw_pk = doc["pkpass"]
    pkpass: bytes
    if isinstance(raw_pk, bytes):
        pkpass = raw_pk
    else:
        pkpass = bytes(raw_pk)

    if device != "ios":
        out: dict[str, object] = {
            "message": "Apple Wallet passes from this link open on iPhone or iPad. Open this URL in Safari on an iPhone to add the pass.",
            "id": slug,
        }
        lab = doc.get("label")
        if isinstance(lab, str) and lab.strip():
            out["label"] = lab
        _log_tap(
            request,
            slug=slug,
            device=device,
            status_code=200,
            backend="mongo",
        )
        return JSONResponse(content=out)

    resp = Response(
        content=pkpass,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": 'attachment; filename="card.pkpass"'},
    )
    _log_tap(
        request,
        slug=slug,
        device=device,
        status_code=200,
        backend="mongo",
    )
    return resp


def _resolve_tap(user_id: str, request: Request) -> Response | JSONResponse:
    if _is_object_id_hex(user_id):
        col = passes_collection()
        if col is None:
            raise HTTPException(
                status_code=503,
                detail="MONGODB_URI is not set; cannot resolve stored pass id",
            )
        return _resolve_tap_from_mongo(user_id, request, col=col)

    slug = normalize_slug(user_id)
    device = classify_user_agent(request.headers.get("user-agent"))

    body = load_walletwallet_body(PROJECT_ROOT, user_id)

    if device != "ios":
        payload = {
            "message": "Apple Wallet passes from this link open on iPhone or iPad. Open this URL in Safari on an iPhone to add the pass.",
            "slug": slug,
        }
        _log_tap(request, slug=slug, device=device, status_code=200)
        return JSONResponse(content=payload)

    api_key = walletwallet_api_key()
    pkpass = fetch_pkpass_or_raise(api_key, body)
    resp = Response(
        content=pkpass,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": 'attachment; filename="card.pkpass"'},
    )
    _log_tap(request, slug=slug, device=device, status_code=200)
    return resp


@app.get("/v1/tap/current", response_model=None)
def tap_current(request: Request) -> Response | JSONResponse:
    col = passes_collection()
    if col is None:
        raise HTTPException(
            status_code=503,
            detail="MONGODB_URI is not set; cannot resolve /v1/tap/current",
        )
    ap = read_active_pass_id()
    if not ap:
        raise HTTPException(
            status_code=404,
            detail="No active pass. Set one via PUT /api/settings/active-pass or the PWA.",
        )
    return _resolve_tap_from_mongo(ap, request, col=col)


@app.get("/v1/card/current", response_model=None)
def card_current(request: Request) -> Response | JSONResponse:
    return tap_current(request)


@app.get("/v1/tap/{user_id}")
def tap_card(user_id: str, request: Request):
    return _resolve_tap(user_id, request)


@app.get("/v1/card/{user_id}")
def tap_card_alias(user_id: str, request: Request):
    return _resolve_tap(user_id, request)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


FRONTEND_DIR = PROJECT_ROOT / "frontend"
if (FRONTEND_DIR / "index.html").is_file():
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="pwa",
    )
else:
    logging.getLogger("wallet.tap").warning("frontend/ not found at %s — PWA not mounted", FRONTEND_DIR)
