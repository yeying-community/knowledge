# plugins/interviewer/ingestion/jd_schema.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import List

import weaviate.classes.config as wc

from datasource.vectorstores.weaviate_store import WeaviateStore


DEFAULT_JD_COLLECTION = "kb_interviewer_jd"


def jd_properties() -> List[wc.Property]:
    """
    interviewer JD 的基础 schema（可扩展）
    - 最小必需：job_id, content
    - 其余字段用于 pipeline 适配/调试/溯源
    """
    T = wc.DataType.TEXT

    return [
        wc.Property(name="job_id", data_type=T),
        wc.Property(name="content", data_type=T),

        wc.Property(name="company", data_type=T),
        wc.Property(name="position", data_type=T),
        wc.Property(name="department", data_type=T),
        wc.Property(name="product", data_type=T),
        wc.Property(name="category", data_type=T),
        wc.Property(name="location", data_type=T),
        wc.Property(name="experience", data_type=T),
        wc.Property(name="education", data_type=T),
        wc.Property(name="requirements", data_type=T),
        wc.Property(name="description", data_type=T),

        wc.Property(name="hash", data_type=T),
        wc.Property(name="status", data_type=T),

        wc.Property(name="source_bucket", data_type=T),
        wc.Property(name="source_key", data_type=T),
        wc.Property(name="crawl_date", data_type=T),
        wc.Property(name="publish_time", data_type=T),
        wc.Property(name="modify_time", data_type=T),
        wc.Property(name="crawler_time", data_type=T),
        wc.Property(name="vectorized_at", data_type=T),
    ]


def ensure_jd_collection(
    weaviate_store: WeaviateStore,
    *,
    collection: str = DEFAULT_JD_COLLECTION,
) -> None:
    """
    幂等确保 collection 存在 + 尝试补齐字段。
    WeaviateStore.ensure_collection 已实现“先 list 判断，再 create，再 add_property”的幂等策略。
    """
    weaviate_store.ensure_collection(collection, jd_properties())
