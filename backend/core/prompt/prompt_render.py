# core/prompt/prompt_render.py
# -*- coding: utf-8 -*-
import re
from typing import Dict, Any, Iterable, Optional

_VAR_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")

def render_template(
    template: str,
    params: Dict[str, Any],
    *,
    strict: bool = True,
    allowed_missing: Optional[Iterable[str]] = None,
) -> str:
    rendered = template
    for key, value in params.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", "" if value is None else str(value))

    # 检查是否仍有未替换变量
    missing = set(_VAR_PATTERN.findall(rendered))
    if allowed_missing:
        missing -= set(allowed_missing)

    if missing and strict:
        raise ValueError(f"Unresolved template variables: {sorted(missing)}")

    return rendered
