# core/memory/memory_manager.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import uuid
import hashlib
from typing import Any, Dict, Optional, List

from identity.models import Identity
from datasource.base import Datasource
from core.llm.llm_client import LLMClient
from core.embedding.embedding_client import EmbeddingClient

from core.memory.primary_memory import PrimaryMemory
from core.memory.auxiliary_memory import AuxiliaryMemory
from datasource.objectstores.path_builder import PathBuilder


class MemoryManager:
    """
    Memory 服务门面：
    - push：从 MinIO 读取业务端已写入的 session_history.json，然后写入主记忆(SQLite)+辅助记忆(Weaviate)
    - get_context：summary + 主记忆未摘要最近对话（时间线） + 向量检索命中
    """

    def __init__(self, ds: Datasource, llm: LLMClient, embedder: EmbeddingClient):
        self.ds = ds
        self.llm = llm
        self.embedder = embedder

        self.primary = PrimaryMemory(ds=ds)
        self.aux = AuxiliaryMemory(ds=ds, embedding_client=embedder)

    def ensure_memory_config(self, identity: Identity, summary_threshold: Optional[int] = None) -> None:
        if summary_threshold is None:
            return
        self.ds.memory_primary.ensure_row(
            memory_key=identity.memory_key,
            wallet_id=identity.wallet_id,
            app_id=identity.app_id,
            summary_threshold=int(summary_threshold),
        )

    def push_session_file(
        self,
        identity: Identity,
        filename: str,
        *,
        description: Optional[str] = None,
        summary_threshold: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        业务端约定：先把一个 session 的历史记录写进 MinIO，然后调用 RAG 的 push。
        RAG 按约定路径拼接读取：
          memory/{wallet_id}/{app_id}/{session_id}/{filename}
        """
        url = PathBuilder.business_file(identity, filename)

        if summary_threshold is not None:
            self.ensure_memory_config(identity, summary_threshold=summary_threshold)

        if not self.ds.minio:
            raise RuntimeError("MinIO is not enabled")

        bucket = self.ds.bucket
        raw = self.ds.minio.get_text(bucket=bucket, key=url)
        if not raw:
            raise FileNotFoundError(f"MinIO file not found: bucket={bucket}, key={url}")

        data = json.loads(raw)
        messages = data.get("messages", [])
        if not isinstance(messages, list):
            raise ValueError("Invalid session history json: messages must be a list")

        results = []
        for msg in messages:
            role = (msg.get("role") or "user").strip()
            content = (msg.get("content") or "").strip()
            if not content:
                continue

            uid = str(uuid.uuid4())
            sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

            meta = self.primary.record_message(
                identity=identity,
                uid=uid,
                role=role,
                url=url,
                content_sha256=sha,
                description=description or filename,
            )

            self.aux.write(identity=identity, uid=uid, text=content, role=role)

            results.append(meta)

        self.ds.memory_primary.bump_qa(identity.memory_key, delta=len(results))
        self.primary.maybe_summarize(identity, self.llm)

        return {
            "status": "ok",
            "messages_written": len(results),
            "metas": results,
        }

    def _load_primary_recent(self, identity: Identity) -> List[Dict[str, Any]]:
        if not self.ds.minio:
            return []

        rows = self.ds.memory_contexts.list_all_unsummarized(identity.memory_key)
        if not rows:
            return []

        bucket = self.ds.bucket
        json_cache: Dict[str, dict] = {}
        out: List[Dict[str, Any]] = []

        for r in rows:
            url = r.get("url")
            sha = r.get("content_sha256")
            role = r.get("role", "user")

            if not url or not sha:
                continue

            if url not in json_cache:
                raw = self.ds.minio.get_text(bucket=bucket, key=url)
                if not raw:
                    continue
                try:
                    json_cache[url] = json.loads(raw)
                except Exception:
                    continue

            data = json_cache[url]
            for msg in data.get("messages", []):
                content = msg.get("content", "")
                if not content:
                    continue
                if hashlib.sha256(content.encode("utf-8")).hexdigest() == sha:
                    out.append(
                        {
                            "role": msg.get("role", role),
                            "text": content,
                            "source": "primary",
                            "url": url,
                        }
                    )
                    break

        return out

    def get_context(self, identity: Identity, query: str, top_k: int = 5) -> Dict[str, Any]:
        summary = self.primary.get_summary(identity)
        primary_recent = self._load_primary_recent(identity)
        aux_hits = self.aux.search(identity, query, top_k=top_k)

        return {
            "summary": summary,
            "primary_recent": primary_recent,
            "auxiliary": aux_hits,
        }
