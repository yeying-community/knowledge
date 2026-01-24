# core/orchestrator/query_orchestrator.py
# -*- coding: utf-8 -*-

from typing import Dict, Any, List, Optional

from datasource.sqlstores.app_registry_store import AppRegistryStore
from identity.identity_manager import IdentityManager
from identity.models import Identity
from .app_registry import AppRegistry
from ..memory.memory_manager import MemoryManager
from ..kb.kb_manager import KnowledgeBaseManager
from ..prompt.prompt_builder import PromptBuilder
from ..llm.llm_client import LLMClient
from ..kb.types import KBContextBlock


def _as_int(v: Any, default: int) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def _clip_blocks_by_chars(blocks: List[Dict[str, Any]], max_chars: int) -> List[Dict[str, Any]]:
    """
    按 text 字符数裁剪 context_blocks（从前往后保留）。
    注意：summary 不在这里裁剪，summary 由 PromptBuilder 单独注入。
    """
    if max_chars <= 0:
        return blocks

    out: List[Dict[str, Any]] = []
    used = 0
    for b in blocks:
        t = str(b.get("text", "") or "")
        if not t:
            continue
        if used + len(t) > max_chars:
            remain = max_chars - used
            if remain > 0:
                bb = dict(b)
                bb["text"] = t[:remain]
                out.append(bb)
            break
        out.append(b)
        used += len(t)
    return out


