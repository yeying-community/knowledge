# KB 元数据表说明（Step 1）

本步骤新增 SQLite 表，用于记录 KB 文档元数据（与向量库解耦），并补充摄取日志的 wallet 维度。

---

## 1. 新表：kb_documents

用途：记录每个向量文档的来源、类型与归属，用于后续统计、审计与可视化。

字段：

- `doc_id`：向量库对象 ID（主键）
- `app_id`：所属应用
- `kb_key`：KB key
- `wallet_id`：归属钱包（user_upload 场景）
- `source_url`：来源地址（MinIO URL）
- `source_type`：来源类型（resume/jd/manual 等）
- `source_id`：来源业务 ID（如 resume_id/jd_id）
- `file_type`：文件类型（如 json/pdf/txt）
- `content_sha256`：内容哈希（用于去重/审计）
- `status`：状态（active/deleted）
- `created_at` / `updated_at`：时间戳

索引：

- `idx_kb_documents_app_kb`：按 app + kb_key 查询
- `idx_kb_documents_wallet`：按 wallet 查询
- `idx_kb_documents_status`：按状态查询

---

## 2. ingestion_logs 增补字段

新增 `wallet_id` 字段与索引 `idx_ingestion_logs_wallet`，用于区分多租户日志。

---

## 3. 统计策略（后续扩展）

- 当前 `/kb/{app_id}/{kb_key}/stats` 仍以向量库统计为准
- `kb_documents` 提供离线/弱一致统计基底，可在后续引入：
  - 向量库不可用时的 fallback
  - 按文件类型/来源的统计切片

---

## 4. 关联代码

- 建表与索引：`backend/datasource/connections/sqlite_connection.py`
- Store 封装：`backend/datasource/sqlstores/kb_document_store.py`
- Datasource 聚合：`backend/datasource/base.py`
