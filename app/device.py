"""Classify User-Agent into coarse device buckets for logs and routing."""

from __future__ import annotations

from typing import Literal

DeviceKind = Literal["ios", "android", "other"]


def classify_user_agent(user_agent: str | None) -> DeviceKind:
    """
    Best-effort classification for wallet targeting.
    Does not attempt to detect Samsung separately (out of POC scope).
    """
    ua = (user_agent or "").lower()
    if "iphone" in ua or "ipad" in ua or "ipod" in ua:
        return "ios"
    if "android" in ua:
        return "android"
    return "other"
