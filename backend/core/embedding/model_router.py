# core/embedding/model_router.py
# -*- coding: utf-8 -*-

from .providers.openai import OpenAIEmbeddingProvider
from typing import Any, Optional

class EmbeddingModelRouter:
    """
    v1：统一返回一个 embedding provider
    后续你要按 app_id / 场景路由不同 embedding 模型，再在这里扩展。
    """

    def __init__(self, settings: Any):
        self.settings = settings

    def get_provider(self, *, app_id: Optional[str] = None):
        # 现在不按 app_id 分流：统一用 settings 配置的 embedding
        return OpenAIEmbeddingProvider(settings=self.settings)
