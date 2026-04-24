
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.walletwallet_payload import strip_meta, validate_walletwallet_body


def normalize_slug(user_id: str) -> str:
    return user_id.strip().lower()


def cards_dir(base: Path) -> Path:
    return base / "data" / "cards"


def load_walletwallet_body(base: Path, user_id: str) -> dict[str, Any]:
    slug = normalize_slug(user_id)
    path = cards_dir(base) / f"{slug}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="User not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail="Invalid card JSON") from e
    if not isinstance(raw, dict):
        raise HTTPException(status_code=500, detail="Card JSON must be an object")

    stripped = strip_meta(raw)
    return validate_walletwallet_body(stripped)
