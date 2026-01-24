# core/kb/kb_manager.py
from __future__ import annotations

from typing import List, Optional, Dict, Any

from .kb_registry import KBRegistry, KBConfig
from .types import KBContextBlock
from ..embedding.embedding_client import EmbeddingClient
from identity.models import Identity


def _as_int(v: Any, default: int) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def _as_float(v: Any, default: float) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _score_from_meta(meta: Dict[str, Any]) -> float:
    """
    Weaviate 可能返回 metadata.score 或 metadata.distance
    统一输出：越大越相关
    """
    if not meta:
        return 0.0

    raw_score = meta.get("score")
    if raw_score is not None:
        try:
            return float(raw_score)
        except Exception:
            return 0.0

    dist = meta.get("distance")
    if dist is not None:
        try:
            return 1.0 / (1.0 + float(dist))
        except Exception:
            return 0.0

    return 0.0


class KnowledgeBaseManager:
    """
    KB 统一检索入口（中台核心组件）
    - 由插件 config.yaml 的 knowledge_bases 驱动
    - 每个 KB 可配置：type / collection / top_k / weight
    - user_upload 采用统一 collection + filters（wallet_id + allowed_apps）
    """

    def __init__(self, ds, embedding_client: EmbeddingClient, kb_registry=None):
        self.ds = ds
        self.embedding = embedding_client
        # kb_registry 保留兼容（但中台化版本不依赖它）
        self.registry = kb_registry

    def search(
        self,
        identity: Identity,
        query: str,
        kb_configs: Optional[Dict[str, Any]] = None,
        global_top_k: Optional[int] = None,
    ) -> List[KBContextBlock]:
        if not query or not self.ds.weaviate:
            return []

        kb_configs = kb_configs or {}
        if not isinstance(kb_configs, dict) or not kb_configs:
            # 没有声明 KB，则不检索
            return []

        # 1) query embedding
        qvec = self.embedding.embed_one(query, app_id=identity.app_id)

        blocks: List[KBContextBlock] = []

        # 2) 遍历插件声明的 KB
        for kb_key, cfg in kb_configs.items():
            if not isinstance(cfg, dict):
                continue

            kb_type = str(cfg.get("type") or "")
            collection = str(cfg.get("collection") or "").strip()
            if not collection:
                # 没声明 collection 直接跳过
                continue

            top_k = _as_int(cfg.get("top_k"), 5)
            weight = _as_float(cfg.get("weight"), 1.0)

            # 3) filters（user_upload 推荐统一 collection + filters）
            filters: Dict[str, Any] = {}

            if kb_type == "user_upload":
                # 必须按 private_db_id 过滤，避免不同私有库互相看到
                if identity.private_db_id:
                    filters["private_db_id"] = identity.private_db_id
                else:
                    filters["wallet_id"] = identity.wallet_id

                # 如果在写入 user_upload KB 的时候给每条 chunk/文档存了 allowed_apps
                # 那就按 app_id 再过滤一层（可选但强烈建议）
                if cfg.get("use_allowed_apps_filter"):
                    filters["allowed_apps"] = identity.app_id


            # 4) weaviate search
            try:
                hits = self.ds.weaviate.search(
                    collection=collection,
                    query_vector=qvec,
                    top_k=max(top_k, 0),
                    filters=filters if filters else None,
                )
            except Exception:
                continue

            # 5) 统一成 KBContextBlock
            for h in hits or []:
                props = h.get("properties") or {}
                meta = h.get("metadata") or {}

                text = props.get("text") or props.get("content") or ""
                if not text:
                    continue

                base_score = _score_from_meta(meta)
                final_score = base_score * weight

                enriched_meta = dict(props)
                enriched_meta.update(
                    {
                        "_collection": collection,
                        "_kb_key": kb_key,
                        "_kb_type": kb_type,
                        "_weight": weight,
                        "_base_score": base_score,
                    }
                )

                blocks.append(
                    KBContextBlock(
                        type="kb",
                        kb_key=kb_key,
                        source=collection,
                        text=text,
                        score=final_score,
                        metadata=enriched_meta,
                    )
                )

        # 6) 合并排序（越大越相关）
        blocks.sort(key=lambda b: float(b.score or 0.0), reverse=True)

        if global_top_k is not None:
            global_top_k = max(int(global_top_k), 0)
            blocks = blocks[:global_top_k]

        return blocks
