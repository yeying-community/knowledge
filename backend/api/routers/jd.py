# api/routers/jd.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_deps
from api.kb_meta import infer_file_type, sha256_text
from api.routers.kb import _ensure_collection, _resolve_kb_config, _text_field_from_cfg
from api.schemas.jd import JDUploadRequest, JDUploadResponse
from api.routers.private_db_utils import resolve_private_db_id
from datasource.objectstores.path_builder import PathBuilder


router = APIRouter(prefix="/{app_id}/jd", tags=["jd"])


def _serialize_payload(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return str(payload)


def _extract_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, dict):
        for key in ("text", "content", "jd"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        segments = payload.get("segments")
        if isinstance(segments, list):
            return "\n".join(str(x) for x in segments if x)
        return ""
    if isinstance(payload, list):
        return "\n".join(str(x) for x in payload if x)
    return ""


def _resolve_user_upload_kb(deps, app_id: str, kb_key: Optional[str]) -> tuple[str, dict]:
    if kb_key:
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        if str(cfg.get("type") or "").strip() != "user_upload":
            raise ValueError(f"kb_key={kb_key} is not user_upload")
        return kb_key, cfg

    spec = deps.app_registry.get(app_id)
    kb_cfg = (spec.config or {}).get("knowledge_bases", {}) or {}
    for key, cfg in kb_cfg.items():
        if not isinstance(cfg, dict):
            continue
        if str(cfg.get("type") or "").strip() == "user_upload":
            return str(key), cfg

    raise ValueError(f"app_id={app_id} has no user_upload knowledge base")


@router.post("/upload", response_model=JDUploadResponse)
def upload_jd(app_id: str, req: JDUploadRequest, deps=Depends(get_deps)):
    try:
        effective_app_id = (req.app_id or "").strip() or app_id
        if req.app_id and req.app_id != app_id:
            raise ValueError("app_id in path does not match body")

        row = deps.datasource.app_store.get(effective_app_id)
        if not row or row.get("status") != "active":
            raise HTTPException(status_code=400, detail=f"app_id={effective_app_id} not active in DB")

        if not deps.datasource.minio:
            raise RuntimeError("MinIO is not enabled")
        if not deps.datasource.weaviate:
            raise RuntimeError("Weaviate is not enabled")

        kb_key, cfg = _resolve_user_upload_kb(deps, effective_app_id, req.kb_key)
        collection = _ensure_collection(deps, cfg)

        jd_id = (req.jd_id or "").strip() or str(uuid.uuid4())
        raw_json = _serialize_payload(req.jd)
        jd_text = _extract_text(req.jd) or raw_json

        private_db_id = resolve_private_db_id(
            deps,
            app_id=effective_app_id,
            wallet_id=req.wallet_id,
            private_db_id=req.private_db_id,
            session_id=req.session_id,
            allow_create=True,
        )
        if not private_db_id:
            raise HTTPException(status_code=400, detail="session_id or private_db_id is required")

        key = PathBuilder.user_jd(req.wallet_id, effective_app_id, jd_id)
        deps.datasource.minio.put_text(bucket=deps.datasource.bucket, key=key, text=raw_json)
        source_url = f"minio://{deps.datasource.bucket}/{key}"
        file_type = infer_file_type(source_url) or "json"

        text_field = _text_field_from_cfg(cfg)
        props: Dict[str, Any] = {
            text_field: jd_text,
            "wallet_id": req.wallet_id,
            "private_db_id": private_db_id,
            "jd_id": jd_id,
            "source_url": source_url,
            "file_type": file_type,
            "metadata_json": raw_json,
        }
        if req.metadata:
            combined = {"jd": req.jd, "metadata": req.metadata}
            props["metadata_json"] = _serialize_payload(combined)
        if cfg.get("use_allowed_apps_filter"):
            props["allowed_apps"] = effective_app_id

        vector = deps.embedding_client.embed_one(jd_text, app_id=effective_app_id)
        doc_id = deps.datasource.weaviate.upsert(
            collection=collection,
            vector=vector,
            properties=props,
        )

        deps.datasource.kb_documents.upsert(
            doc_id=str(doc_id),
            app_id=effective_app_id,
            kb_key=kb_key,
            wallet_id=req.wallet_id,
            private_db_id=private_db_id,
            source_url=source_url,
            source_type="jd",
            source_id=jd_id,
            file_type=file_type,
            content_sha256=sha256_text(raw_json),
        )

        return JDUploadResponse(
            jd_id=jd_id,
            kb_key=kb_key,
            collection=collection,
            doc_id=str(doc_id),
            source_url=source_url,
        )
    except HTTPException:
        raise
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
