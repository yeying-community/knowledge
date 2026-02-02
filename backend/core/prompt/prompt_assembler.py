# core/prompt/prompt_assembler.py
# -*- coding: utf-8 -*-
from typing import List, Dict


def assemble_messages(
    global_system: str,
    app_system: str,
    user_prompt: str,
) -> List[Dict[str, str]]:
    """
    将三层 prompt 组合成 LLM 可用的 messages。

    当前策略：
    - global system + app system 合并为一个 system message
    - intent prompt 作为 user message
    """

    system_content = "\n\n".join(
        part for part in [global_system, app_system] if part
    )

    messages = [
        {
            "role": "system",
            "content": system_content,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

    return messages
