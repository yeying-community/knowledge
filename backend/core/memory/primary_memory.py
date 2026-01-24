# core/memory/primary_memory.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from typing import Optional, List

from identity.models import Identity
from datasource.base import Datasource
from core.llm.llm_client import LLMClient
from datasource.objectstores.path_builder import PathBuilder


class PrimaryMemory:
    """
    主记忆：
    - 负责摘要（summary）的生成、读取、更新
    - 只保留“当前生效”的摘要（latest summary_url）
    """

    def __init__(self, ds: Datasource):
        self.ds = ds

    # ------------------------------------------------------------------
    # 读取摘要文本（统一走 ds.minio_bucket）
    # ------------------------------------------------------------------
    def get_summary_text(self, summary_url: str) -> Optional[str]:
        if not summary_url or not self.ds.minio:
            return None
        return self.ds.minio.get_text(
            bucket=self.ds.bucket,
            key=summary_url,
        )

    # ------------------------------------------------------------------
    # 获取当前有效摘要（主记忆表里只认最新 summary_url）
    # ------------------------------------------------------------------
    def get_summary(self, identity: Identity) -> Optional[str]:
        row = self.ds.memory_primary.get(identity.memory_key)
        if not row:
            return None
        return self.get_summary_text(row.get("summary_url"))

    # ------------------------------------------------------------------
    # 记录一条 message 元信息（不写内容，只写 URL & meta）
    # ------------------------------------------------------------------
    def record_message(
        self,
        identity: Identity,
        uid: str,
        role: str,
        url: str,
        content_sha256: str,
        description: str,
    ) -> dict:
        """
        注意：
        - message 内容已经由业务写入 MinIO
        - 这里仅记录元信息
        """
        self.ds.memory_contexts.upsert(
            uid=uid,
            memory_key=identity.memory_key,
            wallet_id=identity.wallet_id,
            app_id=identity.app_id,
            role=role,
            url=url,
            description=description,
            content_sha256=content_sha256,
            qa_count=1,
        )

        # 确保主记忆行存在
        self.ds.memory_primary.ensure_row(
            memory_key=identity.memory_key,
            wallet_id=identity.wallet_id,
            app_id=identity.app_id,
        )

        return {
            "uid": uid,
            "memory_key": identity.memory_key,
            "role": role,
            "url": url,
            "description": description,
            "content_sha256": content_sha256,
        }

    # ------------------------------------------------------------------
    # 触发摘要：当“未摘要 QA 数”达到阈值
    # ------------------------------------------------------------------
    def maybe_summarize(self, identity: Identity, llm: LLMClient) -> None:
        """
        规则：
        - threshold：summary_threshold（从主记忆表或插件配置获得）
        - 新摘要 = 上一次摘要 + 本次未摘要内容
        - 生成后：
            * 写入 MinIO
            * 更新 memory_primary.summary_url / summary_version
            * 标记 contexts 为 summarized
        """
        row = self.ds.memory_primary.get(identity.memory_key) or {}
        threshold = int(row.get("summary_threshold") or 0)
        if threshold <= 0:
            return

        unsummarized = self._list_all_unsummarized(identity.memory_key)
        if not unsummarized:
            return

        total_qa = sum(int(x.get("qa_count") or 0) for x in unsummarized)
        if total_qa < threshold:
            return

        old_summary = self.get_summary(identity) or ""

        # 读取未摘要内容
        parts: List[str] = []
        json_cache: dict = {}

        if not self.ds.minio:
            raise RuntimeError("MinIO is not enabled")

        bucket = self.ds.bucket

        for item in unsummarized:
            key = item["url"]
            if key not in json_cache:
                json_cache[key] = self.ds.minio.get_text(bucket=bucket, key=key) or ""
            raw = json_cache[key]
            if not raw:
                continue

            try:
                data = json.loads(raw)
                for msg in data.get("messages", []):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if content:
                        parts.append(f"{role}: {content}")
            except Exception:
                parts.append(raw)

        if not parts:
            return

        # 构造 LLM 输入
        input_text = ""
        if old_summary.strip():
            input_text += f"【上一次摘要】\n{old_summary.strip()}\n\n"
        input_text += "【新增对话】\n" + "\n".join(parts)

        prompt = (
            "请将下面内容总结为一段可用于后续对话的摘要，要求：\n"
            "1) 保留关键事实、约束、用户偏好、已达成结论。\n"
            "2) 删除冗余细节。\n"
            "3) 输出中文，长度控制在 300-800 字。\n\n"
            f"{input_text}"
        )
        messages = [
            {
                "role": "system",
                "content": "你是一个对话摘要器，请将以下内容压缩为高质量摘要。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        summary_text = llm.chat(
            messages,
            app_id=identity.app_id,
            intent="memory_summary",
        )

        # 生成新版本号
        prev_version = int(row.get("summary_version") or 0)
        new_version = prev_version + 1

        summary_key = PathBuilder.summary(identity, new_version)

        # 写入 MinIO
        self.ds.minio.put_text(
            bucket=bucket,
            key=summary_key,
            text=summary_text,
        )

        # 更新主记忆表（只保留最新）
        self.ds.memory_primary.update_summary(
            memory_key=identity.memory_key,
            summary_url=summary_key,
            summary_version=new_version,
        )

        # 标记 contexts 已摘要
        self.ds.memory_contexts.mark_summarized_by_memory(identity.memory_key)

    # ------------------------------------------------------------------
    # 工具：拉取全部未摘要 contexts（处理分页）
    # ------------------------------------------------------------------
    def _list_all_unsummarized(self, memory_key: str, page_size: int = 200) -> List[dict]:
        out: List[dict] = []
        offset = 0
        while True:
            page = self.ds.memory_contexts.list_by_memory(
                memory_key=memory_key,
                is_summarized=0,
                limit=page_size,
                offset=offset,
            )
            if not page:
                break
            out.extend(page)
            offset += len(page)
            if len(page) < page_size:
                break
        return out
