# api/app_register.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import yaml

from api.deps import get_deps
from api.auth.deps import get_optional_auth_wallet_id, resolve_operator_wallet_id
from api.auth.normalize import normalize_wallet_id
from api.routers.kb import _ensure_collection, _kb_filters
from api.routers.owner import ensure_app_owner, require_wallet_id, is_super_admin
from api.schemas.ingestion import IngestionLogItem
from core.orchestrator.app_registry import AppRegistry

router = APIRouter(prefix="/app", tags=["app"])


# -------------------------
# Schemas
# -------------------------
class AppRegisterReq(BaseModel):
    app_id: str
    wallet_id: Optional[str] = None


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


class IntentDetailItem(BaseModel):
    name: str
    description: str = ""
    params: List[str] = Field(default_factory=list)
    exposed: bool = True


class AppIntentsDetailResp(BaseModel):
    app_id: str
    intents: List[IntentDetailItem]


class AppIntentsUpdateReq(BaseModel):
    intents: List[IntentDetailItem] = Field(default_factory=list)


class WorkflowItem(BaseModel):
    name: str
    description: str = ""
    intents: List[str] = Field(default_factory=list)
    enabled: bool = True


class AppWorkflowsResp(BaseModel):
    app_id: str
    workflows: List[WorkflowItem]


class AppWorkflowsUpdateReq(BaseModel):
    workflows: List[WorkflowItem] = Field(default_factory=list)


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


class PluginFileInfo(BaseModel):
    path: str
    kind: str
    exists: bool = True
    size_bytes: int = 0
    updated_at: Optional[str] = None


class PluginFileListResp(BaseModel):
    app_id: str
    files: List[PluginFileInfo]


class PluginFileReadResp(BaseModel):
    app_id: str
    path: str
    kind: str
    content: str


class PluginFileUpdateReq(BaseModel):
    path: str
    content: str = ""


class PluginFileUpdateResp(BaseModel):
    app_id: str
    path: str
    status: str = "ok"


