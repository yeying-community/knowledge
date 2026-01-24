# core/llm/providers/openai.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI


class OpenAILLMProvider:
    """
    OpenAI Provider（Chat Completions）
    - 支持 OpenAI 式参数透传（kwargs）
    - 支持 stream=True 时自动聚合输出 content
    - 支持自定义 base_url（OPENAI_API_BASE），方便接入兼容 OpenAI 协议的网关
    """

    PROVIDER_NAME = "openai"

    def __init__(self, settings, model: str = "gpt-4.1-mini", temperature: float = 0.2) -> None:
        api_key = settings.openai_api_key
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        base_url = settings.openai_api_base  # 可为空：用官方默认
        self.model: str = settings.openai_model
        if not self.model:
            raise RuntimeError("OPENAI_MODEL is empty")

        self.temperature: float = float(temperature)


        # OpenAI 官方 Python SDK client
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=2)

    def chat(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        对齐 LLMClient.chat 的稳定入口：
        - messages 必填
        - model/temperature 可覆盖默认
        - 其它 OpenAI 参数全部从 kwargs 透传（tools/tool_choice/response_format/stream/...）
        """
        final_model = (model or self.model).strip()
        final_temperature = self.temperature if temperature is None else float(temperature)

        # 避免用户 kwargs 里重复传 messages/model/temperature 导致冲突
        clean_kwargs = dict(kwargs)
        clean_kwargs.pop("messages", None)
        clean_kwargs.pop("model", None)
        clean_kwargs.pop("temperature", None)

        # stream 聚合：保持对外返回结构仍是 {"content": "...", "raw": ...}
        stream = bool(clean_kwargs.get("stream", False))

        if not stream:
            resp = self.client.chat.completions.create(
                model=final_model,
                messages=messages,
                temperature=final_temperature,
                **clean_kwargs,
            )
            content, usage = self._extract_chat_content_and_usage(resp)
            return {
                "content": content,
                "raw": resp,
                "model": final_model,
                "usage": usage,
                "provider": self.PROVIDER_NAME,
            }

        # stream=True：迭代流事件并拼接增量内容
        # 注意：不同 SDK/网关的事件结构可能略有差异，这里做尽量兼容的提取。
        chunks = []
        parts: List[str] = []

        resp_stream = self.client.chat.completions.create(
            model=final_model,
            messages=messages,
            temperature=final_temperature,
            **clean_kwargs,
        )

        for event in resp_stream:
            chunks.append(event)
            delta = None
            try:
                # OpenAI SDK 常见：event.choices[0].delta.content
                delta = getattr(event.choices[0].delta, "content", None)  # type: ignore[attr-defined]
            except Exception:
                delta = None

            if isinstance(delta, str) and delta:
                parts.append(delta)

        content = "".join(parts).strip() if parts else None
        return {
            "content": content,
            "raw": chunks,  # 原始流事件列表
            "model": final_model,
            "usage": None,  # 流式通常需要额外处理 usage，这里先不强求
            "provider": self.PROVIDER_NAME,
        }

    @staticmethod
    def _extract_chat_content_and_usage(resp: Any) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        content: Optional[str] = None
        usage: Optional[Dict[str, Any]] = None

        try:
            choice = resp.choices[0]
            msg = getattr(choice, "message", None)
            content = getattr(msg, "content", None)
        except Exception:
            content = None

        try:
            u = getattr(resp, "usage", None)
            if u is not None:
                # usage 可能是 pydantic 模型 / 对象，这里尽量转 dict
                usage = u.model_dump() if hasattr(u, "model_dump") else dict(u)
        except Exception:
            usage = None

        return content, usage
