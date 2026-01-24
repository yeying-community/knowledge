# rag/datasource/connections/sqlite_connection.py
# -*- coding: utf-8 -*-
"""
SQLiteConnection（核心版）
- 初始化 identity + memory 相关表
- 不包含业务表
"""

from __future__ import annotations
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, Optional


CORE_DDL = r"""
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

-- 身份层： wallet_id + app_id + session_id → memory_key
CREATE TABLE IF NOT EXISTS identity_session (
  memory_key   TEXT PRIMARY KEY,
  wallet_id    TEXT NOT NULL,
  app_id       TEXT NOT NULL,
  session_id   TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(wallet_id, app_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_identity_session_wallet_app
  ON identity_session (wallet_id, app_id, created_at DESC);

-- 会话元信息（替代 mem_registry）
CREATE TABLE IF NOT EXISTS memory_metadata (
  memory_key    TEXT PRIMARY KEY,
  wallet_id     TEXT NOT NULL,
  app_id        TEXT NOT NULL,
  session_id    TEXT NOT NULL,
  params_json   TEXT,
  status        TEXT NOT NULL DEFAULT 'active',
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(wallet_id, app_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_metadata_wallet
  ON memory_metadata (wallet_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_metadata_app
  ON memory_metadata (app_id, created_at DESC);

-- 主记忆摘要
CREATE TABLE IF NOT EXISTS memory_primary (
  memory_key          TEXT PRIMARY KEY,
  wallet_id           TEXT NOT NULL,
  app_id              TEXT NOT NULL,
  summary_url         TEXT,
  summary_version     INTEGER NOT NULL DEFAULT 0,
  summary_threshold   INTEGER NOT NULL DEFAULT 0,
  recent_qa_count     INTEGER NOT NULL DEFAULT 0,
  total_qa_count      INTEGER NOT NULL DEFAULT 0,
  last_summary_index  INTEGER NOT NULL DEFAULT 0,
  last_summary_at     TEXT,
  created_at          TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_primary_wallet
  ON memory_primary (wallet_id, created_at DESC);

-- 辅助记忆目录（存元信息，不存向量）
CREATE TABLE IF NOT EXISTS memory_contexts (
  uid            TEXT PRIMARY KEY,
  memory_key     TEXT NOT NULL,
  wallet_id      TEXT NOT NULL,
  app_id         TEXT NOT NULL,
  role           TEXT NOT NULL,
  url            TEXT NOT NULL,
  description    TEXT,
  content_sha256 TEXT NOT NULL UNIQUE,
  qa_count       INTEGER NOT NULL DEFAULT 0,
  is_summarized  INTEGER NOT NULL DEFAULT 0,
  summarized_at  TEXT,
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_contexts_memory_created
  ON memory_contexts (memory_key, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_contexts_wallet_created
  ON memory_contexts (wallet_id, created_at DESC);
  
-- App 注册表（记录哪些 app 被启用）
CREATE TABLE IF NOT EXISTS app_registry (
  app_id       TEXT PRIMARY KEY,
  owner_wallet_id TEXT,
  status       TEXT NOT NULL DEFAULT 'active',
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 摄取任务日志
CREATE TABLE IF NOT EXISTS ingestion_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  wallet_id   TEXT,
  app_id      TEXT,
  kb_key      TEXT,
  collection  TEXT,
  status      TEXT NOT NULL,
  message     TEXT,
  meta_json   TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ingestion_logs_created
  ON ingestion_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingestion_logs_app_kb
  ON ingestion_logs (app_id, kb_key, created_at DESC);

-- 私有数据库（按 app_id + owner_wallet_id 隔离）
CREATE TABLE IF NOT EXISTS private_dbs (
  private_db_id   TEXT PRIMARY KEY,
  app_id          TEXT NOT NULL,
  owner_wallet_id TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'active',
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_private_dbs_owner
  ON private_dbs (owner_wallet_id, app_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_private_dbs_app
  ON private_dbs (app_id, created_at DESC);

-- 私有库与会话绑定（一个 session_id 只归属一个 private_db）
CREATE TABLE IF NOT EXISTS private_db_sessions (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  private_db_id  TEXT NOT NULL,
  app_id         TEXT NOT NULL,
  owner_wallet_id TEXT NOT NULL,
  session_id     TEXT NOT NULL,
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(app_id, owner_wallet_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_private_db_sessions_db
  ON private_db_sessions (private_db_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_private_db_sessions_owner
  ON private_db_sessions (owner_wallet_id, app_id, created_at DESC);

-- 摄取作业队列表
CREATE TABLE IF NOT EXISTS ingestion_jobs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  wallet_id     TEXT NOT NULL,
  data_wallet_id TEXT,
  private_db_id TEXT,
  app_id        TEXT NOT NULL,
  kb_key        TEXT NOT NULL,
  job_type      TEXT NOT NULL DEFAULT 'kb_ingest',
  source_url    TEXT,
  file_type     TEXT,
  content_sha256 TEXT,
  status        TEXT NOT NULL DEFAULT 'pending',
  options_json  TEXT,
  result_json   TEXT,
  error_message TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
  started_at    TEXT,
  finished_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status
  ON ingestion_jobs (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_wallet
  ON ingestion_jobs (wallet_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_app
  ON ingestion_jobs (app_id, created_at DESC);


-- 摄取作业执行记录
CREATE TABLE IF NOT EXISTS ingestion_job_runs (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id     INTEGER NOT NULL,
  status     TEXT NOT NULL,
  message    TEXT,
  meta_json  TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ingestion_job_runs_job
  ON ingestion_job_runs (job_id, created_at DESC);

-- KB 文档元数据（与向量存储解耦）
CREATE TABLE IF NOT EXISTS kb_documents (
  doc_id        TEXT PRIMARY KEY,
  app_id        TEXT NOT NULL,
  kb_key        TEXT NOT NULL,
  wallet_id     TEXT,
  private_db_id TEXT,
  source_url    TEXT,
  source_type   TEXT,
  source_id     TEXT,
  file_type     TEXT,
  content_sha256 TEXT,
  status        TEXT NOT NULL DEFAULT 'active',
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_kb_documents_app_kb
  ON kb_documents (app_id, kb_key, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_kb_documents_wallet
  ON kb_documents (wallet_id, created_at DESC);


CREATE INDEX IF NOT EXISTS idx_kb_documents_status
  ON kb_documents (status, created_at DESC);
"""


