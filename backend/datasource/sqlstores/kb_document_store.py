# rag/datasource/sqlstores/kb_document_store.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class KBDocumentStore:
    """KB 文档元数据存储（向量存储之外的索引层）"""

    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def upsert(
        self,
        *,
        doc_id: str,
        app_id: str,
        kb_key: str,
        wallet_id: Optional[str] = None,
        private_db_id: Optional[str] = None,
        source_url: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        file_type: Optional[str] = None,
        content_sha256: Optional[str] = None,
        status: str = "active",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO kb_documents(
              doc_id, app_id, kb_key, wallet_id, private_db_id,
              source_url, source_type, source_id, file_type, content_sha256, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
              app_id = excluded.app_id,
              kb_key = excluded.kb_key,
              wallet_id = COALESCE(excluded.wallet_id, kb_documents.wallet_id),
              private_db_id = COALESCE(excluded.private_db_id, kb_documents.private_db_id),
              source_url = COALESCE(excluded.source_url, kb_documents.source_url),
              source_type = COALESCE(excluded.source_type, kb_documents.source_type),
              source_id = COALESCE(excluded.source_id, kb_documents.source_id),
              file_type = COALESCE(excluded.file_type, kb_documents.file_type),
              content_sha256 = COALESCE(excluded.content_sha256, kb_documents.content_sha256),
              status = excluded.status,
              updated_at = datetime('now')
            """,
            (
                doc_id,
                app_id,
                kb_key,
                wallet_id,
                private_db_id,
                source_url,
                source_type,
                source_id,
                file_type,
                content_sha256,
                status,
            ),
        )

    def get(self, doc_id: str) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM kb_documents WHERE doc_id = ?",
            (doc_id,),
        )

    def list(
        self,
        *,
        app_id: Optional[str] = None,
        kb_key: Optional[str] = None,
        wallet_id: Optional[str] = None,
        private_db_id: Optional[str] = None,
        status: Optional[str] = "active",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Row]:
        clauses = []
        params: List[Any] = []

        if app_id:
            clauses.append("app_id = ?")
            params.append(app_id)
        if kb_key:
            clauses.append("kb_key = ?")
            params.append(kb_key)
        if wallet_id:
            clauses.append("wallet_id = ?")
            params.append(wallet_id)
        if private_db_id:
            clauses.append("private_db_id = ?")
            params.append(private_db_id)
        if status:
            clauses.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])

        return self.conn.query_all(
            f"""
            SELECT * FROM kb_documents
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )

    def count(
        self,
        *,
        app_id: Optional[str] = None,
        kb_key: Optional[str] = None,
        wallet_id: Optional[str] = None,
        private_db_id: Optional[str] = None,
        status: Optional[str] = "active",
    ) -> int:
        clauses = []
        params: List[Any] = []

        if app_id:
            clauses.append("app_id = ?")
            params.append(app_id)
        if kb_key:
            clauses.append("kb_key = ?")
            params.append(kb_key)
        if wallet_id:
            clauses.append("wallet_id = ?")
            params.append(wallet_id)
        if private_db_id:
            clauses.append("private_db_id = ?")
            params.append(private_db_id)
        if status:
            clauses.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        row = self.conn.query_one(
            f"SELECT COUNT(*) AS total FROM kb_documents {where}",
            tuple(params),
        )
        return int(row["total"] if row else 0)

    def mark_deleted(self, doc_id: str) -> None:
        self.conn.execute(
            """
            UPDATE kb_documents
               SET status = 'deleted',
                   updated_at = datetime('now')
             WHERE doc_id = ?
            """,
            (doc_id,),
        )