# -------------------------
# API
# -------------------------
@router.post("/register", response_model=AppRegisterResp)
def register_app(
    req: AppRegisterReq,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    """
    注册/启用一个业务插件（App）
    - 不再写入内存 registry
    - 注册事实只落 SQLite（app_registry 表）
    - 仍然会校验 plugins/<app_id> 是否可加载（防止写入垃圾 app_id）
    """
    app_id = req.app_id
    wallet_id = resolve_operator_wallet_id(
        request_wallet_id=req.wallet_id,
        auth_wallet_id=auth_wallet_id,
        allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
    )

    try:
        require_wallet_id(wallet_id)
        row = deps.datasource.app_store.get(app_id)
        if row:
            owner = normalize_wallet_id(row.get("owner_wallet_id"))
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
def list_apps(
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    """
    返回插件目录 + DB 注册状态的融合视图
    """
    wallet_id = resolve_operator_wallet_id(
        request_wallet_id=wallet_id,
        auth_wallet_id=auth_wallet_id,
        allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
    )
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


def _intent_items_from_block(intents_block: dict) -> List[IntentDetailItem]:
    items: List[IntentDetailItem] = []
    for name, meta in sorted(intents_block.items(), key=lambda x: x[0]):
        if not isinstance(name, str) or not name.strip():
            continue
        meta = meta or {}
        params = meta.get("params") or []
        if not isinstance(params, list):
            params = []
        items.append(
            IntentDetailItem(
                name=name.strip(),
                description=str(meta.get("description") or ""),
                params=[str(p) for p in params if str(p).strip()],
                exposed=bool(meta.get("exposed", True)),
            )
        )
    return items


def _build_intents_block(items: List[IntentDetailItem]) -> dict:
    intents_block: dict = {}
    seen = set()
    for item in items:
        name = (item.name or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            raise ValueError(f"intent name duplicate: {name}")
        seen.add(key)
        intents_block[name] = {
            "description": item.description or "",
            "params": [str(p) for p in (item.params or []) if str(p).strip()],
            "exposed": bool(item.exposed),
        }
    if not intents_block:
        raise ValueError("intents cannot be empty")
    return intents_block


def _load_workflows_file(path: Path) -> List[WorkflowItem]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = []
    if isinstance(raw, dict):
        items = raw.get("workflows") or []
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError("workflows.yaml must be a dict or list")
    if not isinstance(items, list):
        raise ValueError("workflows must be a list")
    normalized: List[WorkflowItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        intents = item.get("intents") or []
        if not isinstance(intents, list):
            intents = []
        normalized.append(
            WorkflowItem(
                name=name,
                description=str(item.get("description") or ""),
                intents=[str(p) for p in intents if str(p).strip()],
                enabled=bool(item.get("enabled", True)),
            )
        )
    return normalized


def _build_workflows_block(items: List[WorkflowItem]) -> List[dict]:
    seen = set()
    output: List[dict] = []
    for item in items:
        name = (item.name or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            raise ValueError(f"workflow name duplicate: {name}")
        seen.add(key)
        output.append(
            {
                "name": name,
                "description": item.description or "",
                "intents": [str(p) for p in (item.intents or []) if str(p).strip()],
                "enabled": bool(item.enabled),
            }
        )
    return output


def _ensure_plugin_dir(deps, app_id: str, operator_wallet_id: str) -> Path:
    plugin_dir = deps.app_registry.plugins_root / app_id
    if not plugin_dir.exists():
        raise FileNotFoundError(f"插件目录不存在: {plugin_dir}")
    if is_super_admin(deps, operator_wallet_id):
        return plugin_dir
    ensure_app_owner(deps, app_id, operator_wallet_id)
    return plugin_dir


def _normalize_plugin_path(path: str) -> str:
    raw = str(path or "").strip()
    if not raw:
        raise ValueError("path is required")
    if raw.startswith("/") or raw.startswith("\\"):
        raise ValueError("path must be relative")
    if "\\" in raw:
        raise ValueError("path must use forward slashes")
    parts = Path(raw).parts
    if any(part == ".." for part in parts):
        raise ValueError("path cannot contain ..")
    return raw


def _plugin_kind(path: str) -> str:
    if path in ("config.yaml", "intents.yaml", "workflows.yaml", "pipeline.py"):
        return {
            "config.yaml": "config",
            "intents.yaml": "intents",
            "workflows.yaml": "workflows",
            "pipeline.py": "pipeline",
        }[path]
    if path.startswith("prompts/") and path.count("/") == 1 and path.endswith(".md"):
        return "prompt"
    raise ValueError("path not allowed")


def _resolve_plugin_file(plugin_dir: Path, rel_path: str) -> Path:
    target = (plugin_dir / rel_path).resolve()
    root = plugin_dir.resolve()
    if target == root or root not in target.parents:
        raise ValueError("path out of plugin dir")
    return target


def _file_info(plugin_dir: Path, rel_path: str, kind: str, exists: bool) -> PluginFileInfo:
    size_bytes = 0
    updated_at = None
    if exists:
        stat = (plugin_dir / rel_path).stat()
        size_bytes = int(stat.st_size or 0)
        updated_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
    return PluginFileInfo(
        path=rel_path,
        kind=kind,
        exists=exists,
        size_bytes=size_bytes,
        updated_at=updated_at,
    )


def _validate_plugin_content(app_id: str, path: str, content: str) -> None:
    if path == "config.yaml":
        data = yaml.safe_load(content) or {}
        if not isinstance(data, dict):
            raise ValueError("config.yaml must be a dict")
        AppRegistry._validate_config(app_id, data)
        return
    if path == "intents.yaml":
        data = yaml.safe_load(content) or {}
        if not isinstance(data, dict):
            raise ValueError("intents.yaml must be a dict")
        AppRegistry._parse_intents(data)
        return
    if path == "workflows.yaml":
        data = yaml.safe_load(content) or {}
        if isinstance(data, dict):
            workflows = data.get("workflows") or []
            if not isinstance(workflows, list):
                raise ValueError("workflows must be a list")
            return
        if isinstance(data, list):
            return
        raise ValueError("workflows.yaml must be a dict or list")


def _clear_plugin_cache(deps, app_id: str, kind: str) -> None:
    if kind in ("prompt", "config", "intents"):
        try:
            deps.prompt_builder.loader.clear_cache(app_id)
        except Exception:
            pass
    if kind == "pipeline":
        try:
            if getattr(deps.pipeline_registry, "cache_enabled", False):
                deps.pipeline_registry._pipelines.pop(app_id, None)
        except Exception:
            pass


@router.get("/{app_id}/intents/detail", response_model=AppIntentsDetailResp)
def get_intent_details(
    app_id: str,
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
        spec = deps.app_registry.get(app_id)
        intents_block = {k: {
            "description": v.description,
            "params": list(v.params),
            "exposed": v.exposed,
        } for k, v in spec.intents.items()}
        items = _intent_items_from_block(intents_block)
        return AppIntentsDetailResp(app_id=app_id, intents=items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{app_id}/intents", response_model=AppIntentsDetailResp)
def update_intents(
    app_id: str,
    req: AppIntentsUpdateReq,
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
        spec = deps.app_registry.get(app_id)
        before_block = {k: {
            "description": v.description,
            "params": list(v.params),
            "exposed": v.exposed,
        } for k, v in spec.intents.items()}
        intents_block = _build_intents_block(req.intents or [])
        raw = {"intents": intents_block}
        AppRegistry._parse_intents(raw)
        intent_path = spec.plugin_dir / "intents.yaml"
        intent_path.write_text(
            yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        deps.datasource.audit_logs.create(
            operator_wallet_id=operator_wallet_id,
            app_id=app_id,
            entity_type="intent",
            entity_id=app_id,
            action="intent.update",
            meta={"before": before_block, "after": intents_block},
        )
        items = _intent_items_from_block(intents_block)
        return AppIntentsDetailResp(app_id=app_id, intents=items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/workflows", response_model=AppWorkflowsResp)
def get_workflows(
    app_id: str,
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
        spec = deps.app_registry.get(app_id)
        workflow_path = spec.plugin_dir / "workflows.yaml"
        items = _load_workflows_file(workflow_path)
        return AppWorkflowsResp(app_id=app_id, workflows=items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{app_id}/workflows", response_model=AppWorkflowsResp)
def update_workflows(
    app_id: str,
    req: AppWorkflowsUpdateReq,
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
        spec = deps.app_registry.get(app_id)
        workflow_path = spec.plugin_dir / "workflows.yaml"
        before_items = _load_workflows_file(workflow_path)
        workflows_block = _build_workflows_block(req.workflows or [])
        raw = {"workflows": workflows_block}
        workflow_path.write_text(
            yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        deps.datasource.audit_logs.create(
            operator_wallet_id=operator_wallet_id,
            app_id=app_id,
            entity_type="workflow",
            entity_id=app_id,
            action="workflow.update",
            meta={"before": [item.dict() for item in before_items], "after": workflows_block},
        )
        items = _load_workflows_file(workflow_path)
        return AppWorkflowsResp(app_id=app_id, workflows=items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/plugin/files", response_model=PluginFileListResp)
def list_plugin_files(
    app_id: str,
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
        plugin_dir = _ensure_plugin_dir(deps, app_id, operator_wallet_id)
        files: List[PluginFileInfo] = []
        base_files = [
            ("config.yaml", "config"),
            ("intents.yaml", "intents"),
            ("workflows.yaml", "workflows"),
            ("pipeline.py", "pipeline"),
            ("prompts/system.md", "prompt"),
        ]
        for rel_path, kind in base_files:
            path = plugin_dir / rel_path
            files.append(_file_info(plugin_dir, rel_path, kind, path.exists()))

        prompts_dir = plugin_dir / "prompts"
        if prompts_dir.exists():
            for md in sorted(prompts_dir.glob("*.md")):
                if md.name == "system.md":
                    continue
                rel_path = f"prompts/{md.name}"
                files.append(_file_info(plugin_dir, rel_path, "prompt", True))

        return PluginFileListResp(app_id=app_id, files=files)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/plugin/file", response_model=PluginFileReadResp)
def read_plugin_file(
    app_id: str,
    path: str,
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
        plugin_dir = _ensure_plugin_dir(deps, app_id, operator_wallet_id)
        rel_path = _normalize_plugin_path(path)
        kind = _plugin_kind(rel_path)
        target = _resolve_plugin_file(plugin_dir, rel_path)
        if not target.exists():
            raise HTTPException(status_code=404, detail="file not found")
        return PluginFileReadResp(
            app_id=app_id,
            path=rel_path,
            kind=kind,
            content=target.read_text(encoding="utf-8"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{app_id}/plugin/file", response_model=PluginFileUpdateResp)
def update_plugin_file(
    app_id: str,
    req: PluginFileUpdateReq,
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
        plugin_dir = _ensure_plugin_dir(deps, app_id, operator_wallet_id)
        rel_path = _normalize_plugin_path(req.path)
        kind = _plugin_kind(rel_path)
        target = _resolve_plugin_file(plugin_dir, rel_path)
        before_size = target.stat().st_size if target.exists() else 0
        _validate_plugin_content(app_id, rel_path, req.content or "")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(req.content or "", encoding="utf-8")
        _clear_plugin_cache(deps, app_id, kind)
        deps.datasource.audit_logs.create(
            operator_wallet_id=operator_wallet_id,
            app_id=app_id,
            entity_type="plugin_file",
            entity_id=rel_path,
            action="plugin.update",
            meta={
                "path": rel_path,
                "size_before": int(before_size or 0),
                "size_after": len(req.content or ""),
            },
        )
        return PluginFileUpdateResp(app_id=app_id, path=rel_path, status="ok")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/status", response_model=AppStatusResp)
def app_status(
    app_id: str,
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
