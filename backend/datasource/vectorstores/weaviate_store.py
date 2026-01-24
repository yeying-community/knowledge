# rag/datasource/vectorstores/weaviate_store.py
# -*- coding: utf-8 -*-
"""
WeaviateStore（新版，无业务，无 schema）
核心原则：
- 不自动创建 collection
- 不写任何业务字段（memory_id / app）
- schema 全由 Memory/Kb 模块控制
"""

from __future__ import annotations

import time
from typing import List, Dict, Any, Optional

import weaviate
import weaviate.classes.config as wc
import weaviate.classes.query as wq
from weaviate.classes.query import Filter

from datasource.connections.weaviate_connection import WeaviateConnection


def _safe_name(name: str) -> str:
    """轻量校验：不改写，仅防空字符串。"""
    s = (name or "").strip()
    if not s:
        raise ValueError("collection name is empty")
    return s


def _build_filters(filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
    if not filters:
        return None
    clauses = [Filter.by_property(k).equal(v) for k, v in filters.items()]
    return Filter.all_of(clauses)


def _is_missing_class_error(err: Exception) -> bool:
    msg = str(err).lower()
    return "could not find class" in msg or "not found in schema" in msg


def _is_already_exists_error(err: Exception) -> bool:
    msg = str(err).lower()
    return "already exists" in msg and "class name" in msg


class WeaviateStore:
    """纯向量数据库客户端"""

    def __init__(self, conn: WeaviateConnection):
        self.conn = conn
        self.client: weaviate.WeaviateClient = conn.client
        self._ensured: set[str] = set()

    # ---------------- Collection 管理 ----------------

    def create_collection(self, name: str, properties: List[wc.Property], embedding: bool = True):
        col = _safe_name(name)
        vector_cfg = wc.Configure.Vectors.self_provided() if embedding else None

        self.client.collections.create(
            name=col,
            properties=properties,
            vector_config=vector_cfg,
        )


    def ensure_collection(self, name: str, properties: List[wc.Property]):
        """Memory/Kb 模块用：确保 collection 存在（幂等）"""
        col = _safe_name(name)

        if col in self._ensured:
            self._ensure_properties(col, properties)
            return

        # 1) 先用 list_all 判断是否存在（这是会真实访问服务端的）
        try:
            existing_names = set(self.list_collections())
        except Exception as e:
            print(f"[weaviate][ensure_collection] list_collections failed: err={e}")
            raise

        exists = col in existing_names
        if not exists:
            # 2) 不存在：创建
            try:
                self.client.collections.create(
                    name=col,
                    properties=properties,
                    vector_config=wc.Configure.Vectors.self_provided(),
                )
            except Exception as e_create:
                if _is_already_exists_error(e_create):
                    exists = True
                else:
                    print(f"[weaviate][ensure_collection] create FAILED: col={col} err={e_create}")
                    raise

            # 3) 创建后轮询验证（处理一致性延迟）
            #    总等待约 0.4 * (1..10) = 22 秒（可按需调整）
            if not exists:
                for i in range(10):
                    time.sleep(0.4 * (i + 1))
                    try:
                        existing_names = set(self.list_collections())
                    except Exception as e_list:
                        print(f"[weaviate][ensure_collection] post-create list failed: i={i} err={e_list}")
                        continue
                    if col in existing_names:
                        exists = True
                        break

        # 4) 已存在：才尝试补字段
        self._ensure_properties(col, properties)
        self._ensured.add(col)

    def _ensure_properties(self, col: str, properties: List[wc.Property]) -> None:
        try:
            existing = self.client.collections.get(col)
        except Exception as e_get:
            if _is_missing_class_error(e_get):
                return
            raise
        for p in properties:
            try:
                existing.config.add_property(p)
            except Exception as e:
                msg = str(e).lower()
                if "already exists" in msg:
                    # 正常幂等场景，静默跳过
                    pass
                else:
                    print(
                        f"[weaviate][ensure_collection] add_property unexpected error: "
                        f"col={col} prop={p.name} err={e}"
                    )
    def list_collections(self) -> List[str]:
        cols = self.client.collections.list_all()
        result = []
        for c in cols:
            result.append(c if isinstance(c, str) else getattr(c, "name", str(c)))
        return result

    # ---------------- 写入 ----------------

    def upsert(
        self,
        collection: str,
        vector: List[float],
        properties: Dict[str, Any],
        object_id: Optional[str] = None,
    ) -> str:
        col = self.client.collections.get(_safe_name(collection))

        if object_id:
            try:
                col.data.replace(uuid=object_id, properties=properties, vector=vector)
                return object_id
            except Exception as e:
                msg = str(e).lower()
                if "no object" in msg or "not found" in msg:
                    col.data.insert(properties=properties, vector=vector, uuid=object_id)
                    return object_id
                raise

        res = col.data.insert(properties=properties, vector=vector)
        return str(res)

    def batch_upsert(
        self,
        collection: str,
        vectors: List[List[float]],
        properties_list: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        col = self.client.collections.get(_safe_name(collection))
        out: List[str] = []

        with col.batch.dynamic() as batch:
            for i, props in enumerate(properties_list):
                uid = ids[i] if ids else None
                vec = vectors[i]
                if uid:
                    batch.add_object(properties=props, vector=vec, uuid=uid)
                    out.append(uid)
                else:
                    r = batch.add_object(properties=props, vector=vec)
                    out.append(str(r))

        return out

    # ---------------- 搜索 ----------------

    def search(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int = 8,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        col = self.client.collections.get(_safe_name(collection))
        where = _build_filters(filters)

        res = col.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=wq.MetadataQuery(distance=True),
            filters=where,
        )

        hits = []
        for obj in res.objects or []:
            props = obj.properties or {}
            dist = getattr(obj.metadata, "distance", None)
            score = 1 / (1 + dist) if dist is not None else 0.0
            hits.append({
                "properties": props,
                "metadata": {
                    "score": score,
                    "distance": dist,
                },
            })
        return hits

    # ---------------- 文本/HYBRID ----------------

    def hybrid(
        self,
        collection: str,
        text: str,
        vector: Optional[List[float]] = None,
        alpha: float = 0.5,
        top_k: int = 8,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        col = self.client.collections.get(_safe_name(collection))

        where = _build_filters(filters)

        res = col.query.hybrid(
            query=text,
            vector=vector,
            alpha=alpha,
            limit=top_k,
            filters=where,
            return_metadata=wq.MetadataQuery(score=True),
        )

        hits = []
        for obj in res.objects or []:
            props = obj.properties or {}
            hits.append({
                "properties": props,
                "metadata": {
                    "score": getattr(obj.metadata, "score", None),
                },
            })
        return hits

    # ---------------- 列表/统计 ----------------

    def count(self, collection: str, filters: Optional[Dict[str, Any]] = None) -> int:
        col = self.client.collections.get(_safe_name(collection))
        where = _build_filters(filters)
        last_err = None
        for i in range(5):
            try:
                res = col.aggregate.over_all(filters=where, total_count=True)
                return int(getattr(res, "total_count", 0) or 0)
            except Exception as e:
                if not _is_missing_class_error(e):
                    raise
                last_err = e
                time.sleep(0.4 * (i + 1))
        if last_err:
            raise last_err
        return 0

    def fetch_objects(
        self,
        collection: str,
        *,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        include_vector: bool = False,
    ) -> List[Dict[str, Any]]:
        col = self.client.collections.get(_safe_name(collection))
        where = _build_filters(filters)
        last_err = None
        for i in range(5):
            try:
                res = col.query.fetch_objects(
                    limit=limit,
                    offset=offset,
                    filters=where,
                    include_vector=include_vector,
                    return_metadata=wq.MetadataQuery(creation_time=True, last_update_time=True),
                    return_properties=True,
                )
                last_err = None
                break
            except Exception as e:
                if not _is_missing_class_error(e):
                    raise
                last_err = e
                time.sleep(0.4 * (i + 1))
        if last_err:
            raise last_err

        out = []
        for obj in getattr(res, "objects", []) or []:
            meta = getattr(obj, "metadata", None)
            out.append(
                {
                    "id": str(getattr(obj, "uuid", "")),
                    "properties": getattr(obj, "properties", {}) or {},
                    "created_at": getattr(meta, "creation_time", None),
                    "updated_at": getattr(meta, "last_update_time", None),
                }
            )
        return out

    def fetch_object_by_id(self, collection: str, object_id: str) -> Optional[Dict[str, Any]]:
        col = self.client.collections.get(_safe_name(collection))
        res = col.query.fetch_object_by_id(
            uuid=object_id,
            return_properties=True,
        )
        if res is None:
            return None
        meta = getattr(res, "metadata", None)
        return {
            "id": str(getattr(res, "uuid", "")),
            "properties": getattr(res, "properties", {}) or {},
            "created_at": getattr(meta, "creation_time", None),
            "updated_at": getattr(meta, "last_update_time", None),
        }

    # ---------------- 删除 ----------------

    def delete_by_id(self, collection: str, object_id: str):
        col = self.client.collections.get(_safe_name(collection))
        col.data.delete_by_id(object_id)

    def delete_by_filter(self, collection: str, filters: Dict[str, Any]):
        col = self.client.collections.get(_safe_name(collection))
        clauses = [Filter.by_property(k).equal(v) for k, v in filters.items()]
        where = Filter.all_of(clauses)
        col.data.delete_many(where=where)

    def update(
        self,
        collection: str,
        object_id: str,
        *,
        properties: Optional[Dict[str, Any]] = None,
        vector: Optional[List[float]] = None,
    ) -> None:
        col = self.client.collections.get(_safe_name(collection))
        col.data.update(
            uuid=object_id,
            properties=properties if properties else None,
            vector=vector,
        )

    def get_properties_by_id(self, collection: str, object_id: str) -> Optional[Dict[str, Any]]:
        """
        通过 uuid 获取对象 properties。
        - 存在：返回 dict
        - 不存在：返回 None
        """
        col = self.client.collections.get(_safe_name(collection))
        try:
            obj = col.query.fetch_object_by_id(uuid=object_id)
        except Exception:
            # fetch 本身异常（网络/权限/协议），往上抛，让上层计入 errors
            raise

        if obj is None:
            return None
        props = getattr(obj, "properties", None)
        return props or None
