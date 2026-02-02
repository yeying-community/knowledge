# core/embedding/embedding_client.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from .model_router import EmbeddingModelRouter
from settings.config import Settings


class EmbeddingClient:
    """
    对外稳定入口：
      - embed(texts, app_id=None, **kwargs) -> vectors
      - embed_one(text, app_id=None, **kwargs) -> vector
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.router = EmbeddingModelRouter(settings=self.settings)

    def embed(
        self,
        texts: Iterable[str],
        *,
        app_id: Optional[str] = None,
        **kwargs: Any,
    ) -> List[List[float]]:
        texts_list = list(texts)
        if not texts_list:
            return []

        provider = self.router.get_provider(app_id=app_id)
        return provider.embed(texts_list, **kwargs)

    def embed_one(
        self,
        text: str,
        *,
        app_id: Optional[str] = None,
        **kwargs: Any,
    ) -> List[float]:
        vecs = self.embed([text], app_id=app_id, **kwargs)
        return vecs[0] if vecs else []
