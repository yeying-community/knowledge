# core/memory/auxiliary_memory.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import List, Dict, Optional
import weaviate.classes.config as wc
import uuid
from ..embedding.embedding_client import EmbeddingClient
from identity.models import Identity
from datasource.base import Datasource


class AuxiliaryMemory:
    """
    辅助记忆（向量检索）
    - 使用统一 collection：MemoryVectors
    - 按 memory_key 过滤
    """

    COLLECTION_NAME = "MemoryVectors"

    def __init__(self, ds: Datasource, embedding_client: EmbeddingClient):
        self.ds = ds
        self.embedding = embedding_client
        self._schema_ready = False

    @ staticmethod
    def _stable_uuid(uid: str) -> str:
        """
        将业务侧 uid 映射为合法 UUID（幂等且可复现）。
        """
        return str(uuid.uuid5(uuid.NAMESPACE_URL, str(uid)))
    # ---------------------------------------------------
    # 写入
    # ---------------------------------------------------

    def write(self, identity: Identity, uid: str, text: str, role: str) -> Optional[str]:
        if not self.ds.weaviate or not text:
            return None

        vector = self.embedding.embed_one(text, app_id=identity.app_id)

        if not self._schema_ready:
            self._ensure_collection()
            self._schema_ready = True

        properties = {
            "memory_key": identity.memory_key,
            "wallet_id": identity.wallet_id,
            "app_id": identity.app_id,
            "uid": uid,
            "role": role,
            "text": text,
        }

        return self.ds.weaviate.upsert(
            collection=self.COLLECTION_NAME,
            vector=vector,
            properties=properties,
            object_id=self._stable_uuid(uid),
        )

    # ---------------------------------------------------
    # 检索
    # ---------------------------------------------------

    def search(self, identity: Identity, query: str, top_k: int = 5) -> List[Dict]:
        if not self.ds.weaviate or not query:
            return []
        if not self._schema_ready:
            self._ensure_collection()
            self._schema_ready = True

        top_k = max(top_k, 1)
        qvector = self.embedding.embed_one(query, app_id=identity.app_id)

        hits = self.ds.weaviate.search(
            collection=self.COLLECTION_NAME,
            query_vector=qvector,
            top_k=top_k,
            filters={"memory_key": identity.memory_key},
        )

        results = []
        for h in hits:
            props = h.get("properties") or {}
            meta = h.get("metadata") or {}

            # 统一 score 语义
            score = meta.get("score")
            if score is None and meta.get("distance") is not None:
                score = 1.0 / (1.0 + float(meta["distance"]))

            results.append({
                "uid": props.get("uid"),
                "role": props.get("role"),
                "text": props.get("text"),
                "score": score or 0.0,
            })

        return results

    # ---------------------------------------------------
    # 建表
    # ---------------------------------------------------

    def _ensure_collection(self):
        self.ds.weaviate.ensure_collection(
            name=self.COLLECTION_NAME,
            properties=[
                wc.Property(name="memory_key", data_type=wc.DataType.TEXT),
                wc.Property(name="wallet_id", data_type=wc.DataType.TEXT),
                wc.Property(name="app_id", data_type=wc.DataType.TEXT),
                wc.Property(name="uid", data_type=wc.DataType.TEXT),
                wc.Property(name="role", data_type=wc.DataType.TEXT),
                wc.Property(name="text", data_type=wc.DataType.TEXT),
            ],
        )
