# scripts/rebuild_jd.py
# -*- coding: utf-8 -*-

import os
from pathlib import Path

import yaml

from settings.config import Settings
from datasource.connections.sqlite_connection import SQLiteConnection
from datasource.sqlstores.ingestion_log_store import IngestionLogStore
from datasource.connections.minio_connection import MinioConnection
from datasource.objectstores.minio_store import MinIOStore

from datasource.connections.weaviate_connection import WeaviateConnection
from datasource.vectorstores.weaviate_store import WeaviateStore

from core.embedding.embedding_client import EmbeddingClient
from plugins.interviewer.ingestion.jd_rebuild import (
    rebuild_jd_kb,
    DEFAULT_BUCKET,
    DEFAULT_JD_COLLECTION,
    DEFAULT_APP_ID,
)


def _load_collection(project_root: Path, app_id: str) -> str:
    config_path = project_root / "plugins" / app_id / "config.yaml"
    if not config_path.exists():
        return DEFAULT_JD_COLLECTION
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    kb_cfg = (data.get("knowledge_bases") or {}).get("jd_kb") or {}
    return str(kb_cfg.get("collection") or DEFAULT_JD_COLLECTION)


def _log_ingestion(store: IngestionLogStore, **kwargs) -> None:
    try:
        store.create(**kwargs)
    except Exception:
        pass


def main():
    settings = Settings()

    # ---- MinIO（不经过 Datasource，因此不会初始化 sqlite）----
    minio = MinIOStore(MinioConnection(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    ))

    # ---- Weaviate ----
    if not settings.weaviate_enabled:
        raise RuntimeError("Weaviate is not enabled (settings.weaviate_enabled=false)")

    weaviate = WeaviateStore(WeaviateConnection(
        scheme=settings.weaviate_scheme,
        host=settings.weaviate_host,
        port=settings.weaviate_port,
        grpc_port=settings.weaviate_grpc_port,
        api_key=settings.weaviate_api_key,
    ))

    # ---- Embedding ----
    embedder = EmbeddingClient(settings)

    project_root = Path(__file__).resolve().parents[1]
    app_id = os.getenv("RAG_APP_ID", DEFAULT_APP_ID)
    collection = os.getenv("JD_COLLECTION", _load_collection(project_root, app_id))
    bucket = os.getenv("JD_BUCKET", DEFAULT_BUCKET)

    sqlite = SQLiteConnection(db_path=settings.sqlite_path)
    log_store = IngestionLogStore(sqlite)

    _log_ingestion(
        log_store,
        status="started",
        message="jd rebuild started",
        app_id=app_id,
        kb_key="jd_kb",
        collection=collection,
        meta={"bucket": bucket},
    )

    try:
        stats = rebuild_jd_kb(
            minio_store=minio,
            embedding_client=embedder,
            weaviate_store=weaviate,
            bucket=bucket,
            collection=collection,
            batch_size=8,
            app_id=app_id,
        )
    except Exception as e:
        _log_ingestion(
            log_store,
            status="failed",
            message=str(e),
            app_id=app_id,
            kb_key="jd_kb",
            collection=collection,
            meta={"bucket": bucket},
        )
        raise
    else:
        _log_ingestion(
            log_store,
            status="success",
            message="jd rebuild finished",
            app_id=app_id,
            kb_key="jd_kb",
            collection=collection,
            meta={
                "bucket": bucket,
                "total": stats.jd_total,
                "upserted": stats.jd_upserted,
                "skipped": stats.jd_skipped,
                "deleted": stats.jd_deleted,
                "errors": stats.errors,
            },
        )

    print("JD rebuild finished:", stats)


if __name__ == "__main__":
    main()
