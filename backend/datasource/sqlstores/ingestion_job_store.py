# rag/datasource/sqlstores/ingestion_job_store.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class IngestionJobStore:
    """摄取作业存储（队列 + 运行记录）"""

    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def create(
        self,
        *,
        wallet_id: str,
        data_wallet_id: Optional[str] = None,
        private_db_id: Optional[str] = None,
        app_id: str,
        kb_key: str,
        job_type: str,
        source_url: Optional[str] = None,
        file_type: Optional[str] = None,
        content_sha256: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> int:
        options_json = json.dumps(options or {}, ensure_ascii=False)
        cur = self.conn.execute(
            """
            INSERT INTO ingestion_jobs(
              wallet_id, data_wallet_id, private_db_id, app_id, kb_key, job_type,
              source_url, file_type, content_sha256, status, options_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                wallet_id,
                data_wallet_id,
                private_db_id,
                app_id,
                kb_key,
                job_type,
                source_url,
                file_type,
                content_sha256,
                options_json,
            ),
        )
        return int(cur.lastrowid)

    def get(self, job_id: int) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM ingestion_jobs WHERE id = ?",
            (job_id,),
        )

    def list(
        self,
        *,
        wallet_id: Optional[str] = None,
        data_wallet_id: Optional[str] = None,
        private_db_id: Optional[str] = None,
        app_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Row]:
        clauses = []
        params: List[Any] = []
        if wallet_id:
            clauses.append("wallet_id = ?")
            params.append(wallet_id)
        if data_wallet_id:
            clauses.append("data_wallet_id = ?")
            params.append(data_wallet_id)
        if private_db_id:
            clauses.append("private_db_id = ?")
            params.append(private_db_id)
        if app_id:
            clauses.append("app_id = ?")
            params.append(app_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        return self.conn.query_all(
            f"""
            SELECT * FROM ingestion_jobs
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )

    def mark_running(self, job_id: int) -> None:
        self.conn.execute(
            """
            UPDATE ingestion_jobs
               SET status = 'running',
                   started_at = COALESCE(started_at, datetime('now')),
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (job_id,),
        )

    def mark_success(self, job_id: int, result: Optional[dict] = None) -> None:
        result_json = json.dumps(result or {}, ensure_ascii=False)
        self.conn.execute(
            """
            UPDATE ingestion_jobs
               SET status = 'success',
                   result_json = ?,
                   finished_at = datetime('now'),
                   updated_at = datetime('now'),
                   error_message = NULL
             WHERE id = ?
            """,
            (result_json, job_id),
        )

    def mark_failed(self, job_id: int, error_message: str) -> None:
        self.conn.execute(
            """
            UPDATE ingestion_jobs
               SET status = 'failed',
                   error_message = ?,
                   finished_at = datetime('now'),
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (error_message, job_id),
        )

    def append_run(
        self,
        *,
        job_id: int,
        status: str,
        message: str = "",
        meta: Optional[dict] = None,
    ) -> None:
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        self.conn.execute(
            """
            INSERT INTO ingestion_job_runs(job_id, status, message, meta_json)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, status, message, meta_json),
        )

    def list_runs(self, job_id: int, limit: int = 50, offset: int = 0) -> List[Row]:
        return self.conn.query_all(
            """
            SELECT * FROM ingestion_job_runs
             WHERE job_id = ?
             ORDER BY created_at DESC
             LIMIT ? OFFSET ?
            """,
            (job_id, limit, offset),
        )
