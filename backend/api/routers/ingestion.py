# api/routers/ingestion.py
# -*- coding: utf-8 -*-

import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from api.deps import get_deps
from api.kb_meta import infer_file_type
from api.schemas.ingestion import IngestionLogCreate, IngestionLogList, IngestionLogItem
from api.routers.owner import ensure_app_owner, require_wallet_id, is_super_admin
from api.routers.kb import _resolve_kb_config
from datasource.objectstores.path_builder import PathBuilder

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.get("/logs", response_model=IngestionLogList)
def list_logs(
    limit: int = 50,
    offset: int = 0,
    wallet_id: str | None = None,
    app_id: str | None = None,
    kb_key: str | None = None,
    status: str | None = None,
    deps=Depends(get_deps),
):
    wallet_id = require_wallet_id(wallet_id)
    if not app_id:
        raise HTTPException(status_code=400, detail="app_id is required")
    ensure_app_owner(deps, app_id, wallet_id)
    wallet_filter = None if is_super_admin(deps, wallet_id) else wallet_id
    rows = deps.datasource.ingestion_logs.list(
        limit=limit,
        offset=offset,
        wallet_id=wallet_filter,
        app_id=app_id,
        kb_key=kb_key,
        status=status,
    )
    items = []
    for row in rows:
        items.append(
            IngestionLogItem(
                id=row.get("id"),
                status=row.get("status"),
                message=row.get("message"),
                wallet_id=row.get("wallet_id"),
                app_id=row.get("app_id"),
                kb_key=row.get("kb_key"),
                collection=row.get("collection"),
                meta_json=row.get("meta_json"),
                created_at=row.get("created_at"),
            )
        )
    return IngestionLogList(items=items)


@router.post("/logs")
def create_log(req: IngestionLogCreate, deps=Depends(get_deps)):
    try:
        wallet_id = require_wallet_id(req.wallet_id)
        if not req.app_id:
            raise HTTPException(status_code=400, detail="app_id is required")
        ensure_app_owner(deps, req.app_id, wallet_id)
        deps.datasource.ingestion_logs.create(
            status=req.status,
            message=req.message or "",
            wallet_id=wallet_id,
            app_id=req.app_id,
            kb_key=req.kb_key,
            collection=req.collection,
            meta=req.meta or {},
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload")
def upload_file(
    wallet_id: str = Form(...),
    app_id: str = Form(...),
    kb_key: str = Form(...),
    data_wallet_id: str | None = Form(None),
    filename: str | None = Form(None),
    file: UploadFile = File(...),
    deps=Depends(get_deps),
):
    try:
        ensure_app_owner(deps, app_id, wallet_id)
        if not deps.datasource.minio:
            raise HTTPException(status_code=400, detail="MinIO is not enabled")
        if not file:
            raise HTTPException(status_code=400, detail="file is required")

        cfg = _resolve_kb_config(deps, app_id, kb_key)
        kb_type = str(cfg.get("type") or "").strip()
        storage_wallet_id = data_wallet_id or wallet_id
        if kb_type != "user_upload":
            data_wallet_id = None

        raw = file.file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="empty file")
        name = (filename or file.filename or "").strip() or f"upload_{uuid.uuid4()}"
        file_type = infer_file_type(name) or "bin"
        key = PathBuilder.kb_upload(storage_wallet_id, app_id, kb_key, name)
        deps.datasource.minio.put_bytes(
            bucket=deps.datasource.bucket,
            key=key,
            data=raw,
            content_type=file.content_type or "application/octet-stream",
        )
        sha256 = hashlib.sha256(raw).hexdigest()
        return {
            "bucket": deps.datasource.bucket,
            "key": key,
            "source_url": f"minio://{deps.datasource.bucket}/{key}",
            "file_type": file_type,
            "size_bytes": len(raw),
            "content_sha256": sha256,
            "data_wallet_id": data_wallet_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
