# core/runtime/plugin_context.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from datasource.base import Datasource
from datasource.objectstores.path_builder import PathBuilder
from identity.models import Identity
from settings.config import Settings
from core.orchestrator.app_registry import AppRegistry
from core.orchestrator.query_orchestrator import QueryOrchestrator


def _clip_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return text
    if text and len(text) > max_chars:
        return text[:max_chars]
    return text


def _extract_text(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw[:1] not in ("{", "["):
        return raw
    try:
        data = json.loads(raw)
    except Exception:
        return raw
    if isinstance(data, dict):
        for key in ("text", "content", "resume", "jd"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        segments = data.get("segments")
        if isinstance(segments, list):
            return "\n".join(str(x) for x in segments if x)
        return raw
    if isinstance(data, list):
        return "\n".join(str(x) for x in data if x)
    return raw


def _resolve_minio_key(bucket: str, identity: Identity, url: str) -> str:
    raw = (url or "").strip()
    if raw.startswith("minio://"):
        raw = raw[len("minio://") :]
    key = raw.lstrip("/")
    if key.startswith(f"{bucket}/"):
        key = key[len(bucket) + 1 :]
    if key.startswith("memory/") or key.startswith("kb/"):
        return key
    return PathBuilder.business_file(identity, key)


@dataclass
class PluginContext:
    settings: Settings
    datasource: Datasource
    app_registry: AppRegistry
    orchestrator: QueryOrchestrator

    def load_text_from_minio(
        self,
        identity: Identity,
        url: Optional[str],
        *,
        field_name: str = "file",
        max_chars: int = 0,
    ) -> str:
        if not url:
            return ""
        if not self.datasource.minio:
            raise RuntimeError("MinIO is not enabled")
        bucket = self.datasource.bucket
        key = _resolve_minio_key(bucket, identity, url)
        try:
            raw = self.datasource.minio.get_text(bucket=bucket, key=key)
        except Exception:
            raise FileNotFoundError(f"{field_name} not found: {key}")
        text = _extract_text(raw)
        if not text:
            raise ValueError(f"{field_name} empty: {key}")
        return _clip_text(text, max_chars)
