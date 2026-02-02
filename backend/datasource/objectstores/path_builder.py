# datasource/objectstores/path_builder.py
# -*- coding: utf-8 -*-

from identity.models import Identity


class PathBuilder:
    """
    MinIO 路径生成器
    - business_file: 业务上传的 JSON （RAG 读取）
    - summary: RAG 自动生成摘要文件（primary_memory 写入）
    """

    # -----------------------------
    # 业务上传文件（RAG 读取）
    # -----------------------------
    @staticmethod
    def business_file(identity: Identity, filename: str) -> str:
        """
        业务已上传到 MinIO 的文件路径：
            memory/<wallet>/<app>/<session>/<filename>

        filename 由业务传入，例如：
            history/full_session.json
            outputs/grade.json
        """
        safe = filename.lstrip("/")
        return (
            f"memory/{identity.wallet_id}/"
            f"{identity.app_id}/"
            f"{identity.session_id}/"
            f"{safe}"
        )

    # -----------------------------
    # RAG 自动生成摘要文件
    # -----------------------------
    @staticmethod
    def summary(identity: Identity, version: int) -> str:
        """
        RAG 写入摘要文件：
            memory/<wallet>/<app>/<session>/summary/summary_<version>.json
        """
        return (
            f"memory/{identity.wallet_id}/"
            f"{identity.app_id}/"
            f"{identity.session_id}/summary/"
            f"summary_{version}.json"
        )

    @staticmethod
    def user_resume(wallet_id: str, app_id: str, resume_id: str) -> str:
        """
        用户简历文件路径：
            kb/<wallet>/<app>/resume/<resume_id>.json
        """
        safe_id = str(resume_id).strip().lstrip("/")
        return f"kb/{wallet_id}/{app_id}/resume/{safe_id}.json"

    @staticmethod
    def user_jd(wallet_id: str, app_id: str, jd_id: str) -> str:
        """
        用户 JD 文件路径：
            kb/<wallet>/<app>/jd/<jd_id>.json
        """
        safe_id = str(jd_id).strip().lstrip("/")
        return f"kb/{wallet_id}/{app_id}/jd/{safe_id}.json"

    @staticmethod
    def kb_prefix(wallet_id: str, app_id: str, kb_key: str) -> str:
        """
        KB 基础路径：
            kb/<wallet>/<app>/<kb_key>/
        """
        safe_key = str(kb_key).strip().lstrip("/")
        return f"kb/{wallet_id}/{app_id}/{safe_key}/"

    @staticmethod
    def kb_upload(wallet_id: str, app_id: str, kb_key: str, filename: str) -> str:
        """
        通用 KB 上传文件路径：
            kb/<wallet>/<app>/<kb_key>/uploads/<filename>
        """
        safe_name = str(filename).strip().lstrip("/")
        prefix = PathBuilder.kb_prefix(wallet_id, app_id, kb_key)
        return f"{prefix}uploads/{safe_name}"
