# core/kb/kb_registry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class KBConfig:
    name: str                 # 逻辑名：jd_kb / user_kb
    collection: str           # weaviate collection
    top_k: int = 3
    text_field: str = "text"  # 主文本字段
    weight: float = 1.0       # 融合权重（KB 层只做“加权得分”，不做 rerank）
    is_user_kb: bool = False  # 是否用户私有 KB（需要按 wallet_id / allowed_apps 过滤）


class KBRegistry:
    """
    中台级 KB 注册表：
    - 只在 /app/register 阶段写
    - query 阶段只读
    """

    def __init__(self) -> None:
        self._app_kbs: Dict[str, List[KBConfig]] = {}

    def register_app(self, app_id: str, kbs: List[KBConfig]) -> None:
        if not app_id:
            raise ValueError("app_id is empty")
        if app_id in self._app_kbs:
            raise RuntimeError(f"KB already registered for app_id={app_id}")

        normalized: List[KBConfig] = []
        for kb in (kbs or []):
            if not kb.name:
                raise ValueError("KBConfig.name is empty")
            if not kb.collection:
                raise ValueError(f"KBConfig.collection is empty for kb={kb.name}")

            top_k = max(int(kb.top_k or 1), 1)
            weight = float(kb.weight if kb.weight is not None else 1.0)
            if weight < 0:
                weight = 0.0

            text_field = kb.text_field or "text"

            normalized.append(
                KBConfig(
                    name=kb.name,
                    collection=kb.collection,
                    top_k=top_k,
                    text_field=text_field,
                    weight=weight,
                    is_user_kb=bool(kb.is_user_kb),
                )
            )

        self._app_kbs[app_id] = normalized

    def get_kbs(self, app_id: str) -> List[KBConfig]:
        return self._app_kbs.get(app_id, []).copy()
