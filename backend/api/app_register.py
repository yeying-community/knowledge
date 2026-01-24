# api/app_register.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from api.deps import get_deps
from api.routers.kb import _ensure_collection, _kb_filters
from api.routers.owner import ensure_app_owner, require_wallet_id, is_super_admin
from api.schemas.ingestion import IngestionLogItem

router = APIRouter(prefix="/app", tags=["app"])


# -------------------------
# Schemas
# -------------------------
class AppRegisterReq(BaseModel):
    app_id: str
    wallet_id: str


class AppRegisterResp(BaseModel):
    app_id: str
    status: str = "ok"


class AppInfoResp(BaseModel):
    app_id: str
    status: str
    has_plugin: bool
    owner_wallet_id: Optional[str] = None


class AppIntentsResp(BaseModel):
    app_id: str
    intents: List[str]
    exposed_intents: List[str]


class AppStatusKBInfo(BaseModel):
    kb_key: str
    collection: str
    total_count: int
    chunk_count: int
    error: Optional[str] = None


class AppStatusResp(BaseModel):
    app_id: str
    status: str
    owner_wallet_id: Optional[str] = None
    has_plugin: bool
    kb_stats: List[AppStatusKBInfo] = Field(default_factory=list)
    last_ingestion: Optional[IngestionLogItem] = None


# -------------------------
# API
# -------------------------
@router.post("/register", response_model=AppRegisterResp)
def register_app(req: AppRegisterReq, deps=Depends(get_deps)):
    """
    注册/启用一个业务插件（App）
    - 不再写入内存 registry
    - 注册事实只落 SQLite（app_registry 表）
    - 仍然会校验 plugins/<app_id> 是否可加载（防止写入垃圾 app_id）
    """
    app_id = req.app_id
    wallet_id = req.wallet_id

    try:
        require_wallet_id(wallet_id)
        row = deps.datasource.app_store.get(app_id)
        if row:
            owner = row.get("owner_wallet_id")
            if owner and owner != wallet_id and not is_super_admin(deps, wallet_id):
                raise HTTPException(
                    status_code=403,
                    detail=f"wallet_id does not own app_id={app_id}",
                )

        # 1) 校验插件目录与声明文件（按需加载，不落内存）
        deps.app_registry.register_app(app_id)

        # 2) 写 DB：active
        deps.datasource.app_store.upsert(app_id, status="active", owner_wallet_id=wallet_id)

        return AppRegisterResp(app_id=app_id, status="ok")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list", response_model=List[AppInfoResp])
def list_apps(wallet_id: Optional[str] = None, deps=Depends(get_deps)):
    """
    返回插件目录 + DB 注册状态的融合视图
    """
    wallet_id = require_wallet_id(wallet_id)
    if is_super_admin(deps, wallet_id):
        rows = deps.datasource.app_store.list_all(status=None)
    else:
        rows = deps.datasource.app_store.list_by_owner(wallet_id, status=None)
    db_map = {row.get("app_id"): row for row in rows if row.get("app_id")}
    plugin_ids = set(deps.app_registry.list_apps())
    all_ids = sorted(db_map.keys())

    return [
        AppInfoResp(
            app_id=app_id,
            status=(db_map.get(app_id) or {}).get("status", "unregistered"),
            has_plugin=app_id in plugin_ids,
            owner_wallet_id=(db_map.get(app_id) or {}).get("owner_wallet_id"),
        )
        for app_id in all_ids
    ]


@router.get("/{app_id}/intents", response_model=AppIntentsResp)
def list_intents(app_id: str, deps=Depends(get_deps)):
    """
    返回插件 intents（含 exposed intents）
    """
    try:
        intents = deps.app_registry.list_intents(app_id)
        exposed = deps.app_registry.list_exposed_intents(app_id)
        return AppIntentsResp(app_id=app_id, intents=intents, exposed_intents=exposed)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/status", response_model=AppStatusResp)
def app_status(app_id: str, wallet_id: Optional[str] = None, deps=Depends(get_deps)):
    try:
        row = ensure_app_owner(deps, app_id, wallet_id)
        status = row.get("status") or "unregistered"
        owner_wallet_id = row.get("owner_wallet_id")
        has_plugin = deps.app_registry.is_registered(app_id)

        kb_stats: List[AppStatusKBInfo] = []
        if has_plugin:
            try:
                spec = deps.app_registry.get(app_id)
                kb_cfg = (spec.config or {}).get("knowledge_bases", {}) or {}
            except Exception:
                kb_cfg = {}
                has_plugin = False
            if isinstance(kb_cfg, dict):
                for kb_key, cfg in kb_cfg.items():
                    if not isinstance(cfg, dict):
                        continue
                    collection = str(cfg.get("collection") or "")
                    try:
                        collection = _ensure_collection(deps, cfg)
                        filters = _kb_filters(cfg, app_id, None, None)
                        total = deps.datasource.weaviate.count(
                            collection,
                            filters=filters if filters else None,
                        )
                        kb_stats.append(
                            AppStatusKBInfo(
                                kb_key=str(kb_key),
                                collection=collection,
                                total_count=total,
                                chunk_count=total,
                            )
                        )
                    except Exception as e:
                        kb_stats.append(
                            AppStatusKBInfo(
                                kb_key=str(kb_key),
                                collection=collection,
                                total_count=0,
                                chunk_count=0,
                                error=str(e),
                            )
                        )

        logs = deps.datasource.ingestion_logs.list(limit=1, offset=0, app_id=app_id)
        last_log = None
        if logs:
            row = logs[0]
            last_log = IngestionLogItem(
                id=row.get("id"),
                status=row.get("status"),
                message=row.get("message"),
                app_id=row.get("app_id"),
                kb_key=row.get("kb_key"),
                collection=row.get("collection"),
                meta_json=row.get("meta_json"),
                created_at=row.get("created_at"),
            )

        return AppStatusResp(
            app_id=app_id,
            status=status,
            owner_wallet_id=owner_wallet_id,
            has_plugin=has_plugin,
            kb_stats=kb_stats,
            last_ingestion=last_log,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
