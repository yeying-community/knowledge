# plugins/interviewer/ingestion/jd_rebuild.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Set

from core.embedding.embedding_client import EmbeddingClient
from datasource.objectstores.minio_store import MinIOStore
from datasource.vectorstores.weaviate_store import WeaviateStore

from .jd_schema import ensure_jd_collection, DEFAULT_JD_COLLECTION


DEFAULT_BUCKET = "company-jd"
DEFAULT_BATCH_SIZE = 32
PROGRESS_EVERY = 100
DEFAULT_APP_ID = "interviewer"

# 稳定 UUID 映射：同一个 job_id 永远得到同一个 UUID
JD_UUID_NAMESPACE = uuid.UUID("2f4a0c8d-6c3a-4a0e-9c6f-6d9c7a8d2c11")


@dataclass
class RebuildStats:
    companies: int = 0
    manifests_found: int = 0
    jd_total: int = 0
    jd_upserted: int = 0
    jd_deleted: int = 0
    jd_skipped: int = 0
    errors: int = 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def _jd_object_id(job_id: str) -> str:
    """
    将任意 job_id（可能是纯数字/短字符串）映射为合法 UUID 字符串。
    采用 UUIDv5：稳定、可重复、无碰撞风险可忽略。
    """
    return str(uuid.uuid5(JD_UUID_NAMESPACE, job_id))


def _compose_content(jd: Dict) -> str:
    parts: List[str] = []

    def add(k: str, label: str):
        v = _safe_str(jd.get(k))
        if v:
            parts.append(f"{label}：{v}")

    add("company", "公司")
    add("category", "类别")
    add("position", "职位")
    add("department", "部门")
    add("product", "产品")
    add("location", "地点")
    add("experience", "经验")
    add("education", "学历")

    req = _safe_str(jd.get("requirements"))
    if req:
        parts.append("任职要求：\n" + req)

    desc = _safe_str(jd.get("description"))
    if desc:
        parts.append("岗位职责：\n" + desc)

    return "\n".join(parts).strip()


