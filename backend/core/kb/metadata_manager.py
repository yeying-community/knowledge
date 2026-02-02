# core/kb/kb_manager.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...datasource.base import Datasource
from ..embedding.embedding_client import EmbeddingClient  # 你之前为记忆服务写的那个
from ...identity.models import Identity  # 已有的 identity 对象
from .kb_registry import KBRegistry, KBConfig


class KnowledgeBaseManager:
    """
    统一 KB 管理与检索（中台核心组件）

    只负责“从多个 KB 中检索候选片段”，不做：
    - chunk
    - rerank（只按 score 排序）
    - prompt 拼接

    使用方式（示例）：
        kb_manager = KnowledgeBaseManager(ds, embedding_client, kb_registry)
        results = kb_manager.search(identity, query)
    """

    def __init__(
        self,
        ds: Datasource,
        embedding_client: EmbeddingClient,
        kb_registry: KBRegistry,
    ) -> None:
        self.ds = ds
        self.embedding = embedding_client
        self.registry = kb_registry

    # ------------------------------------------------------------------
    # 检索入口
    # ------------------------------------------------------------------
    def search(
        self,
        identity: Identity,
        query: str,
        override_kbs: Optional[List[KBConfig]] = None,
    ) -> List[Dict[str, Any]]:
        """
        在当前 app 声明的所有 KB 中做多库检索。

        返回统一结构的 list，每一项是：
            {
                "kb_name": "jd_kb",
                "collection": "InterviewerJDKnowledge",
                "score": 0.83,
                "distance": 0.17,
                "properties": {...},   # 底层对象的所有字段（供 pipeline 自己决定怎么拼 context）
            }

        说明：
        - identity 现在主要用 app_id（未来 user_kb 会用到 wallet_id）
        - override_kbs 用于一些特殊 pipeline 想临时换一套 KB 列表
        """
        # 1）拿到该 app 的 KB 列表
        if override_kbs is not None:
            kb_list = override_kbs
        else:
            kb_list = self.registry.get_kbs_for_app(identity.app_id)

        if not kb_list or not self.ds.weaviate:
            return []

        # 2）对 query 做一次 embedding
        qvec = self.embedding.embed(query)

        # 3）在每个 KB 中检索
        merged_hits: List[Dict[str, Any]] = []

        for kb in kb_list:
            top_k = max(kb.top_k, 1)

            # 目前只考虑“集合级”区分，不做 metadata 过滤
            hits = self.ds.weaviate.search(
                collection=kb.collection,
                query_vector=qvec,
                top_k=top_k,
                filters=None,  # 未来 user_kb 会在这里加 wallet_id / allowed_apps 过滤
            )

            for h in hits:
                props = h.get("properties") or {}
                meta = h.get("metadata") or {}
                merged_hits.append(
                    {
                        "kb_name": kb.name,
                        "collection": kb.collection,
                        "score": meta.get("score"),
                        "distance": meta.get("distance"),
                        "properties": props,
                    }
                )

        # 4）简单按 score 排序（后续可以接入 rerank 模块）
        merged_hits.sort(
            key=lambda x: (x["score"] if x["score"] is not None else 0.0),
            reverse=True,
        )

        return merged_hits
