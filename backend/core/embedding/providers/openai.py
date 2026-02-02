# core/embedding/providers/openai.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI


class OpenAIEmbeddingProvider:
    """
    OpenAI-compatible Embedding Provider
    - 从 Settings 读取 embed_api_key / embed_api_base / embed_model / embed_dim
    - 强制使用 base_url，避免默认打到 OpenAI 官方导致 401
    """

    PROVIDER_NAME = "openai-compatible-embedding"

    def __init__(self, settings: Any):
        api_key = getattr(settings, "embed_api_key", "") or ""
        api_base = getattr(settings, "embed_api_base", "") or ""
        model = getattr(settings, "embed_model", "") or ""
        embed_dim = getattr(settings, "embed_dim", None)

        if not api_key:
            raise RuntimeError("Embedding config missing: embed_api_key (Settings.embed_api_key)")
        if not api_base:
            raise RuntimeError("Embedding config missing: embed_api_base (Settings.embed_api_base)")
        if not model:
            raise RuntimeError("Embedding config missing: embed_model (Settings.embed_model)")

        self.model: str = str(model).strip()
        self.embed_dim: Optional[int] = self._coerce_int(embed_dim)

        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
        )

    @staticmethod
    def _coerce_int(v: Any) -> Optional[int]:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        s = str(v).strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            return None

    def embed(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        """
        kwargs 透传给 embeddings.create（如果厂商支持额外参数）
        """
        texts = [t for t in texts if isinstance(t, str) and t.strip()]
        if not texts:
            return []

        # 避免重复键冲突
        clean_kwargs: Dict[str, Any] = dict(kwargs)
        clean_kwargs.pop("model", None)
        clean_kwargs.pop("input", None)

        resp = self.client.embeddings.create(
            model=self.model,
            input=texts,
            **clean_kwargs,
        )

        vectors = [item.embedding for item in resp.data]

        # 可选：维度校验（不强制，但能提前发现模型/配置不一致）
        if self.embed_dim is not None:
            for i, vec in enumerate(vectors):
                if len(vec) != self.embed_dim:
                    raise RuntimeError(
                        f"Embedding dim mismatch at index={i}: got {len(vec)} expected {self.embed_dim}. "
                        f"Check Settings.embed_dim or embed model."
                    )

        return vectors
