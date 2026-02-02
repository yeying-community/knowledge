# core/orchestrator/app_registry.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


@dataclass(frozen=True)
class IntentSpec:
    name: str
    description: str = ""
    params: Tuple[str, ...] = ()
    exposed: bool = True


@dataclass(frozen=True)
class AppSpec:
    app_id: str
    plugin_dir: Path
    config: Dict[str, Any]
    intents: Dict[str, IntentSpec]


class AppRegistry:
    """
    App 插件加载器（不再承担“注册事实”）：
    - 负责从 plugins/<app_id> 目录加载 config.yaml / intents.yaml / prompts
    - 不负责：是否启用（由 SQLite app_registry 表决定）
    - 不负责：pipeline 实例化（由 PipelineRegistry 按需加载）
    """

    def __init__(self, project_root: str, plugins_dirname: str = "plugins") -> None:
        self.project_root = Path(project_root)
        self.plugins_root = self.project_root / plugins_dirname

    def get(self, app_id: str) -> AppSpec:
        # 不做内存注册校验，直接按需加载
        return self.register_app(app_id)

    def register_app(self, app_id: str) -> AppSpec:
        if not app_id:
            raise ValueError("app_id 不能为空")

        plugin_dir = self.plugins_root / app_id
        if not plugin_dir.exists():
            raise FileNotFoundError(f"插件目录不存在: {plugin_dir}")

        config = self._load_yaml(plugin_dir / "config.yaml")
        intents_raw = self._load_yaml(plugin_dir / "intents.yaml")

        self._validate_config(app_id, config)
        intents = self._parse_intents(intents_raw)

        prompts_dir = plugin_dir / "prompts"
        if not prompts_dir.exists():
            raise FileNotFoundError(f"prompts 目录不存在: {prompts_dir}")

        system_md = prompts_dir / "system.md"
        if not system_md.exists():
            raise FileNotFoundError(f"缺少 prompts/system.md: {system_md}")

        return AppSpec(
            app_id=app_id,
            plugin_dir=plugin_dir,
            config=config,
            intents=intents,
        )

    def is_registered(self, app_id: str) -> bool:
        # 语义调整：这里只判断插件是否存在；是否启用请查 DB
        try:
            d = self.plugins_root / app_id
            return d.exists() and d.is_dir()
        except Exception:
            return False

    def list_apps(self) -> List[str]:
        # 直接扫描 plugins 目录（不依赖内存）
        if not self.plugins_root.exists():
            return []
        return sorted([p.name for p in self.plugins_root.iterdir() if p.is_dir()])

    def list_intents(self, app_id: str) -> List[str]:
        spec = self.get(app_id)
        return sorted(spec.intents.keys())

    def list_exposed_intents(self, app_id: str) -> List[str]:
        spec = self.get(app_id)
        return sorted([k for k, v in spec.intents.items() if v.exposed])

    def get_intent_spec(self, app_id: str, intent: str) -> IntentSpec:
        spec = self.get(app_id)
        if intent not in spec.intents:
            raise KeyError(f"intent 未在 intents.yaml 声明: app_id={app_id}, intent={intent}")
        return spec.intents[intent]

    def is_intent_exposed(self, app_id: str, intent: str) -> bool:
        try:
            return self.get_intent_spec(app_id, intent).exposed
        except KeyError:
            return False

    # -------------------------
    # Internal helpers
    # -------------------------
    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"缺少文件: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"YAML 必须为 dict: {path}")
        return data

    @staticmethod
    def _validate_config(app_id: str, config: Dict[str, Any]) -> None:
        cfg_app_id = (config.get("app_id") or "").strip()
        if cfg_app_id and cfg_app_id != app_id:
            raise ValueError(f"config.yaml 中 app_id={cfg_app_id} 与目录 app_id={app_id} 不一致")

        enabled = config.get("enabled", True)
        if enabled not in (True, False):
            raise ValueError("config.yaml enabled 必须为 bool")

        if "memory" in config and not isinstance(config["memory"], dict):
            raise ValueError("config.yaml memory 必须为 dict")
        if "knowledge_bases" in config and not isinstance(config["knowledge_bases"], dict):
            raise ValueError("config.yaml knowledge_bases 必须为 dict")
        if "prompt" in config and not isinstance(config["prompt"], dict):
            raise ValueError("config.yaml prompt 必须为 dict")
        prompt_cfg = config.get("prompt") or {}
        if isinstance(prompt_cfg, dict):
            if "kb_aliases" in prompt_cfg and not isinstance(prompt_cfg["kb_aliases"], dict):
                raise ValueError("config.yaml prompt.kb_aliases 必须为 dict")
            if "optional_vars" in prompt_cfg and not isinstance(prompt_cfg["optional_vars"], list):
                raise ValueError("config.yaml prompt.optional_vars 必须为 list")

    @staticmethod
    def _parse_intents(intents_raw: Dict[str, Any]) -> Dict[str, IntentSpec]:
        intents_block = intents_raw.get("intents") or {}
        if not isinstance(intents_block, dict):
            raise ValueError("intents.yaml 必须包含 intents: dict")

        intents: Dict[str, IntentSpec] = {}
        for name, meta in intents_block.items():
            if not isinstance(name, str) or not name.strip():
                continue

            meta = meta or {}
            if not isinstance(meta, dict):
                meta = {}

            desc = str(meta.get("description", "") or "")

            params = meta.get("params", []) or []
            if not isinstance(params, list):
                raise ValueError(f"intent={name} 的 params 必须为 list")
            params_norm = tuple(str(p) for p in params if str(p).strip())

            exposed_val = meta.get("exposed", True)
            if exposed_val not in (True, False):
                raise ValueError(f"intent={name} 的 exposed 必须为 bool")
            exposed = bool(exposed_val)

            intents[name] = IntentSpec(
                name=name,
                description=desc,
                params=params_norm,
                exposed=exposed,
            )

        if not intents:
            raise ValueError("intents.yaml 中 intents 不能为空")

        return intents
