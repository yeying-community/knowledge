# SDD-04A 摄取解析器

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：后端研发、数据接入

---

## 1. 解析器职责

将原始文件转换为可向量化的纯文本与元数据。

入口：`backend/core/ingestion/parser_registry.py`

---

## 2. 内置支持类型

- `txt` / `text`
- `md` / `markdown`
- `json`
- `html` / `htm`

不支持的类型会回退到文本解析。

---

## 3. 扩展方式

1) 在 `parser_registry.py` 注册新解析器  
2) 实现 `ParsedDocument` 返回值（text / metadata / file_type）  
3) 在摄取作业中使用对应 `file_type`

