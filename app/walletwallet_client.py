
from __future__ import annotations

import json
import logging

import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)

WW_BASE = "https://api.walletwallet.dev"
PKPASS_PATH = "/api/pkpass"


def fetch_pkpass_or_raise(api_key: str, body: dict[str, object]) -> bytes:
    url = f"{WW_BASE.rstrip('/')}{PKPASS_PATH}"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=60)
    except requests.RequestException as e:
        logger.warning("WalletWallet request failed: %s", type(e).__name__)
        raise HTTPException(status_code=502, detail="WalletWallet request failed") from e

    if resp.status_code == 200:
        return resp.content

    err_detail = "WalletWallet error"
    try:
        data = resp.json()
        if isinstance(data, dict) and data.get("error"):
            err_detail = str(data["error"])[:500]
    except json.JSONDecodeError:
        err_detail = (resp.text or "")[:200] or err_detail

    logger.warning(
        "WalletWallet HTTP %s: %s",
        resp.status_code,
        err_detail[:100],
    )

    if resp.status_code == 400:
        raise HTTPException(status_code=400, detail=err_detail)
    if resp.status_code == 401:
        raise HTTPException(status_code=502, detail="WalletWallet unauthorized (check API key)")
    if resp.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="WalletWallet rate limit exceeded; try again later",
        )

    raise HTTPException(status_code=502, detail="WalletWallet service error")