def _merge_ranked_blocks(
    aux_blocks: List[Dict[str, Any]],
    kb_blocks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    统一把“可排序候选块”合并并排序：
    - aux_blocks: 来自辅助记忆（score 越大越相关）
    - kb_blocks: 来自 KB（score 已按 weight 调整；score 越大越相关）
    """
    merged = []
    for b in aux_blocks:
        bb = dict(b)
        bb.setdefault("type", "memory")
        bb.setdefault("score", 0.0)
        merged.append(bb)
    for b in kb_blocks:
        bb = dict(b)
        bb.setdefault("type", "kb")
        bb.setdefault("score", 0.0)
        merged.append(bb)

    merged.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    return merged


class QueryOrchestrator:
    """
    中台 Query Orchestrator（config 驱动）
    核心原则：
    - intent_params 仅用于 prompt/业务变量（业务可理解）
    - 检索策略（memory_top_k / per-kb top_k / max_chars 等）来自插件 config.yaml
    """

    def __init__(
        self,
        *,
        identity_manager: IdentityManager,
        app_registry: AppRegistry,
        app_store: AppRegistryStore,
        memory_manager: MemoryManager,
        kb_manager: KnowledgeBaseManager,
        prompt_builder: PromptBuilder,
        llm_client: LLMClient,
    ):
        self.identity_manager = identity_manager
        self.app_registry = app_registry
        self.app_store = app_store
        self.memory_manager = memory_manager
        self.kb_manager = kb_manager
        self.prompt_builder = prompt_builder
        self.llm_client = llm_client

    # -------------------------
    # 入口 A：给 API /query 用（钱包/app/session）
    # -------------------------
    def run(
        self,
        *,
        wallet_id: str,
        app_id: str,
        session_id: str,
        intent: str,
        user_query: str,
        intent_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        identity = self.identity_manager.resolve_identity(
            wallet_id=wallet_id,
            app_id=app_id,
            session_id=session_id,
        )
        return self.run_with_identity(
            identity=identity,
            intent=intent,
            user_query=user_query,
            intent_params=intent_params or {},
        )

    # -------------------------
    # 入口 B：给 pipeline 内部调用用（Identity）
    # -------------------------
    def run_with_identity(
        self,
        *,
        identity: Identity,
        intent: str,
        user_query: str,
        intent_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        intent_params = intent_params or {}
        app_id = identity.app_id

        row = self.app_store.get(app_id)
        if not row or row.get("status") != "active":
            raise RuntimeError(f"app_id={app_id} not active in DB")
        app_spec = self.app_registry.get(app_id)
        cfg: Dict[str, Any] = app_spec.config or {}


        memory_cfg: Dict[str, Any] = cfg.get("memory", {}) or {}
        kb_cfg: Dict[str, Any] = cfg.get("knowledge_bases", {}) or {}
        context_cfg: Dict[str, Any] = cfg.get("context", {}) or {}

        # 2) memory 策略
        memory_enabled = bool(memory_cfg.get("enabled", True))
        memory_top_k = _as_int(memory_cfg.get("retrieval_top_k"), 5)
        summary_threshold = None
        if "summary_threshold" in memory_cfg:
            summary_threshold = _as_int(memory_cfg.get("summary_threshold"), 0)
        self.memory_manager.ensure_memory_config(identity, summary_threshold=summary_threshold)

        # 3) context 策略
        max_chars = _as_int(context_cfg.get("max_chars"), 0)

        # 4) Memory 获取（summary 永远置顶；primary_recent 不参与排序）
        if memory_enabled:
            mem = self.memory_manager.get_context(identity, user_query, top_k=memory_top_k)
        else:
            mem = {"summary": None, "primary_recent": [], "auxiliary": []}

        summary = mem.get("summary")

        primary_blocks = [
            {"type": "primary", "text": x.get("text", ""), "role": x.get("role", "user")}
            for x in (mem.get("primary_recent") or [])
            if x and x.get("text")
        ]

        aux_blocks = []
        for h in (mem.get("auxiliary") or []):
            if not h:
                continue
            aux_blocks.append(
                {
                    "type": "memory",
                    "text": h.get("text", ""),
                    "score": float(h.get("score") or 0.0),
                    "meta": h.get("meta") or {},
                }
            )
        aux_blocks.sort(key=lambda x: x["score"], reverse=True)

        # 5) KB 检索（中台化：kb_cfg 来自插件 config.yaml）
        kb_exclude = set(intent_params.get("_kb_exclude") or [])
        if kb_exclude:
            kb_cfg = {k: v for k, v in kb_cfg.items() if k not in kb_exclude}

        kb_hits = self.kb_manager.search(
            identity=identity,
            query=user_query,
            kb_configs=kb_cfg,
        )

        kb_blocks = []
        for b in kb_hits:
            kb_blocks.append(
                {
                    "type": "kb",
                    "kb_key": b.kb_key,
                    "source": b.source,
                    "text": b.text,
                    "score": float(b.score or 0.0),
                    "metadata": b.metadata or {},
                }
            )

        # 6) 合并候选块并排序（summary 不参与；primary 不排序）
        ranked_blocks = _merge_ranked_blocks(aux_blocks=aux_blocks, kb_blocks=kb_blocks)

        # 7) 拼最终 context_blocks：primary(不排序) + ranked(排序后)
        context_blocks = primary_blocks + ranked_blocks

        # 8) 按 max_chars 裁剪（仍然不影响 summary）
        if max_chars > 0:
            context_blocks = _clip_blocks_by_chars(context_blocks, max_chars=max_chars)

        # 9) build prompt（intent_params 仅作为模板变量）
        messages = self.prompt_builder.build(
            identity=identity,
            app_id=app_id,
            intent=intent,
            user_query=user_query,
            summary=summary,
            context_blocks=context_blocks,
            intent_params=intent_params,
            app_config=cfg,
        )

        # 10) call llm
        result = self.llm_client.chat(messages, app_id=app_id, intent=intent)
        content = result.get("content") if isinstance(result, dict) else result

        return {
            "answer": content,
            "debug": {
                "app_id": app_id,
                "intent": intent,
                "summary": bool(summary),
                "primary_recent": len(primary_blocks),
                "aux_hits": len(aux_blocks),
                "kb_hits": len(kb_blocks),
                "memory_top_k": memory_top_k if memory_enabled else 0,
                "max_chars": max_chars,
            },
        }
