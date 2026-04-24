
from __future__ import annotations

import os

from fastapi import HTTPException


def walletwallet_api_key() -> str:
    key = os.getenv("WALLETWALLET_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="WALLETWALLET_API_KEY is not set",
        )
    return key
