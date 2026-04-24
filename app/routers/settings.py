
from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.db_mongo import SETTINGS_ID, passes_collection, settings_collection

router = APIRouter(prefix="/api", tags=["settings"])


def _s_or_503():
    c = settings_collection()
    if c is None:
        raise HTTPException(status_code=503, detail="MONGODB_URI is not set")
    return c


def _as_object_id(p: str) -> ObjectId:
    t = p.strip()
    if len(t) != 24 or not ObjectId.is_valid(t):
        raise HTTPException(status_code=400, detail="active_pass_id must be a 24-hex ObjectId or null")
    return ObjectId(t)


class SettingsResponse(BaseModel):
    active_pass_id: str | None = None


class ActivePassUpdate(BaseModel):
    active_pass_id: str | None = None

    @field_validator("active_pass_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return v


def read_active_pass_id() -> str | None:
    c = settings_collection()
    if c is None:
        return None
    doc = c.find_one({"_id": SETTINGS_ID})
    if not doc:
        return None
    v = doc.get("active_pass_id")
    if v is None:
        return None
    if isinstance(v, ObjectId):
        return str(v)
    return str(v) if v else None


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    _s_or_503()
    return SettingsResponse(active_pass_id=read_active_pass_id())


@router.put("/settings/active-pass", response_model=SettingsResponse)
def put_active_pass(body: ActivePassUpdate) -> SettingsResponse:
    sc = _s_or_503()
    pcol = passes_collection()
    if pcol is None:
        raise HTTPException(status_code=503, detail="MONGODB_URI is not set")
    if body.active_pass_id is not None:
        oid = _as_object_id(body.active_pass_id)
        if not pcol.find_one({"_id": oid}):
            raise HTTPException(status_code=400, detail="No pass with this id")
        to_set: object = oid
    else:
        to_set = None
    sc.update_one(
        {"_id": SETTINGS_ID},
        {"$set": {"active_pass_id": to_set}},
        upsert=True,
    )
    return SettingsResponse(active_pass_id=read_active_pass_id())
