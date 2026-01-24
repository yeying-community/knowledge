# rag/datasource/sqlstores/ingestion_log_store.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class IngestionLogStore:
    """
    Ingestion log store
    - store ingest events for monitoring UI
    """

    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def create(
        self,
        *,
        status: str,
        message: str = "",
        wallet_id: Optional[str] = None,
        app_id: Optional[str] = None,
        kb_key: Optional[str] = None,
        collection: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        meta_json = json.dumps(meta, ensure_ascii=False) if meta else None
        self.conn.execute(
            """
            INSERT INTO ingestion_logs(wallet_id, app_id, kb_key, collection, status, message, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (wallet_id, app_id, kb_key, collection, status, message, meta_json),
        )

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        wallet_id: Optional[str] = None,
        app_id: Optional[str] = None,
        kb_key: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Row]:
        clauses = []
        params: List[Any] = []

        if wallet_id:
            clauses.append("wallet_id = ?")
            params.append(wallet_id)
        if app_id:
            clauses.append("app_id = ?")
            params.append(app_id)
        if kb_key:
            clauses.append("kb_key = ?")
            params.append(kb_key)
        if status:
            clauses.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        params.extend([limit, offset])
        return self.conn.query_all(
            f"""
            SELECT * FROM ingestion_logs
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )
