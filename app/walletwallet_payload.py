
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

_ALLOWED_BARCODE = frozenset({"QR", "PDF417", "Aztec", "Code128"})


def strip_meta(raw: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in raw.items() if k != "meta"}


def validate_walletwallet_body(body: dict[str, Any]) -> dict[str, Any]:
    if "barcodeValue" not in body or not str(body["barcodeValue"]).strip():
        raise HTTPException(status_code=400, detail="card JSON: barcodeValue is required")
    bf = body.get("barcodeFormat")
    if not bf or str(bf).strip().upper() not in _ALLOWED_BARCODE:
        raise HTTPException(
            status_code=400,
            detail="card JSON: barcodeFormat must be one of QR, PDF417, Aztec, Code128",
        )
    normalized = dict(body)
    normalized["barcodeFormat"] = str(normalized["barcodeFormat"]).strip().upper()

    logo = normalized.get("logoText")
    title = normalized.get("title")
    prim = normalized.get("primaryFields")
    has_primary = isinstance(prim, list) and len(prim) > 0
    if not logo and not title and not has_primary:
        raise HTTPException(
            status_code=400,
            detail="card JSON: provide at least one of logoText, title, or non-empty primaryFields",
        )

    return normalized
