# rag/datasource/sqlstores/private_db_store.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class PrivateDBStore:
    """私有库与会话绑定存储"""

    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def create(
        self,
        *,
        app_id: str,
        owner_wallet_id: str,
        private_db_id: Optional[str] = None,
        status: str = "active",
    ) -> str:
        pid = private_db_id or str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO private_dbs(private_db_id, app_id, owner_wallet_id, status)
            VALUES (?, ?, ?, ?)
            """,
            (pid, app_id, owner_wallet_id, status),
        )
        return pid

    def get(self, private_db_id: str) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM private_dbs WHERE private_db_id = ?",
            (private_db_id,),
        )

    def list(
        self,
        *,
        owner_wallet_id: str,
        app_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Row]:
        clauses = ["owner_wallet_id = ?"]
        params: List[Any] = [owner_wallet_id]
        if app_id:
            clauses.append("app_id = ?")
            params.append(app_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}"
        params.extend([limit, offset])
        return self.conn.query_all(
            f"""
            SELECT * FROM private_dbs
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )

    def list_all(
        self,
        *,
        owner_wallet_id: Optional[str] = None,
        app_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Row]:
        clauses = []
        params: List[Any] = []

        col_prefix = "d." if session_id else ""
        if session_id:
            clauses.append("s.session_id = ?")
            params.append(session_id)
        if owner_wallet_id:
            clauses.append(f"{col_prefix}owner_wallet_id = ?")
            params.append(owner_wallet_id)
        if app_id:
            clauses.append(f"{col_prefix}app_id = ?")
            params.append(app_id)
        if status:
            clauses.append(f"{col_prefix}status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        if session_id:
            sql = f"""
            SELECT d.* FROM private_dbs d
            JOIN private_db_sessions s
              ON d.private_db_id = s.private_db_id
            {where}
            ORDER BY d.created_at DESC
            LIMIT ? OFFSET ?
            """
        else:
            sql = f"""
            SELECT * FROM private_dbs
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """
        return self.conn.query_all(sql, tuple(params))

    def get_by_session(self, *, app_id: str, owner_wallet_id: str, session_id: str) -> Optional[Row]:
        return self.conn.query_one(
            """
            SELECT d.* FROM private_dbs d
            JOIN private_db_sessions s
              ON d.private_db_id = s.private_db_id
             WHERE s.app_id = ? AND s.owner_wallet_id = ? AND s.session_id = ?
            """,
            (app_id, owner_wallet_id, session_id),
        )

    def bind_session(self, *, private_db_id: str, app_id: str, owner_wallet_id: str, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT INTO private_db_sessions(private_db_id, app_id, owner_wallet_id, session_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(app_id, owner_wallet_id, session_id) DO UPDATE SET
              private_db_id = excluded.private_db_id
            """,
            (private_db_id, app_id, owner_wallet_id, session_id),
        )

    def list_sessions(self, *, private_db_id: str, app_id: str, owner_wallet_id: str) -> List[Row]:
        return self.conn.query_all(
            """
            SELECT session_id, created_at
              FROM private_db_sessions
             WHERE private_db_id = ? AND app_id = ? AND owner_wallet_id = ?
             ORDER BY created_at DESC
            """,
            (private_db_id, app_id, owner_wallet_id),
        )

    def unbind_session(self, *, private_db_id: str, app_id: str, owner_wallet_id: str, session_id: str) -> int:
        cur = self.conn.execute(
            """
            DELETE FROM private_db_sessions
             WHERE private_db_id = ? AND app_id = ? AND owner_wallet_id = ? AND session_id = ?
            """,
            (private_db_id, app_id, owner_wallet_id, session_id),
        )
        return int(cur.rowcount or 0)

    def resolve_or_create(self, *, app_id: str, owner_wallet_id: str, session_id: str) -> str:
        row = self.get_by_session(app_id=app_id, owner_wallet_id=owner_wallet_id, session_id=session_id)
        if row and row.get("private_db_id"):
            return str(row["private_db_id"])
        private_db_id = self.create(app_id=app_id, owner_wallet_id=owner_wallet_id)
        self.bind_session(
            private_db_id=private_db_id,
            app_id=app_id,
            owner_wallet_id=owner_wallet_id,
            session_id=session_id,
        )
        return private_db_id

    def ensure_owner(self, *, private_db_id: str, app_id: str, owner_wallet_id: str) -> None:
        row = self.get(private_db_id)
        if not row:
            raise ValueError("private_db not found")
        if row.get("app_id") != app_id or row.get("owner_wallet_id") != owner_wallet_id:
            raise ValueError("private_db does not belong to app/owner")
