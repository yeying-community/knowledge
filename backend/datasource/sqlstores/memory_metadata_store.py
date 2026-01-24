# rag/datasource/sqlstores/memory_metadata_store.py
# -*- coding: utf-8 -*-
"""
MemoryMetadataStore
- 会话元信息
"""

from __future__ import annotations
import json
from typing import Optional, Dict, Any
from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class MemoryMetadataStore:
    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def upsert(
        self,
        memory_key: str,
        wallet_id: str,
        app_id: str,
        session_id: str,
        params: Optional[dict],
        status: str = "active",
    ) -> None:
        params_json = json.dumps(params or {}, ensure_ascii=False)
        self.conn.execute(
            """
            INSERT INTO memory_metadata(memory_key, wallet_id, app_id, session_id, params_json, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(memory_key) DO UPDATE SET
              params_json = excluded.params_json,
              status = excluded.status,
              updated_at = datetime('now')
            """,
            (memory_key, wallet_id, app_id, session_id, params_json, status),
        )

    def get(self, memory_key: str) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM memory_metadata WHERE memory_key = ?",
            (memory_key,),
        )
