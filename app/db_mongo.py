"""MongoDB (Atlas) connection and passes collection."""

from __future__ import annotations

import os
import threading
from typing import Any

_client_lock = threading.Lock()
_client: Any = None
_db: Any = None
_passes: Any = None

DEFAULT_DB_NAME = "digital_card"
PASSES_COLLECTION = "passes"


def get_mongo_uri() -> str:
    return os.getenv("MONGODB_URI", "").strip()


def passes_collection():
    """
    Return the ``passes`` collection, or None if MONGODB_URI is unset
    (callers that need DB return 503).
    """
    uri = get_mongo_uri()
    if not uri:
        return None
    global _client, _db, _passes
    with _client_lock:
        if _passes is None:
            from pymongo import DESCENDING, MongoClient

            # Connection pooling: single long-lived client per process.
            _client = MongoClient(
                uri,
                serverSelectionTimeoutMS=10_000,
            )
            db_name = os.getenv("MONGO_DB_NAME", DEFAULT_DB_NAME).strip() or DEFAULT_DB_NAME
            _db = _client[db_name]
            _passes = _db[PASSES_COLLECTION]
            _passes.create_index(
                [("created_at", DESCENDING)],
                name="created_at_desc",
            )
        return _passes
