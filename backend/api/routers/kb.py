# api/routers/kb.py
# -*- coding: utf-8 -*-

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
import weaviate.classes.config as wc

from api.deps import get_deps
from api.schemas.kb import (
    KBInfo,
    KBStats,
    KBDocument,
    KBDocumentList,
    KBDocumentUpsert,
    KBDocumentUpdate,
)
from api.kb_meta import derive_content_sha256, extract_source_info, infer_file_type
from api.routers.owner import ensure_app_owner, require_wallet_id, is_super_admin
from api.routers.private_db_utils import resolve_private_db_id

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


def _resolve_kb_config(deps, app_id: str, kb_key: str) -> dict:
    spec = deps.app_registry.get(app_id)
    kb_cfg = (spec.config or {}).get("knowledge_bases", {}) or {}
    if not isinstance(kb_cfg, dict) or kb_key not in kb_cfg:
        raise KeyError(f"kb_key={kb_key} not found for app_id={app_id}")
    cfg = kb_cfg[kb_key] or {}
    if not isinstance(cfg, dict):
        raise KeyError(f"kb_key={kb_key} config invalid for app_id={app_id}")
    return cfg


def _text_field_from_cfg(cfg: dict) -> str:
    return str(cfg.get("text_field") or "text").strip() or "text"


def _ensure_collection(deps, cfg: dict) -> str:
    collection = str(cfg.get("collection") or "")
    if not collection:
        raise ValueError("collection is empty")
    if not deps.datasource.weaviate:
        raise RuntimeError("Weaviate is not enabled")

    text_field = _text_field_from_cfg(cfg)
    kb_type = str(cfg.get("type") or "").strip()

    props = [
        wc.Property(name=text_field, data_type=wc.DataType.TEXT),
    ]

    if kb_type == "user_upload":
        props.extend(
            [
                wc.Property(name="wallet_id", data_type=wc.DataType.TEXT),
                wc.Property(name="private_db_id", data_type=wc.DataType.TEXT),
                wc.Property(name="resume_id", data_type=wc.DataType.TEXT),
                wc.Property(name="jd_id", data_type=wc.DataType.TEXT),
                wc.Property(name="source_url", data_type=wc.DataType.TEXT),
                wc.Property(name="file_type", data_type=wc.DataType.TEXT),
                wc.Property(name="metadata_json", data_type=wc.DataType.TEXT),
            ]
        )
        if cfg.get("use_allowed_apps_filter"):
            props.append(wc.Property(name="allowed_apps", data_type=wc.DataType.TEXT))

    deps.datasource.weaviate.ensure_collection(collection, props)
    return collection


def _kb_filters(
    cfg: dict,
    app_id: str,
    private_db_id: Optional[str],
    data_wallet_id: Optional[str],
) -> dict:
    kb_type = str(cfg.get("type") or "").strip()
    filters: dict = {}
    if kb_type == "user_upload":
        if private_db_id:
            filters["private_db_id"] = private_db_id
        elif data_wallet_id:
            filters["wallet_id"] = data_wallet_id
        if cfg.get("use_allowed_apps_filter"):
            filters["allowed_apps"] = app_id
    return filters


