# core/orchestrator/pipeline_registry.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Type

from .app_registry import AppRegistry, AppSpec


class BasePipeline:
    def __init__(self, orchestrator: Any) -> None:
        self.orchestrator = orchestrator

    def run(self, *, identity, intent: str, user_query: str, intent_params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass
class PipelineEntry:
    app_id: str
    pipeline: Any
    pipeline_path: Optional[Path] = None


class PipelineRegistry:
    """
    Pipeline Loader（不承担“注册事实”）：
    - get(app_id) 时按需加载 plugins/<app_id>/pipeline.py 并实例化
    - 不要求 /app/register 预注册 pipeline
    """

    def __init__(self, cache_enabled: bool = False) -> None:
        self.cache_enabled = cache_enabled
        self._pipelines: Dict[str, PipelineEntry] = {}

        self._app_registry: Optional[AppRegistry] = None
        self._orchestrator: Any = None
        self._plugin_context: Any = None

    def configure(self, app_registry: AppRegistry, orchestrator: Any, plugin_context: Any = None) -> None:
        self._app_registry = app_registry
        self._orchestrator = orchestrator
        self._plugin_context = plugin_context

    def get(self, app_id: str) -> Any:
        if self.cache_enabled and app_id in self._pipelines:
            pipeline_obj = self._pipelines[app_id].pipeline
            if self._plugin_context is not None:
                setattr(pipeline_obj, "context", self._plugin_context)
            if self._orchestrator is not None:
                setattr(pipeline_obj, "orchestrator", self._orchestrator)
            return pipeline_obj

        if self._app_registry is None or self._orchestrator is None:
            raise KeyError("PipelineRegistry 未配置 app_registry/orchestrator")

        app_spec = self._app_registry.get(app_id)
        pipeline_path = app_spec.plugin_dir / "pipeline.py"

        if pipeline_path.exists():
            pipeline_cls = self._load_pipeline_class(pipeline_path)
            pipeline_obj = pipeline_cls(self._orchestrator)
            if self._plugin_context is not None:
                setattr(pipeline_obj, "context", self._plugin_context)
            if self.cache_enabled:
                self._pipelines[app_id] = PipelineEntry(app_id=app_id, pipeline=pipeline_obj, pipeline_path=pipeline_path)
            return pipeline_obj

        # fallback：没有 pipeline.py 时使用默认直通 pipeline
        pipeline_obj = _DefaultPassThroughPipeline(self._orchestrator)
        if self._plugin_context is not None:
            setattr(pipeline_obj, "context", self._plugin_context)
        if self.cache_enabled:
            self._pipelines[app_id] = PipelineEntry(app_id=app_id, pipeline=pipeline_obj, pipeline_path=None)
        return pipeline_obj

    # -------------------------
    # Dynamic import
    # -------------------------
    @staticmethod
    def _load_pipeline_class(pipeline_path: Path) -> Type:
        module_name = f"plugin_pipeline_{pipeline_path.parent.name}"
        spec = importlib.util.spec_from_file_location(module_name, str(pipeline_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载 pipeline 模块: {pipeline_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        candidates = [
            "InterviewerPipeline",
            f"{pipeline_path.parent.name.capitalize()}Pipeline",
            "Pipeline",
        ]
        for cls_name in candidates:
            if hasattr(module, cls_name):
                cls = getattr(module, cls_name)
                if isinstance(cls, type):
                    return cls

        for _, v in vars(module).items():
            if isinstance(v, type) and hasattr(v, "run"):
                return v

        raise ImportError(f"pipeline.py 中未找到可用 Pipeline 类: {pipeline_path}")


class _DefaultPassThroughPipeline(BasePipeline):
    def run(self, *, identity, intent: str, user_query: str, intent_params: Dict[str, Any]) -> Dict[str, Any]:
        return self.orchestrator.run(
            wallet_id=identity.wallet_id,
            app_id=identity.app_id,
            session_id=identity.session_id,
            intent=intent,
            user_query=user_query,
            intent_params=intent_params or {},
        )
