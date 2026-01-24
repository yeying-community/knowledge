# core/ingestion/parser_registry.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable, Dict, Optional


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._chunks.append(data)

    def text(self) -> str:
        return " ".join(x.strip() for x in self._chunks if x.strip())


@dataclass
class ParsedDocument:
    text: str
    metadata: dict
    file_type: Optional[str] = None
    content_sha256: Optional[str] = None


ParserFunc = Callable[[bytes, Optional[str]], ParsedDocument]


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def _extract_text_from_json(payload) -> str:
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, dict):
        for key in ("text", "content", "resume", "jd"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        segments = payload.get("segments")
        if isinstance(segments, list):
            return "\n".join(str(x) for x in segments if x)
        return json.dumps(payload, ensure_ascii=False)
    if isinstance(payload, list):
        return "\n".join(str(x) for x in payload if x)
    return str(payload)


def _parse_text(data: bytes, filename: Optional[str]) -> ParsedDocument:
    text = _decode_text(data).strip()
    return ParsedDocument(
        text=text,
        metadata={"filename": filename} if filename else {},
        content_sha256=_sha256_bytes(data),
    )


def _parse_json(data: bytes, filename: Optional[str]) -> ParsedDocument:
    text = _decode_text(data)
    try:
        payload = json.loads(text)
    except Exception:
        payload = text
    extracted = _extract_text_from_json(payload)
    metadata = {"filename": filename} if filename else {}
    return ParsedDocument(
        text=extracted,
        metadata=metadata,
        file_type="json",
        content_sha256=_sha256_bytes(data),
    )


def _parse_html(data: bytes, filename: Optional[str]) -> ParsedDocument:
    raw = _decode_text(data)
    parser = _HTMLTextExtractor()
    try:
        parser.feed(raw)
    except Exception:
        pass
    text = parser.text().strip() or raw.strip()
    metadata = {"filename": filename} if filename else {}
    return ParsedDocument(
        text=text,
        metadata=metadata,
        file_type="html",
        content_sha256=_sha256_bytes(data),
    )


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: Dict[str, ParserFunc] = {}
        self._fallback: ParserFunc = _parse_text

    def register(self, file_type: str, parser: ParserFunc) -> None:
        key = (file_type or "").strip().lower()
        if not key:
            return
        self._parsers[key] = parser

    def parse(self, data: bytes, file_type: Optional[str], filename: Optional[str] = None) -> ParsedDocument:
        key = (file_type or "").strip().lower()
        parser = self._parsers.get(key) or self._fallback
        parsed = parser(data, filename)
        if parsed.file_type is None:
            parsed.file_type = key or parsed.file_type
        return parsed


def default_registry() -> ParserRegistry:
    registry = ParserRegistry()
    registry.register("txt", _parse_text)
    registry.register("text", _parse_text)
    registry.register("md", _parse_text)
    registry.register("markdown", _parse_text)
    registry.register("json", _parse_json)
    registry.register("html", _parse_html)
    registry.register("htm", _parse_html)
    return registry
