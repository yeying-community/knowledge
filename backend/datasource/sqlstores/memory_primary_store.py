# rag/datasource/sqlstores/memory_primary_store.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Optional, Dict, Any
from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class MemoryPrimaryStore:
    """主记忆摘要与统计"""

    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def upsert(
        self,
        memory_key: str,
        wallet_id: str,
        app_id: str,
        summary_threshold: Optional[int] = None,
    ) -> None:
        if summary_threshold is None:
            self.conn.execute(
                """
                INSERT INTO memory_primary(memory_key, wallet_id, app_id)
                VALUES (?, ?, ?)
                ON CONFLICT(memory_key) DO UPDATE SET
                  wallet_id = excluded.wallet_id,
                  app_id = excluded.app_id,
                  updated_at = datetime('now')
                """,
                (memory_key, wallet_id, app_id),
            )
            return

        self.conn.execute(
            """
            INSERT INTO memory_primary(memory_key, wallet_id, app_id, summary_threshold)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(memory_key) DO UPDATE SET
              wallet_id = excluded.wallet_id,
              app_id = excluded.app_id,
              summary_threshold = COALESCE(excluded.summary_threshold, memory_primary.summary_threshold),
              updated_at = datetime('now')
            """,
            (memory_key, wallet_id, app_id, summary_threshold),
        )

    def ensure_row(
        self,
        memory_key: str,
        wallet_id: str,
        app_id: str,
        summary_threshold: Optional[int] = None,
    ) -> None:
        self.upsert(
            memory_key=memory_key,
            wallet_id=wallet_id,
            app_id=app_id,
            summary_threshold=summary_threshold,
        )

    def set_summary_threshold(self, memory_key: str, summary_threshold: int) -> None:
        self.conn.execute(
            """
            UPDATE memory_primary
               SET summary_threshold = ?,
                   updated_at = datetime('now')
             WHERE memory_key = ?
            """,
            (int(summary_threshold), memory_key),
        )

    def update_summary(self, memory_key: str, summary_url: str, version: int) -> None:
        self.conn.execute(
            """
            UPDATE memory_primary
               SET summary_url = ?,
                   summary_version = ?,
                   last_summary_at = datetime('now'),
                   recent_qa_count = 0,
                   updated_at = datetime('now')
             WHERE memory_key = ?
            """,
            (summary_url, version, memory_key),
        )

    def bump_qa(self, memory_key: str, delta: int = 1) -> None:
        self.conn.execute(
            """
            UPDATE memory_primary
               SET recent_qa_count = recent_qa_count + ?,
                   total_qa_count  = total_qa_count + ?,
                   updated_at = datetime('now')
             WHERE memory_key = ?
            """,
            (delta, delta, memory_key),
        )

    def advance_index(self, memory_key: str, index: int) -> None:
        self.conn.execute(
            """
            UPDATE memory_primary
               SET last_summary_index = ?,
                   updated_at = datetime('now')
             WHERE memory_key = ?
            """,
            (index, memory_key),
        )

    def get(self, memory_key: str) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM memory_primary WHERE memory_key = ?",
            (memory_key,),
        )
