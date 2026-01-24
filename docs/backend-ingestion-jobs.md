# 摄取作业系统（Step 1）

本步骤将摄取流程升级为可追踪作业：创建 → 运行 → 记录结果与错误。

---

## 1. 数据模型

### ingestion_jobs

字段：

- `id`：自增主键
- `wallet_id` / `app_id` / `kb_key`：租户与目标 KB
- `data_wallet_id`：数据归属钱包（业务用户，可选）
- `private_db_id`：私有库 ID（可选）
- `job_type`：当前固定为 `kb_ingest`
- `source_url`：MinIO URL（`minio://bucket/key`）
- `file_type`：文件类型
- `content_sha256`：内容哈希（可选）
- `status`：`pending` / `running` / `success` / `failed`
- `options_json`：参数（如 `max_chars`）
- `result_json`：结果（doc_id、collection 等）
- `error_message`：失败原因
- `created_at` / `updated_at` / `started_at` / `finished_at`

### ingestion_job_runs

字段：

- `id` / `job_id`
- `status` / `message` / `meta_json`
- `created_at`

---

## 2. API

入口：

- `POST /ingestion/jobs` 创建作业（可加 `?run=true` 立即执行）
- `POST /ingestion/jobs/{job_id}/run` 执行作业
- `GET /ingestion/jobs` 查询作业列表
- `GET /ingestion/jobs/{job_id}` 查询单作业
- `GET /ingestion/jobs/{job_id}/runs` 查询作业执行记录
- `GET /ingestion/jobs/presets` 获取 MinIO 前缀与最近文件
- `POST /ingestion/upload` 上传本地文件到 MinIO

说明：
- `source_url` 目前仅支持 `minio://` 地址
- `content` 会先写入 MinIO 再执行
- `data_wallet_id` 仅在 `user_upload` 类型 KB 生效，用于绑定业务用户数据
- `/ingestion/jobs/presets` 可传 `data_wallet_id` 获取该用户前缀文件
- `session_id/private_db_id` 推荐用于 `user_upload` 类型 KB 绑定私有库
- `session_id` 与 `private_db_id` 同时传入时需一致，否则返回 400
- 使用 `session_id/private_db_id` 查询作业列表时必须提供 `app_id`

---

## 3. 执行流程

1) 校验 `wallet_id` + `app_id` 权限  
2) 读取 MinIO 文件  
3) 解析 → 生成文本  
4) 写入 Weaviate  
5) 写入 `kb_documents` 元数据  
6) 写入 `ingestion_logs` + `ingestion_job_runs`

---

## 4. 关联代码

- 建表：`backend/datasource/connections/sqlite_connection.py`
- Store：`backend/datasource/sqlstores/ingestion_job_store.py`
- Runner：`backend/core/ingestion/job_runner.py`
- Router：`backend/api/routers/ingestion_jobs.py`
