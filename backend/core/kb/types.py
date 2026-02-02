# core/kb/types.py
# 定义“中台统一 ContextBlock”
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class KBContextBlock:
    type: str                 # "kb"
    kb_key: str
    source: str               # kb_name
    text: str                 # 用于 prompt 的主要文本
    score: float
    metadata: Dict[str, Any]
