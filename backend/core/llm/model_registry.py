# core/llm/model_registry.py
# -*- coding: utf-8 -*-

from .providers.openai import OpenAILLMProvider


class ModelRegistry:
    """
    后续可按：
    - app_id
    - intent
    - 是否 reasoning
    路由模型
    """

    def get_provider(self, *, settings, app_id: str | None = None, intent: str | None = None):
        # 暂时 v1：统一模型
        return OpenAILLMProvider(settings)
