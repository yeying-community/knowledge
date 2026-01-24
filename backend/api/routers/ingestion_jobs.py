# api/routers/ingestion_jobs.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_deps
from api.kb_meta import infer_file_type, sha256_text
from api.routers.kb import _resolve_kb_config
from api.routers.owner import ensure_app_owner, is_super_admin, require_wallet_id
from api.schemas.ingestion_jobs import (
    IngestionJobCreate,
    IngestionJobInfo,
    IngestionJobList,
    IngestionJobPreset,
    IngestionJobRunItem,
    IngestionJobRuns,
)
from api.routers.private_db_utils import resolve_private_db_id
from core.ingestion.job_runner import run_ingestion_job
from datasource.objectstores.path_builder import PathBuilder

router = APIRouter(prefix="/ingestion/jobs", tags=["ingestion-jobs"])


def _as_job_info(row) -> IngestionJobInfo:
    return IngestionJobInfo(
        id=row.get("id"),
        wallet_id=row.get("wallet_id") or "",
        data_wallet_id=row.get("data_wallet_id"),
        private_db_id=row.get("private_db_id"),
        app_id=row.get("app_id") or "",
        kb_key=row.get("kb_key") or "",
        job_type=row.get("job_type") or "",
        source_url=row.get("source_url"),
        file_type=row.get("file_type"),
        status=row.get("status") or "",
        options_json=row.get("options_json"),
        result_json=row.get("result_json"),
        error_message=row.get("error_message"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        started_at=row.get("started_at"),
        finished_at=row.get("finished_at"),
    )


@router.post("", response_model=IngestionJobInfo)
def create_job(req: IngestionJobCreate, run: bool = False, deps=Depends(get_deps)):
    try:
        ensure_app_owner(deps, req.app_id, req.wallet_id)
        if not deps.datasource.minio and req.content:
            raise HTTPException(status_code=400, detail="MinIO is required for inline content")

        cfg = _resolve_kb_config(deps, req.app_id, req.kb_key)
        kb_type = str(cfg.get("type") or "").strip()
        data_wallet_id = (req.data_wallet_id or "").strip() or None
        private_db_id = None
        if kb_type == "user_upload":
            private_db_id = resolve_private_db_id(
                deps,
                app_id=req.app_id,
                wallet_id=req.wallet_id,
                private_db_id=req.private_db_id,
                session_id=req.session_id,
                allow_create=True,
            )
            if not private_db_id and not data_wallet_id:
                raise HTTPException(status_code=400, detail="session_id or private_db_id is required for user_upload")
            if not private_db_id and data_wallet_id:
                private_db_id = data_wallet_id
            data_wallet_id = data_wallet_id or req.wallet_id
        else:
            data_wallet_id = None
        storage_wallet_id = data_wallet_id if kb_type == "user_upload" else req.wallet_id

        source_url = req.source_url
        file_type = req.file_type

        content_sha256 = None
        if req.content:
            filename = (req.filename or "").strip() or f"ingest_{uuid.uuid4()}.txt"
            file_type = file_type or infer_file_type(filename) or "txt"
            key = PathBuilder.kb_upload(storage_wallet_id, req.app_id, req.kb_key, filename)
            deps.datasource.minio.put_text(bucket=deps.datasource.bucket, key=key, text=req.content)
            source_url = f"minio://{deps.datasource.bucket}/{key}"
            content_sha256 = sha256_text(req.content)

        if not source_url:
            raise HTTPException(status_code=400, detail="source_url is required")
        if "://" in source_url and not source_url.startswith("minio://"):
            raise HTTPException(status_code=400, detail="only minio:// URLs are supported for now")
        if file_type is None:
            file_type = infer_file_type(source_url) or "txt"

        options = dict(req.options or {})
        if req.metadata:
            options["metadata"] = req.metadata

        job_id = deps.datasource.ingestion_jobs.create(
            wallet_id=req.wallet_id,
            data_wallet_id=data_wallet_id,
            private_db_id=private_db_id or data_wallet_id,
            app_id=req.app_id,
            kb_key=req.kb_key,
            job_type="kb_ingest",
            source_url=source_url,
            file_type=file_type,
            content_sha256=content_sha256,
            options=options,
        )
        job = deps.datasource.ingestion_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=500, detail="failed to create ingestion job")

        if run:
            run_ingestion_job(job_id, deps)
            job = deps.datasource.ingestion_jobs.get(job_id) or job
        return _as_job_info(job)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@router.get("", response_model=IngestionJobList)
