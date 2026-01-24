# rag/datasource/sqlstores/identity_session_store.py
# -*- coding: utf-8 -*-
"""
IdentitySessionStore
- 管理 wallet_id + app_id + session_id ↔ memory_key 的映射
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class IdentitySessionStore:
    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def upsert(self, memory_key: str, wallet_id: str, app_id: str, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT INTO identity_session(memory_key, wallet_id, app_id, session_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(memory_key) DO UPDATE SET
              wallet_id = excluded.wallet_id,
              app_id = excluded.app_id,
              session_id = excluded.session_id,
              updated_at = datetime('now')
            """,
            (memory_key, wallet_id, app_id, session_id),
        )

    def get_by_memory_key(self, memory_key: str) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM identity_session WHERE memory_key = ?",
            (memory_key,),
        )

    def get(self, wallet_id: str, app_id: str, session_id: str) -> Optional[Row]:
        return self.conn.query_one(
            """
            SELECT * FROM identity_session
             WHERE wallet_id = ? AND app_id = ? AND session_id = ?
            """,
            (wallet_id, app_id, session_id),
        )

    def list(
        self,
        *,
        app_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Row]:
        conditions = []
        params: list[Any] = []
        if app_id:
            conditions.append("s.app_id = ?")
            params.append(app_id)
        if wallet_id:
            conditions.append("s.wallet_id = ?")
            params.append(wallet_id)
        if session_id:
            conditions.append("s.session_id = ?")
            params.append(session_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT
              s.*,
              COALESCE(m.message_count, 0) AS message_count,
              m.last_message_at
            FROM identity_session s
            LEFT JOIN (
              SELECT memory_key,
                     COUNT(*) AS message_count,
                     MAX(created_at) AS last_message_at
                FROM memory_contexts
               GROUP BY memory_key
            ) m ON s.memory_key = m.memory_key
            {where}
            ORDER BY s.updated_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self.conn.query_all(sql, tuple(params))

    def count(
        self,
        *,
        app_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> int:
        conditions = []
        params: list[Any] = []
        if app_id:
            conditions.append("app_id = ?")
            params.append(app_id)
        if wallet_id:
            conditions.append("wallet_id = ?")
            params.append(wallet_id)
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        row = self.conn.query_one(
            f"SELECT COUNT(*) AS total FROM identity_session {where}",
            tuple(params),
        )
        return int(row["total"] if row else 0)
