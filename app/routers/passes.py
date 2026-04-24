
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from bson import Binary, ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.db_mongo import SETTINGS_ID, passes_collection, settings_collection
from app.routers.settings import read_active_pass_id
from app.deps import walletwallet_api_key
from app.walletwallet_client import fetch_pkpass_or_raise
from app.walletwallet_payload import validate_walletwallet_body

router = APIRouter(prefix="/api", tags=["passes"])


def _col_or_503():
    c = passes_collection()
    if c is None:
        raise HTTPException(status_code=503, detail="MONGODB_URI is not set")
    return c


def _dt_iso_utc(d: datetime) -> str:
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class PassListItem(BaseModel):
    id: str
    label: str | None = None
    created_at: str


@router.post(
    "/passes",
    response_model=PassListItem,
)
def create_pass(body: dict[str, Any]) -> PassListItem:
    col = _col_or_503()
    raw = deepcopy(body)
    label_val = raw.pop("label", None)
    label: str | None
    if label_val is None:
        label = None
    elif isinstance(label_val, str) and label_val.strip():
        label = label_val.strip()[:200]
    else:
        label = None

    wbody = validate_walletwallet_body(raw)
    api_key = walletwallet_api_key()
    pkpass = fetch_pkpass_or_raise(api_key, wbody)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    res = col.insert_one(
        {
            "label": label,
            "request_json": wbody,
            "pkpass": Binary(pkpass),
            "created_at": now,
        }
    )
    oid = res.inserted_id
    assert isinstance(oid, ObjectId)
    return PassListItem(
        id=str(oid),
        label=label,
        created_at=_dt_iso_utc(now),
    )


def _label_to_str(lab: Any) -> str | None:
    if lab is None:
        return None
    if isinstance(lab, str):
        return lab
    return str(lab)[:200]


def _coerce_created_at(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v
    if v is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, tz=timezone.utc).replace(tzinfo=None)
    if isinstance(v, str):
        s = v.strip()
        if s:
            try:
                d = datetime.fromisoformat(s.replace("Z", "+00:00"))
                return d.replace(tzinfo=None) if d.tzinfo else d
            except ValueError:
                pass
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize_doc(doc: dict[str, Any]) -> PassListItem:
    oid = doc.get("_id")
    if not isinstance(oid, ObjectId):
        raise HTTPException(status_code=500, detail="Invalid pass document: bad _id")
    cr = _coerce_created_at(doc.get("created_at"))
    return PassListItem(
        id=str(oid),
        label=_label_to_str(doc.get("label")),
        created_at=_dt_iso_utc(cr),
    )


@router.get(
    "/passes",
    response_model=list[PassListItem],
)
def list_passes() -> list[PassListItem]:
    from pymongo.errors import PyMongoError

    col = _col_or_503()
    out: list[PassListItem] = []
    try:
        for doc in col.find({}, {"pkpass": 0, "request_json": 0}).sort("created_at", -1):
            try:
                out.append(_serialize_doc(doc))
            except HTTPException as e:
                if e.status_code == 500:
                    continue
                raise
    except PyMongoError as e:
        raise HTTPException(
            status_code=503,
            detail=f"MongoDB error: {e!s}. Check MONGODB_URI, Atlas network access, and that the user can read the database.",
        ) from e
    return out


@router.get(
    "/passes/{pass_id}/pkpass",
    response_class=Response,
    responses={200: {"content": {"application/vnd.apple.pkpass": {}}}},
)
def download_pkpass(pass_id: str) -> Response:
    t = pass_id.strip()
    if len(t) != 24 or not ObjectId.is_valid(t):
        raise HTTPException(status_code=400, detail="Invalid pass id")
    col = _col_or_503()
    doc = col.find_one({"_id": ObjectId(t)})
    if not doc or "pkpass" not in doc:
        raise HTTPException(status_code=404, detail="Pass not found")
    raw = doc["pkpass"]
    blob: bytes = raw if isinstance(raw, (bytes, memoryview)) else bytes(raw)
    return Response(
        content=blob,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": 'attachment; filename="card.pkpass"'},
    )


@router.delete(
    "/passes/{pass_id}",
    status_code=204,
    response_class=Response,
)
def delete_pass(pass_id: str) -> Response:
    t = pass_id.strip()
    if len(t) != 24 or not ObjectId.is_valid(t):
        raise HTTPException(status_code=400, detail="Invalid pass id")
    col = _col_or_503()
    oid = ObjectId(t)
    res = col.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pass not found")
    sc = settings_collection()
    if sc is not None and read_active_pass_id() == t:
        sc.update_one(
            {"_id": SETTINGS_ID},
            {"$set": {"active_pass_id": None}},
            upsert=True,
        )
    return Response(status_code=204)
