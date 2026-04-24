
from __future__ import annotations

import os
import threading
from typing import Any

_client_lock = threading.Lock()
_client: Any = None
_db: Any = None
_passes: Any = None
_settings: Any = None

DEFAULT_DB_NAME = "digital_card"
PASSES_COLLECTION = "passes"
SETTINGS_COLLECTION = "settings"
SETTINGS_ID = "singleton"


def get_mongo_uri() -> str:
    return os.getenv("MONGODB_URI", "").strip()


def passes_collection():
    uri = get_mongo_uri()
    if not uri:
        return None
    global _client, _db, _passes, _settings
    with _client_lock:
        if _passes is not None:
            return _passes

        from fastapi import HTTPException
        from pymongo import DESCENDING, MongoClient
        from pymongo.errors import PyMongoError

        new_client: Any
        new_db: Any
        new_passes: Any
        new_settings: Any

        try:
            import certifi

            new_client = MongoClient(
                uri,
                serverSelectionTimeoutMS=10_000,
                tlsCAFile=certifi.where(),
            )
            db_name = os.getenv("MONGO_DB_NAME", DEFAULT_DB_NAME).strip() or DEFAULT_DB_NAME
            new_db = new_client[db_name]
            new_passes = new_db[PASSES_COLLECTION]
            new_passes.create_index(
                [("created_at", DESCENDING)],
                name="created_at_desc",
            )
            new_settings = new_db[SETTINGS_COLLECTION]
            new_settings.update_one(
                {"_id": SETTINGS_ID},
                {"$setOnInsert": {"active_pass_id": None}},
                upsert=True,
            )
        except PyMongoError as e:
            msg = f"{e!s}"
            hint = (
                " In Atlas, open your cluster → Connect → get a new connection string, "
                "and set MONGODB_URI in Render. If the cluster was deleted, create a new one or fix the host."
            )
            if "DNS" in msg or "_mongodb._tcp" in msg or "does not exist" in msg:
                hint = " Your SRV host is wrong or the cluster no longer exists — copy a **fresh** MONGODB_URI from MongoDB Atlas → Database → Connect."
            elif "CERTIFICATE_VERIFY_FAILED" in msg or "certificate verify failed" in msg:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Could not verify MongoDB Atlas TLS certificates. "
                        "Run `pip install -U certifi pymongo`, reinstall the app (`pip install -e .`), and restart the server."
                    ),
                ) from e
            raise HTTPException(
                status_code=503,
                detail=(msg + hint)[:2000],
            ) from e

        _client = new_client
        _db = new_db
        _passes = new_passes
        _settings = new_settings
        return _passes


def settings_collection():
    p = passes_collection()
    if p is None:
        return None
    return _settings
