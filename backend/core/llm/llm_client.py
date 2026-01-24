# core/llm/llm_client.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Dict, List, Optional

from settings.config import Settings
from .model_registry import ModelRegistry


class LLMClient:
    """
    对外接口保持稳定：
      - chat(messages, app_id=None, intent=None, **kwargs) -> Dict[str, Any]

    约定返回：
      {
        "content": str | None,
        "raw": Any,             # provider 的原始响应/流事件
        "model": str | None,    # 实际使用的模型（如果 provider 提供）
        "usage": dict | None,   # 如果 provider 能解析
        "provider": str,        # 例如 "openai"
      }
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()
        self.registry = ModelRegistry()

    def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        app_id: Optional[str] = None,
        intent: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        保持你原有对外调用方式不变，并允许 OpenAI 风格参数透传：
          tools/tool_choice/response_format/max_tokens/top_p/stream/seed/...
        """
        provider = self.registry.get_provider(settings=self.settings, app_id=app_id, intent=intent)

        # 统一只走 provider.chat，避免“猜方法名”造成不一致
        if not hasattr(provider, "chat"):
            raise RuntimeError(f"LLM provider {type(provider)} does not implement chat()")

        return provider.chat(messages=messages, **kwargs)
