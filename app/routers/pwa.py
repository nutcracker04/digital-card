
from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["pwa"])


class PwaConfigResponse(BaseModel):
    brandName: str
    orchestratorUrl: str


@router.get("/pwa-config", response_model=PwaConfigResponse)
def get_pwa_config() -> PwaConfigResponse:
    brand = os.getenv("PWA_BRAND_NAME", "PassForge").strip() or "PassForge"
    orch = os.getenv("PWA_ORCHESTRATOR_URL", "").strip().rstrip("/")
    return PwaConfigResponse(brandName=brand, orchestratorUrl=orch)