def _extract_company_dates(keys: List[str]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for k in keys:
        parts = k.split("/")
        if len(parts) >= 2:
            company, date = parts[0], parts[1]
            if date.isdigit() and len(date) == 8:
                out.setdefault(company, set()).add(date)
    return out


def rebuild_jd_kb(
    *,
    minio_store: MinIOStore,
    embedding_client: EmbeddingClient,
    weaviate_store: WeaviateStore,
    bucket: str = DEFAULT_BUCKET,
    collection: str = DEFAULT_JD_COLLECTION,
    batch_size: int = DEFAULT_BATCH_SIZE,
    app_id: str = DEFAULT_APP_ID,
) -> RebuildStats:
    """
    全量重建 + hash 增量 + batch embed/upsert
    修复点：Weaviate object_id 使用稳定 UUID 映射，避免 “uuid not valid”。
    """
    stats = RebuildStats()
    t0 = time.time()

    print(f"[jd-rebuild] start bucket={bucket}, collection={collection}, batch_size={batch_size}")

    # 1) schema
    ensure_jd_collection(weaviate_store, collection=collection)

    # 2) embedding 维度探针
    probe = embedding_client.embed_one("ping", app_id=app_id)
    print(f"[jd-rebuild] embedding probe dim={len(probe)}")

    # 3) list keys
    print("[jd-rebuild] listing minio keys...")
    t_list = time.time()
    all_keys = minio_store.list(bucket, prefix="", recursive=True)
    print(f"[jd-rebuild] minio list done: keys={len(all_keys)}, cost={time.time()-t_list:.2f}s")

    company_dates = _extract_company_dates(all_keys)
    companies = sorted(company_dates.keys())
    stats.companies = len(companies)
    print(f"[jd-rebuild] found companies={stats.companies}")

    batch_texts: List[str] = []
    batch_props: List[Dict] = []
    batch_ids: List[str] = []  # Weaviate UUID strings

    def flush_batch(reason: str):
        nonlocal batch_texts, batch_props, batch_ids

        if not batch_texts:
            return

        n = len(batch_texts)
        print(f"[jd-rebuild] flush_batch({reason}): n={n} (embed -> upsert) ...")

        t_embed = time.time()
        vectors = embedding_client.embed(batch_texts, app_id=app_id)
        print(f"[jd-rebuild] batch embedded: n={n}, cost={time.time()-t_embed:.2f}s")

        t_upsert = time.time()
        try:
            weaviate_store.batch_upsert(
                collection=collection,
                vectors=vectors,
                properties_list=batch_props,
                ids=batch_ids,
            )
        except Exception as e:
            print(f"[jd-rebuild] batch upsert FAILED: n={n} err={e}")
            sample_id = batch_ids[0] if batch_ids else ""
            sample_key = batch_props[0].get("source_key") if batch_props else ""
            sample_job = batch_props[0].get("job_id") if batch_props else ""
            print(f"[jd-rebuild] batch upsert FAILED sample: uuid={sample_id} job_id={sample_job} source_key={sample_key}")
            raise

        print(f"[jd-rebuild] batch upserted: n={n}, cost={time.time()-t_upsert:.2f}s")

        stats.jd_upserted += n
        batch_texts, batch_props, batch_ids = [], [], []

    try:
        for company in companies:
            latest = max(company_dates[company])
            manifest_key = f"{company}/{latest}/manifest.json"
            if manifest_key not in all_keys:
                continue

            print(f"[jd-rebuild] company={company}, date={latest}")
            print(f"[jd-rebuild] loading manifest: {manifest_key}")

            t_m = time.time()
            manifest = minio_store.get_json(bucket, manifest_key)
            files = manifest.get("files", []) or []
            print(f"[jd-rebuild] manifest loaded: files={len(files)}, cost={time.time()-t_m:.2f}s")

            stats.manifests_found += 1
            crawl_date = _safe_str(manifest.get("crawl_date") or latest)

            for f in files:
                job_id = ""
                jd_key = ""
                try:
                    job_id = _safe_str(f.get("job_id"))
                    jd_key = _safe_str(f.get("key"))
                    if not job_id or not jd_key:
                        stats.jd_skipped += 1
                        continue

                    stats.jd_total += 1
                    obj_id = _jd_object_id(job_id)  # 合法 UUID

                    jd = minio_store.get_json(bucket, jd_key)
                    if not isinstance(jd, dict):
                        stats.jd_skipped += 1
                        continue

                    status = _safe_str(jd.get("status")).lower()
                    if status == "expired":
                        try:
                            weaviate_store.delete_by_id(collection, obj_id)
                            stats.jd_deleted += 1
                        except Exception as e:
                            stats.errors += 1
                            print(f"[jd-rebuild] delete failed: job_id={job_id} uuid={obj_id} err={e}")
                        continue

                    # hash 增量（用 UUID 查）
                    new_hash = _safe_str(jd.get("hash"))
                    if new_hash:
                        try:
                            existing = weaviate_store.get_properties_by_id(collection, obj_id)
                        except Exception as e:
                            existing = None
                            print(f"[jd-rebuild] get_by_id failed (ignore): job_id={job_id} uuid={obj_id} err={e}")

                        if existing:
                            old_hash = _safe_str(existing.get("hash"))
                            if old_hash and old_hash == new_hash:
                                stats.jd_skipped += 1
                                continue

                    content = _compose_content(jd)
                    if not content:
                        stats.jd_skipped += 1
                        continue

                    batch_texts.append(content)
                    batch_ids.append(obj_id)
                    batch_props.append({
                        # 业务主键仍保存 job_id
                        "job_id": job_id,
                        "content": content,

                        "company": _safe_str(jd.get("company")),
                        "position": _safe_str(jd.get("position")),
                        "department": _safe_str(jd.get("department")),
                        "product": _safe_str(jd.get("product")),
                        "category": _safe_str(jd.get("category")),
                        "location": _safe_str(jd.get("location")),
                        "experience": _safe_str(jd.get("experience")),
                        "education": _safe_str(jd.get("education")),
                        "requirements": _safe_str(jd.get("requirements")),
                        "description": _safe_str(jd.get("description")),

                        "hash": new_hash,
                        "status": _safe_str(jd.get("status")),

                        "source_bucket": bucket,
                        "source_key": jd_key,
                        "crawl_date": crawl_date,
                        "publish_time": _safe_str(jd.get("publish_time")),
                        "modify_time": _safe_str(jd.get("modify_time")),
                        "crawler_time": _safe_str(jd.get("crawler_time")),
                        "vectorized_at": _now_iso(),
                    })

                    if len(batch_texts) == batch_size:
                        flush_batch("batch_full")

                    if stats.jd_total % PROGRESS_EVERY == 0:
                        elapsed = time.time() - t0
                        rate = stats.jd_total / elapsed if elapsed > 0 else 0.0
                        print(
                            f"[jd-rebuild] progress total={stats.jd_total} "
                            f"upserted={stats.jd_upserted} skipped={stats.jd_skipped} "
                            f"deleted={stats.jd_deleted} errors={stats.errors} rate={rate:.2f}/s"
                        )

                except Exception as e:
                    stats.errors += 1
                    print(f"[jd-rebuild] item error: company={company} jd_key={jd_key} job_id={job_id} err={e}")
                    # 如需失败即停，解除注释：
                    # raise

        flush_batch("final")

    except KeyboardInterrupt:
        print("\n[jd-rebuild] interrupted, flushing batch...")
        try:
            flush_batch("interrupt")
        except Exception as e:
            stats.errors += 1
            print(f"[jd-rebuild] flush on interrupt FAILED err={e}")

    elapsed = time.time() - t0
    print(
        f"[jd-rebuild] done total={stats.jd_total} upserted={stats.jd_upserted} "
        f"skipped={stats.jd_skipped} deleted={stats.jd_deleted} "
        f"errors={stats.errors} cost={elapsed:.2f}s"
    )

    return stats
