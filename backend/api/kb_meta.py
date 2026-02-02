# api/kb_meta.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional, Tuple


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def infer_file_type(source_url: Optional[str]) -> Optional[str]:
    if not source_url:
        return None
    clean = source_url.split("?", 1)[0].split("#", 1)[0]
    ext = Path(clean).suffix.lower().lstrip(".")
    return ext or None


def extract_source_info(props: dict) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(props, dict):
        return None, None
    resume_id = props.get("resume_id")
    if resume_id:
        return "resume", str(resume_id)
    jd_id = props.get("jd_id")
    if jd_id:
        return "jd", str(jd_id)
    return None, None


def derive_content_sha256(text: Optional[str], props: Optional[dict], text_field: str) -> Optional[str]:
    if text:
        return sha256_text(str(text))
    if props:
        raw = props.get(text_field)
        if raw:
            return sha256_text(str(raw))
        meta = props.get("metadata_json")
        if meta:
            return sha256_text(str(meta))
    return None
