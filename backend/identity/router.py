# rag/identity/router.py
# -*- coding: utf-8 -*-

from __future__ import annotations


class AccessRouter:
    """
    目前只是骨架，将来 KB 层会调用它。
    未来用于：
    - 多业务之间的访问权限判断
    - 不同 app 访问用户私有知识库的 allowed_apps 检查
    - 企业版中可能加入 RBAC / ABAC 策略
    """

    def can_access_kb(self, app_id: str, kb_meta: dict) -> bool:
        """
        默认规则：如果用户私有 KB 的 allowed_apps 包含 app_id → 准许访问
        """
        allowed_apps = kb_meta.get("allowed_apps", [])
        return app_id in allowed_apps