@router.get("/list", response_model=list[KBInfo])
def list_kbs(wallet_id: Optional[str] = None, deps=Depends(get_deps)):
    try:
        wallet_id = require_wallet_id(wallet_id)
        if is_super_admin(deps, wallet_id):
            rows = deps.datasource.app_store.list_all(status=None)
        else:
            rows = deps.datasource.app_store.list_by_owner(wallet_id, status=None)
        app_status_map = {row.get("app_id"): row.get("status") for row in rows if row.get("app_id")}

        out: list[KBInfo] = []
        for app_id in sorted(app_status_map.keys()):
            try:
                spec = deps.app_registry.get(app_id)
            except Exception:
                continue
            kb_cfg = (spec.config or {}).get("knowledge_bases", {}) or {}
            if not isinstance(kb_cfg, dict):
                continue
            for kb_key, cfg in kb_cfg.items():
                if not isinstance(cfg, dict):
                    continue
                out.append(
                    KBInfo(
                        app_id=app_id,
                        kb_key=str(kb_key),
                        kb_type=str(cfg.get("type") or ""),
                        collection=str(cfg.get("collection") or ""),
                        text_field=_text_field_from_cfg(cfg),
                        top_k=int(cfg.get("top_k") or 0),
                        weight=float(cfg.get("weight") or 0.0),
                        use_allowed_apps_filter=bool(cfg.get("use_allowed_apps_filter")),
                        status=app_status_map.get(app_id),
                    )
                )
        return out
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/{kb_key}/stats", response_model=KBStats)
def kb_stats(
    app_id: str,
    kb_key: str,
    wallet_id: Optional[str] = None,
    data_wallet_id: Optional[str] = None,
    private_db_id: Optional[str] = None,
    session_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        ensure_app_owner(deps, app_id, wallet_id)
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = _ensure_collection(deps, cfg)
        kb_type = str(cfg.get("type") or "").strip()
        if kb_type == "user_upload":
            private_db_id = resolve_private_db_id(
                deps,
                app_id=app_id,
                wallet_id=wallet_id,
                private_db_id=private_db_id,
                session_id=session_id,
                allow_create=False,
            )
        else:
            private_db_id = None
        filters = _kb_filters(cfg, app_id, private_db_id, data_wallet_id)
        total = deps.datasource.weaviate.count(collection, filters=filters if filters else None)
        return KBStats(
            app_id=app_id,
            kb_key=kb_key,
            collection=collection,
            total_count=total,
            chunk_count=total,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/{kb_key}/documents", response_model=KBDocumentList)
def list_documents(
    app_id: str,
    kb_key: str,
    limit: int = 20,
    offset: int = 0,
    wallet_id: Optional[str] = None,
    data_wallet_id: Optional[str] = None,
    private_db_id: Optional[str] = None,
    session_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        ensure_app_owner(deps, app_id, wallet_id)
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = _ensure_collection(deps, cfg)
        kb_type = str(cfg.get("type") or "").strip()
        if kb_type == "user_upload":
            private_db_id = resolve_private_db_id(
                deps,
                app_id=app_id,
                wallet_id=wallet_id,
                private_db_id=private_db_id,
                session_id=session_id,
                allow_create=False,
            )
        else:
            private_db_id = None
        filters = _kb_filters(cfg, app_id, private_db_id, data_wallet_id)
        items = deps.datasource.weaviate.fetch_objects(
            collection,
            limit=limit,
            offset=offset,
            filters=filters if filters else None,
        )
        normalized = []
        for item in items:
            normalized.append(
                KBDocument(
                    id=item.get("id") or "",
                    properties=item.get("properties") or {},
                    created_at=_to_iso(item.get("created_at")),
                    updated_at=_to_iso(item.get("updated_at")),
                )
            )
        total = deps.datasource.weaviate.count(collection, filters=filters if filters else None)
        return KBDocumentList(items=normalized, total=total)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _to_iso(val) -> str | None:
    if not val:
        return None
    try:
        return val.isoformat()
    except Exception:
        return str(val)


def _prepare_properties(cfg: dict, payload: dict) -> dict:
    props = dict(payload or {})
    text_field = _text_field_from_cfg(cfg)
    text_val = props.get(text_field)
    if text_val is None:
        return props
    props[text_field] = str(text_val)
    return props


def _resolve_text_and_vector(cfg: dict, req, deps, app_id: str) -> tuple[dict, list | None]:
    props = _prepare_properties(cfg, req.properties)
    text_field = _text_field_from_cfg(cfg)

    text = req.text
    if not text and props.get(text_field):
        text = props.get(text_field)
    if text:
        props[text_field] = text

    vector = req.vector
    if vector is None and text:
        vector = deps.embedding_client.embed_one(str(text), app_id=app_id)
    return props, vector


def _record_doc_meta(
    deps,
    *,
    doc_id: str,
    app_id: str,
    kb_key: str,
    wallet_id: Optional[str],
    props: dict,
    text: Optional[str],
    text_field: str,
    default_source_type: Optional[str] = None,
) -> None:
    source_url = props.get("source_url") if isinstance(props, dict) else None
    if isinstance(source_url, str) and not source_url.strip():
        source_url = None

    source_type, source_id = extract_source_info(props or {})
    if source_type is None:
        source_type = default_source_type
    file_type = props.get("file_type") if isinstance(props, dict) else None
    if file_type is None:
        file_type = infer_file_type(source_url)

    content_sha256 = derive_content_sha256(text, props, text_field)

    deps.datasource.kb_documents.upsert(
        doc_id=doc_id,
        app_id=app_id,
        kb_key=kb_key,
        wallet_id=wallet_id,
        source_url=source_url,
        source_type=source_type,
        source_id=source_id,
        file_type=file_type,
        content_sha256=content_sha256,
    )


@router.post("/{app_id}/{kb_key}/documents", response_model=KBDocument)
def create_document(
    app_id: str,
    kb_key: str,
    req: KBDocumentUpsert,
    wallet_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        ensure_app_owner(deps, app_id, wallet_id)
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = _ensure_collection(deps, cfg)

        props, vector = _resolve_text_and_vector(cfg, req, deps, app_id)
        if vector is None:
            raise ValueError("vector is required (text or vector must be provided)")

        obj_id = deps.datasource.weaviate.upsert(
            collection=collection,
            vector=vector,
            properties=props,
            object_id=req.id,
        )
        _record_doc_meta(
            deps,
            doc_id=str(obj_id),
            app_id=app_id,
            kb_key=kb_key,
            wallet_id=wallet_id,
            props=props,
            text=req.text or props.get(_text_field_from_cfg(cfg)),
            text_field=_text_field_from_cfg(cfg),
            default_source_type="manual",
        )
        obj = deps.datasource.weaviate.fetch_object_by_id(collection, obj_id)
        if not obj:
            return KBDocument(id=obj_id, properties=props)
        return KBDocument(
            id=obj.get("id") or obj_id,
            properties=obj.get("properties") or props,
            created_at=_to_iso(obj.get("created_at")),
            updated_at=_to_iso(obj.get("updated_at")),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{app_id}/{kb_key}/documents/{doc_id}", response_model=KBDocument)
def replace_document(
    app_id: str,
    kb_key: str,
    doc_id: str,
    req: KBDocumentUpsert,
    wallet_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        ensure_app_owner(deps, app_id, wallet_id)
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = _ensure_collection(deps, cfg)

        props, vector = _resolve_text_and_vector(cfg, req, deps, app_id)
        if vector is None:
            raise ValueError("vector is required (text or vector must be provided)")

        deps.datasource.weaviate.upsert(
            collection=collection,
            vector=vector,
            properties=props,
            object_id=doc_id,
        )
        _record_doc_meta(
            deps,
            doc_id=doc_id,
            app_id=app_id,
            kb_key=kb_key,
            wallet_id=wallet_id,
            props=props,
            text=req.text or props.get(_text_field_from_cfg(cfg)),
            text_field=_text_field_from_cfg(cfg),
            default_source_type="manual",
        )
        obj = deps.datasource.weaviate.fetch_object_by_id(collection, doc_id)
        if not obj:
            return KBDocument(id=doc_id, properties=props)
        return KBDocument(
            id=obj.get("id") or doc_id,
            properties=obj.get("properties") or props,
            created_at=_to_iso(obj.get("created_at")),
            updated_at=_to_iso(obj.get("updated_at")),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{app_id}/{kb_key}/documents/{doc_id}", response_model=KBDocument)
def update_document(
    app_id: str,
    kb_key: str,
    doc_id: str,
    req: KBDocumentUpdate,
    wallet_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        ensure_app_owner(deps, app_id, wallet_id)
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = _ensure_collection(deps, cfg)

        props, vector = _resolve_text_and_vector(cfg, req, deps, app_id)
        deps.datasource.weaviate.update(
            collection=collection,
            object_id=doc_id,
            properties=props if props else None,
            vector=vector,
        )
        if props or vector or req.text:
            _record_doc_meta(
                deps,
                doc_id=doc_id,
                app_id=app_id,
                kb_key=kb_key,
                wallet_id=wallet_id,
                props=props or {},
                text=req.text or (props.get(_text_field_from_cfg(cfg)) if props else None),
                text_field=_text_field_from_cfg(cfg),
            )
        obj = deps.datasource.weaviate.fetch_object_by_id(collection, doc_id)
        if not obj:
            return KBDocument(id=doc_id, properties=props or {})
        return KBDocument(
            id=obj.get("id") or doc_id,
            properties=obj.get("properties") or props,
            created_at=_to_iso(obj.get("created_at")),
            updated_at=_to_iso(obj.get("updated_at")),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{app_id}/{kb_key}/documents/{doc_id}")
def delete_document(
    app_id: str,
    kb_key: str,
    doc_id: str,
    wallet_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        ensure_app_owner(deps, app_id, wallet_id)
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = _ensure_collection(deps, cfg)
        deps.datasource.weaviate.delete_by_id(collection, doc_id)
        deps.datasource.kb_documents.mark_deleted(doc_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
