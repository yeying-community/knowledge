# core/prompt/prompt_loader.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional


class PromptLoader:
    """
    负责从文件系统加载 Prompt 模板。
    - 支持缓存
    - 支持预加载插件 prompts
    - 不做渲染、不关心 context，只返回原始模板文本
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self._cache: Dict[str, str] = {}  # key -> template text

    # ------------------------------------------------------------------
    # Global Prompt
    # ------------------------------------------------------------------
    def load_global_system(self) -> str:
        path = self.project_root / "core" / "prompt" / "global_prompts" / "system.md"
        return self._read_cached(f"global:system", path)

    # ------------------------------------------------------------------
    # App-level Prompt
    # ------------------------------------------------------------------
    def load_app_system(self, app_id: str) -> str:
        path = self.project_root / "plugins" / app_id / "prompts" / "system.md"
        return self._read_cached(f"{app_id}:system", path)

    # ------------------------------------------------------------------
    # Intent Prompt
    # ------------------------------------------------------------------
    def load_intent(self, app_id: str, intent: str) -> str:
        path = self.project_root / "plugins" / app_id / "prompts" / f"{intent}.md"
        return self._read_cached(f"{app_id}:intent:{intent}", path)

    # ------------------------------------------------------------------
    # 预加载 / 校验：在 /app/register 时调用
    # ------------------------------------------------------------------
    def preload_app_prompts(self, app_id: str, strict: bool = True) -> Dict[str, str]:
        """
        预加载一个 app 的所有 prompt 文件到缓存中，并返回 {name: text}

        - strict=True：若缺少 system.md 或 prompts/ 目录不存在，直接报错
        - strict=False：尽最大努力加载，缺失则跳过
        """
        prompts_dir = self.project_root / "plugins" / app_id / "prompts"
        if not prompts_dir.exists():
            if strict:
                raise FileNotFoundError(f"prompts 目录不存在: {prompts_dir}")
            return {}

        out: Dict[str, str] = {}

        system_md = prompts_dir / "system.md"
        if not system_md.exists():
            if strict:
                raise FileNotFoundError(f"缺少 prompts/system.md: {system_md}")
        else:
            out["system"] = self._read_cached(f"{app_id}:system", system_md)

        # 扫描所有 *.md（不含 system.md），作为 intent 模板候选
        for md in sorted(prompts_dir.glob("*.md")):
            if md.name == "system.md":
                continue
            intent = md.stem
            out[intent] = self._read_cached(f"{app_id}:intent:{intent}", md)

        return out

    def clear_cache(self, app_id: Optional[str] = None) -> None:
        """
        - app_id=None：清空全部缓存
        - app_id=xxx：只清空该 app 的缓存
        """
        if app_id is None:
            self._cache.clear()
            return

        prefix = f"{app_id}:"
        keys = [k for k in self._cache.keys() if k.startswith(prefix)]
        for k in keys:
            self._cache.pop(k, None)

    # ------------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------------
    def _read_cached(self, cache_key: str, path: Path) -> str:
        if cache_key in self._cache:
            return self._cache[cache_key]
        text = self._read(path)
        self._cache[cache_key] = text
        return text

    @staticmethod
    def _read(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")
        return path.read_text(encoding="utf-8")
