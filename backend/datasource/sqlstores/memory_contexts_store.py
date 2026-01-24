# rag/datasource/sqlstores/memory_contexts_store.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Optional, Dict, Any, List
import sqlite3
from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class MemoryContextsStore:
    """辅助记忆元信息（不存向量）"""

    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    # -------- 创建条目（幂等） --------
    def create(
        self,
        uid: str,
        memory_key: str,
        wallet_id: str,
        app_id: str,
        role: str,
        url: str,
        sha256: str,
        description: Optional[str] = None,
    ) -> Row:
        try:
            self.conn.execute(
                """
                INSERT INTO memory_contexts(uid, memory_key, wallet_id, app_id, role, url, description, content_sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (uid, memory_key, wallet_id, app_id, role, url, description, sha256),
            )
        except sqlite3.IntegrityError:
            # 幂等：sha256 或 uid 冲突
            row = self.get_by_sha256(sha256)
            if row:
                return row
            row = self.get(uid)
            if row:
                return row
            raise

        return self.get(uid)

    def upsert(
        self,
        uid: str,
        memory_key: str,
        wallet_id: str,
        app_id: str,
        role: str,
        url: str,
        description: Optional[str],
        content_sha256: str,
        qa_count: int = 1,
    ) -> Row:
        row = self.create(
            uid=uid,
            memory_key=memory_key,
            wallet_id=wallet_id,
            app_id=app_id,
            role=role,
            url=url,
            description=description,
            sha256=content_sha256,
        )
        if row and qa_count:
            self.bump_qa(uid, delta=qa_count)
        return row

    # -------- 查询 --------
    def get(self, uid: str) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM memory_contexts WHERE uid = ?",
            (uid,),
        )

    def get_by_sha256(self, sha256: str) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM memory_contexts WHERE content_sha256 = ?",
            (sha256,),
        )

    def list_by_memory(
        self,
        memory_key: str,
        *,
        is_summarized: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Row]:
        if is_summarized in (0, 1):
            return self.conn.query_all(
                """
                SELECT * FROM memory_contexts
                 WHERE memory_key = ? AND is_summarized = ?
                 ORDER BY created_at DESC
                 LIMIT ? OFFSET ?
                """,
                (memory_key, is_summarized, limit, offset),
            )
        return self.conn.query_all(
            """
            SELECT * FROM memory_contexts
             WHERE memory_key = ?
             ORDER BY created_at DESC
             LIMIT ? OFFSET ?
            """,
            (memory_key, limit, offset),
        )

    def count_by_memory(
        self,
        memory_key: str,
        *,
        is_summarized: Optional[int] = None,
    ) -> int:
        if is_summarized in (0, 1):
            row = self.conn.query_one(
                """
                SELECT COUNT(*) AS total FROM memory_contexts
                 WHERE memory_key = ? AND is_summarized = ?
                """,
                (memory_key, is_summarized),
            )
        else:
            row = self.conn.query_one(
                """
                SELECT COUNT(*) AS total FROM memory_contexts
                 WHERE memory_key = ?
                """,
                (memory_key,),
            )
        return int(row["total"] if row else 0)

    def list_all_unsummarized(self, memory_key):
        return self.conn.query_all(
            """
            SELECT * FROM memory_contexts
            WHERE memory_key = ? AND is_summarized = 0
            ORDER BY created_at ASC
        """,
            (memory_key,)
        )

    # -------- 状态更新 --------
    def mark_summarized(self, uid: str) -> None:
        self.conn.execute(
            """
            UPDATE memory_contexts SET
              is_summarized = 1,
              summarized_at = datetime('now'),
              updated_at = datetime('now')
             WHERE uid = ?
            """,
            (uid,),
        )

    def mark_summarized_by_memory(self, memory_key: str) -> None:
        self.conn.execute(
            """
            UPDATE memory_contexts SET
              is_summarized = 1,
              summarized_at = datetime('now'),
              updated_at = datetime('now')
             WHERE memory_key = ? AND is_summarized = 0
            """,
            (memory_key,),
        )

    def bump_qa(self, uid: str, delta: int = 1) -> None:
        self.conn.execute(
            """
            UPDATE memory_contexts SET
              qa_count = qa_count + ?,
              updated_at = datetime('now')
             WHERE uid = ?
            """,
            (delta, uid),
        )

    def update_description(self, uid: str, desc: Optional[str]) -> None:
        self.conn.execute(
            """
            UPDATE memory_contexts SET
              description = ?,
              updated_at = datetime('now')
             WHERE uid = ?
            """,
            (desc, uid),
        )

    def update_fields(
        self,
        uid: str,
        *,
        description: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Optional[Row]:
        updates = []
        params: list[Any] = []
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if role is not None:
            updates.append("role = ?")
            params.append(role)
        if not updates:
            return self.get(uid)
        params.append(uid)
        self.conn.execute(
            f"""
            UPDATE memory_contexts SET
              {', '.join(updates)},
              updated_at = datetime('now')
             WHERE uid = ?
            """,
            tuple(params),
        )
        return self.get(uid)
