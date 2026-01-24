# core/ingestion/job_runner.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

from api.kb_meta import infer_file_type
from api.routers.kb import _ensure_collection, _resolve_kb_config, _text_field_from_cfg
from core.ingestion.parser_registry import ParsedDocument, default_registry


def _parse_minio_url(source_url: str, default_bucket: str) -> Tuple[str, str]:
    raw = source_url.strip()
    if raw.startswith("minio://"):
        raw = raw[len("minio://") :]
    if "/" not in raw:
        return default_bucket, raw
    bucket, key = raw.split("/", 1)
    return bucket or default_bucket, key


def _load_job_options(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _clip_text(text: str, max_chars: Optional[int]) -> str:
    if not max_chars:
        return text
    if max_chars <= 0:
        return text
    return text[:max_chars]


def _normalize_parsed(
    parsed: ParsedDocument, fallback_file_type: Optional[str]
) -> ParsedDocument:
    if parsed.file_type is None:
        parsed.file_type = fallback_file_type
    return parsed


def run_ingestion_job(job_id: int, deps) -> dict:
    job = deps.datasource.ingestion_jobs.get(job_id)
    if not job:
        raise ValueError(f"ingestion_job not found: id={job_id}")

    status = str(job.get("status") or "")
    if status == "running":
        raise RuntimeError(f"ingestion_job {job_id} is already running")

    deps.datasource.ingestion_jobs.mark_running(job_id)
    deps.datasource.ingestion_jobs.append_run(
        job_id=job_id, status="running", message="job started"
    )

    try:
        app_id = str(job.get("app_id") or "")
        kb_key = str(job.get("kb_key") or "")
        wallet_id = str(job.get("wallet_id") or "")
        source_url = str(job.get("source_url") or "")
        if not app_id or not kb_key or not wallet_id:
            raise ValueError("job missing app_id/kb_key/wallet_id")
        if not source_url:
            raise ValueError("job missing source_url")
        if not deps.datasource.minio:
            raise RuntimeError("MinIO is not enabled")
        if not deps.datasource.weaviate:
            raise RuntimeError("Weaviate is not enabled")

        cfg = _resolve_kb_config(deps, app_id, kb_key)
        kb_type = str(cfg.get("type") or "").strip()
        data_wallet_id = str(job.get("data_wallet_id") or "")
        private_db_id = str(job.get("private_db_id") or "")
        owner_wallet_id = data_wallet_id or wallet_id
        if kb_type != "user_upload":
            owner_wallet_id = ""

        options = _load_job_options(job.get("options_json"))
        max_chars = options.get("max_chars")
        if max_chars is not None:
            try:
                max_chars = int(max_chars)
            except Exception:
                max_chars = None

        bucket, key = _parse_minio_url(source_url, deps.datasource.bucket)
        raw = deps.datasource.minio.get_bytes(bucket=bucket, key=key)
        file_type = str(job.get("file_type") or "") or infer_file_type(source_url)

        registry = default_registry()
        parsed = _normalize_parsed(
            registry.parse(raw, file_type, filename=Path(key).name),
            file_type,
        )
        text = _clip_text(parsed.text or "", max_chars)
        if not text:
            raise ValueError("parsed text is empty")

        collection = _ensure_collection(deps, cfg)
        text_field = _text_field_from_cfg(cfg)

        metadata = parsed.metadata or {}
        extra_meta = options.get("metadata")
        if isinstance(extra_meta, dict):
            metadata.update(extra_meta)

        props = {
            text_field: text,
            "source_url": source_url,
            "file_type": parsed.file_type,
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
        }
        if kb_type == "user_upload":
            if private_db_id:
                props["private_db_id"] = private_db_id
            props["wallet_id"] = owner_wallet_id
        if cfg.get("use_allowed_apps_filter"):
            props["allowed_apps"] = app_id

        vector = deps.embedding_client.embed_one(text, app_id=app_id)
        doc_id = deps.datasource.weaviate.upsert(
            collection=collection,
            vector=vector,
            properties=props,
        )

        deps.datasource.kb_documents.upsert(
            doc_id=str(doc_id),
            app_id=app_id,
            kb_key=kb_key,
            wallet_id=owner_wallet_id or None,
            private_db_id=private_db_id or None,
            source_url=source_url,
            source_type="ingestion_job",
            source_id=str(job_id),
            file_type=parsed.file_type,
            content_sha256=parsed.content_sha256,
        )

        result = {
            "job_id": job_id,
            "doc_id": str(doc_id),
            "collection": collection,
            "kb_key": kb_key,
            "file_type": parsed.file_type,
            "source_url": source_url,
        }
        deps.datasource.ingestion_jobs.mark_success(job_id, result=result)
        deps.datasource.ingestion_jobs.append_run(
            job_id=job_id, status="success", message="job completed", meta=result
        )
        deps.datasource.ingestion_logs.create(
            status="success",
            message="ingestion job completed",
            wallet_id=wallet_id,
            app_id=app_id,
            kb_key=kb_key,
            collection=collection,
            meta={"job_id": job_id},
        )
        return result
    except Exception as e:
        deps.datasource.ingestion_jobs.mark_failed(job_id, str(e))
        deps.datasource.ingestion_jobs.append_run(
            job_id=job_id, status="failed", message=str(e)
        )
        deps.datasource.ingestion_logs.create(
            status="failed",
            message=str(e),
            wallet_id=job.get("wallet_id"),
            app_id=job.get("app_id"),
            kb_key=job.get("kb_key"),
            collection=None,
            meta={"job_id": job_id},
        )
        raise