class SQLiteConnection:
    """SQLite 核心连接层（无业务，无逻辑删除）"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        default_path = Path(os.getcwd()) / "db" / "rag.sqlite3"
        self.db_path = Path(db_path or os.getenv("RAG_DB_PATH", default_path))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path.as_posix(), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()

        self._init_core_schema()

    def _init_core_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(CORE_DDL)
        self._ensure_column("memory_primary", "summary_threshold", "summary_threshold INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("app_registry", "owner_wallet_id", "owner_wallet_id TEXT")
        self._ensure_column("ingestion_logs", "wallet_id", "wallet_id TEXT")
        self._ensure_column("ingestion_jobs", "data_wallet_id", "data_wallet_id TEXT")
        self._ensure_column("ingestion_jobs", "private_db_id", "private_db_id TEXT")
        self._ensure_column("kb_documents", "private_db_id", "private_db_id TEXT")
        self._ensure_index(
            "CREATE INDEX IF NOT EXISTS idx_app_registry_owner ON app_registry (owner_wallet_id, created_at DESC)"
        )
        self._ensure_index(
            "CREATE INDEX IF NOT EXISTS idx_ingestion_logs_wallet ON ingestion_logs (wallet_id, created_at DESC)"
        )
        self._ensure_index(
            "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_data_wallet ON ingestion_jobs (data_wallet_id, created_at DESC)"
        )
        self._ensure_index(
            "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_private_db ON ingestion_jobs (private_db_id, created_at DESC)"
        )
        self._ensure_index(
            "CREATE INDEX IF NOT EXISTS idx_kb_documents_private_db ON kb_documents (private_db_id, created_at DESC)"
        )

    def _ensure_column(self, table: str, column: str, ddl: str) -> None:
        try:
            cols = {row["name"] for row in self.query_all(f"PRAGMA table_info({table})")}
        except Exception:
            return
        if column in cols:
            return
        with self._lock, self._conn:
            try:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" in str(exc).lower():
                    return
                raise

    def _ensure_index(self, ddl: str) -> None:
        try:
            with self._lock, self._conn:
                self._conn.execute(ddl)
        except Exception:
            return

    # ---------- 基础操作 ----------
    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock, self._conn:
            return self._conn.execute(sql, params)

    def query_all(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
