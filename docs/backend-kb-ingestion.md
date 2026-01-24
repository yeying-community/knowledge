# KB 元数据写入流程（Step 2）

本步骤将上传与 CRUD 接口接入 `kb_documents`，并补齐摄取日志的 wallet 维度。

---

## 1. resume / jd 上传写入

写入点：

- `POST /resume/upload`
- `POST /{app_id}/jd/upload`

行为：

- 写 MinIO（JSON 原文）
- 写 Weaviate（向量 + properties）
- 写 SQLite `kb_documents`（doc_id / source_url / file_type / content_sha256）

字段约定：

- `source_type`：`resume` / `jd`
- `source_id`：`resume_id` / `jd_id`
- `file_type`：从 `source_url` 解析，默认 `json`

---

## 2. /kb 文档 CRUD 写入

写入点：

- `POST /kb/{app_id}/{kb_key}/documents`
- `PUT /kb/{app_id}/{kb_key}/documents/{doc_id}`
- `PATCH /kb/{app_id}/{kb_key}/documents/{doc_id}`
- `DELETE /kb/{app_id}/{kb_key}/documents/{doc_id}`

行为：

- create/replace/update 会 upsert `kb_documents`
- delete 将 `kb_documents.status` 标记为 `deleted`

`source_type` 默认：

- 若 props 中携带 `resume_id` / `jd_id`，自动识别
- 其他情况默认为 `manual`（仅在 create/replace 时写入）

---

## 3. ingestion_logs wallet 维度

- `ingestion_logs` 新增 `wallet_id` 列
- list 时非超级管理员会按 wallet 过滤

---

## 4. 关联代码

- helper：`backend/api/kb_meta.py`
- resume 上传：`backend/api/routers/resume.py`
- jd 上传：`backend/api/routers/jd.py`
- kb CRUD：`backend/api/routers/kb.py`
- ingestion 日志：`backend/api/routers/ingestion.py`
