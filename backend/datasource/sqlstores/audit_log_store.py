# rag/datasource/sqlstores/audit_log_store.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class AuditLogStore:
    """
    Audit log store
    - store config changes & private db operations
    """

    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def create(
        self,
        *,
        action: str,
        operator_wallet_id: Optional[str] = None,
        app_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        meta_json = json.dumps(meta, ensure_ascii=False) if meta else None
        self.conn.execute(
            """
            INSERT INTO audit_logs(operator_wallet_id, app_id, entity_type, entity_id, action, meta_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (operator_wallet_id, app_id, entity_type, entity_id, action, meta_json),
        )

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        app_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        operator_wallet_id: Optional[str] = None,
    ) -> List[Row]:
        clauses = []
        params: List[Any] = []

        if app_id:
            clauses.append("app_id = ?")
            params.append(app_id)
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if entity_id:
            clauses.append("entity_id = ?")
            params.append(entity_id)
        if action:
            clauses.append("action = ?")
            params.append(action)
        if operator_wallet_id:
            clauses.append("operator_wallet_id = ?")
            params.append(operator_wallet_id)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])

        return self.conn.query_all(
            f"""
            SELECT * FROM audit_logs
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )
