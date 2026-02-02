# api/routers/kb.py
# -*- coding: utf-8 -*-

from typing import Optional
from pathlib import Path

import yaml

from fastapi import APIRouter, Depends, HTTPException
import weaviate.classes.config as wc

from api.deps import get_deps
from api.auth.deps import get_optional_auth_wallet_id, resolve_operator_wallet_id
from api.auth.normalize import normalize_wallet_id
from api.schemas.kb import (
    KBInfo,
    KBStats,
    KBDocument,
    KBDocumentList,
    KBDocumentUpsert,
    KBDocumentUpdate,
    KBConfigInfo,
    KBConfigCreate,
    KBConfigUpdate,
)
from api.kb_meta import derive_content_sha256, extract_source_info, infer_file_type
from api.routers.owner import ensure_app_owner, require_wallet_id, is_super_admin
from api.routers.private_db_utils import resolve_private_db_id
from core.orchestrator.app_registry import AppRegistry

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


def _normalize_kb_type(value: str) -> str:
    val = str(value or "").strip()
    if val == "static_kb":
        return "public_kb"
    return val


def _ensure_collection(deps, cfg: dict) -> str:
    collection = str(cfg.get("collection") or "")
    if not collection:
        raise ValueError("collection is empty")
    if not deps.datasource.weaviate:
        raise RuntimeError("Weaviate is not enabled")

    text_field = _text_field_from_cfg(cfg)
    kb_type = _normalize_kb_type(cfg.get("type"))

    props: list[wc.Property] = []
    seen: set[str] = set()

    def add_prop(name: str, data_type) -> None:
        if not name:
            return
        if name in seen:
            return
        props.append(wc.Property(name=name, data_type=data_type))
        seen.add(name)

    add_prop(text_field, wc.DataType.TEXT)

    schema_fields = cfg.get("schema") or []
    if isinstance(schema_fields, list):
        reserved = _reserved_user_upload_fields() if kb_type == "user_upload" else set()
        for field in schema_fields:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name") or "").strip()
            if not name or name in reserved or name == text_field:
                continue
            add_prop(name, _map_weaviate_type(str(field.get("data_type") or "")))

    if kb_type == "user_upload":
        add_prop("wallet_id", wc.DataType.TEXT)
        add_prop("private_db_id", wc.DataType.TEXT)
        add_prop("resume_id", wc.DataType.TEXT)
        add_prop("jd_id", wc.DataType.TEXT)
        add_prop("source_url", wc.DataType.TEXT)
        add_prop("file_type", wc.DataType.TEXT)
        add_prop("metadata_json", wc.DataType.TEXT)
        if cfg.get("use_allowed_apps_filter"):
            add_prop("allowed_apps", wc.DataType.TEXT)

    deps.datasource.weaviate.ensure_collection(collection, props)
    return collection


def _kb_filters(
    cfg: dict,
    app_id: str,
    private_db_id: Optional[str],
    data_wallet_id: Optional[str],
) -> dict:
    kb_type = _normalize_kb_type(cfg.get("type"))
    filters: dict = {}
    if kb_type == "user_upload":
        if private_db_id:
            filters["private_db_id"] = private_db_id
        elif data_wallet_id:
            filters["wallet_id"] = data_wallet_id
        if cfg.get("use_allowed_apps_filter"):
            filters["allowed_apps"] = app_id
    return filters


def _normalize_kb_key(value: str) -> str:
    key = str(value or "").strip()
    if not key:
        raise ValueError("kb_key is required")
    if any(ch.isspace() for ch in key):
        raise ValueError("kb_key cannot contain spaces")
    return key


def _coerce_top_k(value: int | None, default: int = 3) -> int:
    if value is None:
        return default
    try:
        return max(int(value), 1)
    except Exception:
        return default


def _coerce_weight(value: float | None, default: float = 1.0) -> float:
    if value is None:
        return default
    try:
        return max(float(value), 0.0)
    except Exception:
        return default


def _normalize_schema_fields(schema) -> list[dict]:
    if schema is None:
        return []
    if not isinstance(schema, list):
        raise ValueError("schema must be a list")
    normalized: list[dict] = []
    for item in schema:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        data_type = str(item.get("data_type") or item.get("type") or "text").strip().lower()
        entry = {
            "name": name,
            "data_type": data_type or "text",
            "vectorize": bool(item.get("vectorize")),
        }
        desc = item.get("description")
        if desc is not None:
            entry["description"] = str(desc)
        normalized.append(entry)
    return normalized


def _normalize_vector_fields(fields) -> list[str]:
    if fields is None:
        return []
    if isinstance(fields, str):
        parts = [p.strip() for p in fields.split(",") if p.strip()]
        return parts
    if not isinstance(fields, list):
        raise ValueError("vector_fields must be a list")
    return [str(f).strip() for f in fields if str(f).strip()]


def _reserved_user_upload_fields() -> set[str]:
    return {
        "wallet_id",
        "private_db_id",
        "resume_id",
        "jd_id",
        "source_url",
        "file_type",
        "metadata_json",
        "allowed_apps",
    }


def _map_weaviate_type(value: str):
    val = (value or "").strip().lower()
    if val in ("text", "string", "str"):
        return wc.DataType.TEXT
    if val in ("int", "integer"):
        return getattr(wc.DataType, "INT", wc.DataType.TEXT)
    if val in ("number", "float", "double", "decimal"):
        return getattr(wc.DataType, "NUMBER", wc.DataType.TEXT)
    if val in ("bool", "boolean"):
        return getattr(wc.DataType, "BOOLEAN", wc.DataType.TEXT)
    if val in ("date", "datetime", "timestamp"):
        return getattr(wc.DataType, "DATE", wc.DataType.TEXT)
    return wc.DataType.TEXT


def _normalize_kb_config_payload(payload, *, existing: Optional[dict] = None, require_all: bool = False) -> dict:
    cfg = dict(existing or {})
    if payload is None:
        if require_all:
            raise ValueError("payload is required")
        return cfg

    kb_type = getattr(payload, "kb_type", None)
    if kb_type is not None:
        kb_type = _normalize_kb_type(kb_type)
        if not kb_type:
            raise ValueError("kb_type is required")
        cfg["type"] = kb_type

    collection = getattr(payload, "collection", None)
    if collection is not None:
        collection = str(collection).strip()
        if not collection:
            raise ValueError("collection is required")
        cfg["collection"] = collection

    text_field = getattr(payload, "text_field", None)
    if text_field is not None:
        text_field = str(text_field).strip()
        if not text_field:
            raise ValueError("text_field is required")
        cfg["text_field"] = text_field

    if getattr(payload, "top_k", None) is not None:
        cfg["top_k"] = _coerce_top_k(getattr(payload, "top_k", None))
    if getattr(payload, "weight", None) is not None:
        cfg["weight"] = _coerce_weight(getattr(payload, "weight", None))
    if getattr(payload, "use_allowed_apps_filter", None) is not None:
        cfg["use_allowed_apps_filter"] = bool(getattr(payload, "use_allowed_apps_filter"))

    schema = getattr(payload, "schema", None)
    if schema is not None:
        cfg["schema"] = _normalize_schema_fields(schema)

    vector_fields = getattr(payload, "vector_fields", None)
    if vector_fields is not None:
        cfg["vector_fields"] = _normalize_vector_fields(vector_fields)
    elif cfg.get("schema"):
        cfg["vector_fields"] = [f.get("name") for f in cfg["schema"] if f.get("vectorize")]

    if require_all:
        if not cfg.get("type"):
            raise ValueError("kb_type is required")
        if not cfg.get("collection"):
            raise ValueError("collection is required")
        if not cfg.get("text_field"):
            cfg["text_field"] = _text_field_from_cfg(cfg)
    return cfg


def _validate_kb_config(kb_key: str, cfg: dict) -> None:
    if not kb_key:
        raise ValueError("kb_key is required")
    if not isinstance(cfg, dict):
        raise ValueError("kb config must be a dict")
    cfg["type"] = _normalize_kb_type(cfg.get("type"))
    if not str(cfg.get("type") or "").strip():
        raise ValueError("kb_type is required")
    if not str(cfg.get("collection") or "").strip():
        raise ValueError("collection is required")
    text_field = str(cfg.get("text_field") or "").strip()
    if not text_field:
        cfg["text_field"] = "text"
    cfg["top_k"] = _coerce_top_k(cfg.get("top_k"))
    cfg["weight"] = _coerce_weight(cfg.get("weight"))

    schema = cfg.get("schema")
    if schema is not None:
        cfg["schema"] = _normalize_schema_fields(schema)

    vector_fields = cfg.get("vector_fields")
    if vector_fields is not None:
        cfg["vector_fields"] = _normalize_vector_fields(vector_fields)
    elif cfg.get("schema"):
        cfg["vector_fields"] = [f.get("name") for f in cfg["schema"] if f.get("vectorize")]


def _load_app_config_yaml(deps, app_id: str) -> tuple[Path, dict]:
    spec = deps.app_registry.get(app_id)
    config_path = spec.plugin_dir / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found for app_id={app_id}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("config.yaml must be a dict")
    return config_path, raw


def _save_app_config_yaml(config_path: Path, app_id: str, config: dict) -> None:
    AppRegistry._validate_config(app_id, config)
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _as_kb_config_info(app_id: str, kb_key: str, cfg: dict) -> KBConfigInfo:
    return KBConfigInfo(
        app_id=app_id,
        kb_key=kb_key,
        kb_type=_normalize_kb_type(cfg.get("type")),
        collection=str(cfg.get("collection") or ""),
        text_field=str(cfg.get("text_field") or "text"),
        top_k=int(cfg.get("top_k") or 0),
        weight=float(cfg.get("weight") or 0.0),
        use_allowed_apps_filter=bool(cfg.get("use_allowed_apps_filter")),
        vector_fields=_normalize_vector_fields(cfg.get("vector_fields") or []),
        schema=_normalize_schema_fields(cfg.get("schema") or []),
    )


@router.get("/list", response_model=list[KBInfo])
def list_kbs(
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
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
                        kb_type=_normalize_kb_type(cfg.get("type")),
                        collection=str(cfg.get("collection") or ""),
                        text_field=_text_field_from_cfg(cfg),
                        top_k=int(cfg.get("top_k") or 0),
                        weight=float(cfg.get("weight") or 0.0),
                        use_allowed_apps_filter=bool(cfg.get("use_allowed_apps_filter")),
                        vector_fields=_normalize_vector_fields(cfg.get("vector_fields") or []),
                        schema=_normalize_schema_fields(cfg.get("schema") or []),
                        status=app_status_map.get(app_id),
                    )
                )
        return out
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/{kb_key}/stats", response_model=KBStats)
def kb_stats(
    app_id: str,
    kb_key: str,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    data_wallet_id: Optional[str] = None,
    private_db_id: Optional[str] = None,
    session_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, app_id, operator_wallet_id)
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = _ensure_collection(deps, cfg)
        kb_type = str(cfg.get("type") or "").strip()
        if kb_type == "user_upload":
            effective_data_wallet_id = normalize_wallet_id(data_wallet_id) or None
            if session_id and not effective_data_wallet_id:
                raise HTTPException(status_code=400, detail="data_wallet_id is required when using session_id")
            if effective_data_wallet_id:
                private_db_id = resolve_private_db_id(
                    deps,
                    app_id=app_id,
                    operator_wallet_id=operator_wallet_id,
                    data_wallet_id=effective_data_wallet_id,
                    private_db_id=private_db_id,
                    session_id=session_id,
                    allow_create=True,
                )
            filters = _kb_filters(cfg, app_id, private_db_id, effective_data_wallet_id)
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/{kb_key}/documents", response_model=KBDocumentList)
def list_documents(
    app_id: str,
    kb_key: str,
    limit: int = 20,
    offset: int = 0,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    data_wallet_id: Optional[str] = None,
    private_db_id: Optional[str] = None,
    session_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, app_id, operator_wallet_id)
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = _ensure_collection(deps, cfg)
        kb_type = str(cfg.get("type") or "").strip()
        if kb_type == "user_upload":
            effective_data_wallet_id = normalize_wallet_id(data_wallet_id) or None
            if session_id and not effective_data_wallet_id:
                raise HTTPException(status_code=400, detail="data_wallet_id is required when using session_id")
            if effective_data_wallet_id:
                private_db_id = resolve_private_db_id(
                    deps,
                    app_id=app_id,
                    operator_wallet_id=operator_wallet_id,
                    data_wallet_id=effective_data_wallet_id,
                    private_db_id=private_db_id,
                    session_id=session_id,
                    allow_create=True,
                )
            filters = _kb_filters(cfg, app_id, private_db_id, effective_data_wallet_id)
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
    except HTTPException:
        raise
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
    if not text:
        if props.get(text_field):
            text = props.get(text_field)
        else:
            vector_fields = cfg.get("vector_fields") or []
            if isinstance(vector_fields, list) and vector_fields:
                chunks = []
                for field in vector_fields:
                    key = str(field).strip()
                    if not key:
                        continue
                    val = props.get(key)
                    if val is None:
                        continue
                    if isinstance(val, str):
                        chunks.append(val)
                        continue
                    try:
                        chunks.append(yaml.safe_dump(val, allow_unicode=True).strip())
                    except Exception:
                        chunks.append(str(val))
                if chunks:
                    text = "\n".join(chunks)
    if text and not props.get(text_field):
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
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, app_id, operator_wallet_id)
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
            wallet_id=operator_wallet_id,
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{app_id}/{kb_key}/documents/{doc_id}", response_model=KBDocument)
def replace_document(
    app_id: str,
    kb_key: str,
    doc_id: str,
    req: KBDocumentUpsert,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, app_id, operator_wallet_id)
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
            wallet_id=operator_wallet_id,
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{app_id}/{kb_key}/documents/{doc_id}", response_model=KBDocument)
def update_document(
    app_id: str,
    kb_key: str,
    doc_id: str,
    req: KBDocumentUpdate,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, app_id, operator_wallet_id)
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
                wallet_id=operator_wallet_id,
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{app_id}/{kb_key}/documents/{doc_id}")
def delete_document(
    app_id: str,
    kb_key: str,
    doc_id: str,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, app_id, operator_wallet_id)
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = _ensure_collection(deps, cfg)
        deps.datasource.weaviate.delete_by_id(collection, doc_id)
        deps.datasource.kb_documents.mark_deleted(doc_id)
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{app_id}/configs", response_model=KBConfigInfo)
def create_kb_config(
    app_id: str,
    req: KBConfigCreate,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, app_id, operator_wallet_id)

        kb_key = _normalize_kb_key(req.kb_key)
        config_path, config = _load_app_config_yaml(deps, app_id)
        kb_cfg = config.get("knowledge_bases") or {}
        if not isinstance(kb_cfg, dict):
            kb_cfg = {}
        if kb_key in kb_cfg:
            raise HTTPException(status_code=400, detail=f"kb_key={kb_key} already exists")

        new_cfg = _normalize_kb_config_payload(req, require_all=True)
        _validate_kb_config(kb_key, new_cfg)
        kb_cfg[kb_key] = new_cfg
        config["knowledge_bases"] = kb_cfg
        _save_app_config_yaml(config_path, app_id, config)
        deps.datasource.audit_logs.create(
            action="kb_config.create",
            operator_wallet_id=operator_wallet_id,
            app_id=app_id,
            entity_type="kb_config",
            entity_id=kb_key,
            meta={"before": None, "after": new_cfg},
        )
        return _as_kb_config_info(app_id, kb_key, new_cfg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{app_id}/{kb_key}/config", response_model=KBConfigInfo)
def update_kb_config(
    app_id: str,
    kb_key: str,
    req: KBConfigUpdate,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, app_id, operator_wallet_id)

        kb_key = _normalize_kb_key(kb_key)
        config_path, config = _load_app_config_yaml(deps, app_id)
        kb_cfg = config.get("knowledge_bases") or {}
        if not isinstance(kb_cfg, dict) or kb_key not in kb_cfg:
            raise HTTPException(status_code=404, detail=f"kb_key={kb_key} not found")
        existing = kb_cfg.get(kb_key) or {}
        updated = _normalize_kb_config_payload(req, existing=existing, require_all=False)
        _validate_kb_config(kb_key, updated)
        kb_cfg[kb_key] = updated
        config["knowledge_bases"] = kb_cfg
        _save_app_config_yaml(config_path, app_id, config)
        deps.datasource.audit_logs.create(
            action="kb_config.update",
            operator_wallet_id=operator_wallet_id,
            app_id=app_id,
            entity_type="kb_config",
            entity_id=kb_key,
            meta={"before": existing, "after": updated},
        )
        return _as_kb_config_info(app_id, kb_key, updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{app_id}/{kb_key}/config")
def delete_kb_config(
    app_id: str,
    kb_key: str,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, app_id, operator_wallet_id)

        kb_key = _normalize_kb_key(kb_key)
        config_path, config = _load_app_config_yaml(deps, app_id)
        kb_cfg = config.get("knowledge_bases") or {}
        if not isinstance(kb_cfg, dict) or kb_key not in kb_cfg:
            raise HTTPException(status_code=404, detail=f"kb_key={kb_key} not found")
        removed = kb_cfg.pop(kb_key, None)
        config["knowledge_bases"] = kb_cfg
        _save_app_config_yaml(config_path, app_id, config)
        deps.datasource.audit_logs.create(
            action="kb_config.delete",
            operator_wallet_id=operator_wallet_id,
            app_id=app_id,
            entity_type="kb_config",
            entity_id=kb_key,
            meta={"before": removed, "after": None},
        )
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