def list_jobs(
    wallet_id: Optional[str] = None,
    data_wallet_id: Optional[str] = None,
    private_db_id: Optional[str] = None,
    session_id: Optional[str] = None,
    app_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    deps=Depends(get_deps),
):
    wallet_id = require_wallet_id(wallet_id)
    if (session_id or private_db_id) and not app_id:
        raise HTTPException(status_code=400, detail="app_id is required when using session_id/private_db_id")
    if app_id:
        ensure_app_owner(deps, app_id, wallet_id)
    private_db_id = resolve_private_db_id(
        deps,
        app_id=app_id or "",
        wallet_id=wallet_id,
        private_db_id=private_db_id,
        session_id=session_id,
        allow_create=False,
    )
    wallet_filter = None if is_super_admin(deps, wallet_id) else wallet_id
    rows = deps.datasource.ingestion_jobs.list(
        wallet_id=wallet_filter,
        data_wallet_id=data_wallet_id,
        private_db_id=private_db_id,
        app_id=app_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return IngestionJobList(items=[_as_job_info(row) for row in rows])


@router.get("/{job_id}", response_model=IngestionJobInfo)
def get_job(job_id: int, wallet_id: Optional[str] = None, deps=Depends(get_deps)):
    wallet_id = require_wallet_id(wallet_id)
    row = deps.datasource.ingestion_jobs.get(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    ensure_app_owner(deps, row.get("app_id"), wallet_id)
    return _as_job_info(row)


@router.post("/{job_id}/run", response_model=IngestionJobInfo)
def run_job(job_id: int, wallet_id: Optional[str] = None, deps=Depends(get_deps)):
    wallet_id = require_wallet_id(wallet_id)
    row = deps.datasource.ingestion_jobs.get(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    ensure_app_owner(deps, row.get("app_id"), wallet_id)
    run_ingestion_job(job_id, deps)
    row = deps.datasource.ingestion_jobs.get(job_id) or row
    return _as_job_info(row)


@router.get("/{job_id}/runs", response_model=IngestionJobRuns)
def list_runs(
    job_id: int,
    wallet_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    deps=Depends(get_deps),
):
    wallet_id = require_wallet_id(wallet_id)
    job = deps.datasource.ingestion_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    ensure_app_owner(deps, job.get("app_id"), wallet_id)
    rows = deps.datasource.ingestion_jobs.list_runs(job_id, limit=limit, offset=offset)
    items = [
        IngestionJobRunItem(
            id=row.get("id"),
            job_id=row.get("job_id"),
            status=row.get("status"),
            message=row.get("message"),
            meta_json=row.get("meta_json"),
            created_at=row.get("created_at"),
        )
        for row in rows
    ]
    return IngestionJobRuns(items=items)


@router.get("/presets", response_model=IngestionJobPreset)
def ingestion_job_presets(
    wallet_id: Optional[str] = None,
    data_wallet_id: Optional[str] = None,
    app_id: Optional[str] = None,
    kb_key: Optional[str] = None,
    limit: int = 20,
    deps=Depends(get_deps),
):
    wallet_id = require_wallet_id(wallet_id)
    if not app_id or not kb_key:
        raise HTTPException(status_code=400, detail="app_id and kb_key are required")
    ensure_app_owner(deps, app_id, wallet_id)
    if not deps.datasource.minio:
        raise HTTPException(status_code=400, detail="MinIO is not enabled")
    bucket = deps.datasource.bucket
    try:
        cfg = _resolve_kb_config(deps, app_id, kb_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    kb_type = str(cfg.get("type") or "").strip()
    owner_wallet_id = wallet_id
    if kb_type == "user_upload":
        owner_wallet_id = (data_wallet_id or "").strip() or wallet_id
    prefix = PathBuilder.kb_prefix(owner_wallet_id, app_id, kb_key)
    keys = deps.datasource.minio.list(bucket=bucket, prefix=prefix, recursive=True) or []
    if limit:
        keys = keys[: max(int(limit), 1)]
    return IngestionJobPreset(bucket=bucket, prefix=prefix, recent_keys=keys)
