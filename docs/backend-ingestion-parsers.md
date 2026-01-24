# 文档解析器注册表（Step 2）

本步骤新增解析器注册表，统一处理不同文件类型并产出“可向量化文本”。

---

## 1. 当前支持类型

- `json`：提取 `text/content/resume/jd/segments` 字段，否则回退为 JSON 字符串
- `txt` / `md`：直接作为文本
- `html` / `htm`：剥离 HTML 标签后文本化

未识别类型会回退为纯文本解析（UTF-8 忽略错误字符）。

---

## 2. 解析输出结构

```json
{
  "text": "...",
  "metadata": {"filename": "..."},
  "file_type": "json",
  "content_sha256": "..."
}
```

---

## 3. 扩展方式

1) 在 `parser_registry.py` 中注册新的解析器：
   - `registry.register("pdf", parse_pdf)`
2) 解析器签名：`parse(data: bytes, filename: Optional[str]) -> ParsedDocument`

---

## 4. 关联代码

- 注册表：`backend/core/ingestion/parser_registry.py`
