# SDD-11 API 参考

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：后端研发、业务接入、运维

> **API 文档源**：以仓库根目录 `openapi.yaml` 为准（OpenAPI 3.0.3）。本文件仅做概览说明。

---

## 1. 基础约定

- Base URL：由部署环境决定
- 所有接口返回 JSON
- 控制台静态资源：`/console`
- 认证：除 `/health` 与 `/api/v1/public/auth/*` 外，默认要求 `Authorization: Bearer <token>`

### 1.1 兼容 `wallet_id`

为了兼容旧调用：

- 大多数接口仍接受 `wallet_id`（query/body）
- 当 Authorization 存在时，`wallet_id` 必须与 token 地址一致
- 仅开发调试可开启 `AUTH_ALLOW_INSECURE_WALLET_ID=true`

---

## 2. Auth（SIWE/JWT + UCAN）

### 2.1 SIWE 登录

- `POST /api/v1/public/auth/challenge`  
- `POST /api/v1/public/auth/verify`  
- `POST /api/v1/public/auth/refresh`  
- `POST /api/v1/public/auth/logout`

### 2.2 认证探针

- `GET /api/v1/public/profile`

---

## 3. Health & Stores

- `GET /health`  
- `GET /stores/health`

---

## 4. 应用与插件

### 4.1 应用注册

- `POST /app/register`
- `GET /app/list`
- `GET /app/{app_id}/status`

### 4.2 Intent / Workflow

- `GET /app/{app_id}/intents`
- `GET /app/{app_id}/intents/detail`
- `PUT /app/{app_id}/intents`

- `GET /app/{app_id}/workflows`
- `PUT /app/{app_id}/workflows`

**规则**：当 workflow 名称与对外 intent 名称一致时，默认 pipeline 会顺序执行 workflow intents。

### 4.3 插件文件管理

- `GET /app/{app_id}/plugin/files`
- `GET /app/{app_id}/plugin/file?path=...`
- `PUT /app/{app_id}/plugin/file`

允许路径：

- `config.yaml` / `intents.yaml` / `workflows.yaml` / `pipeline.py`
- `prompts/*.md`

---

## 5. 知识库配置

### 5.1 KB 列表与统计

- `GET /kb/list`
- `GET /kb/{app_id}/{kb_key}/stats`

### 5.2 KB 配置增删改

- `POST /kb/{app_id}/configs`
- `PATCH /kb/{app_id}/{kb_key}/config`
- `DELETE /kb/{app_id}/{kb_key}/config`

支持字段（节选）：

- `kb_key` / `collection` / `text_field`
- `type`（`public_kb` / `user_upload`）
- `schema` / `vector_fields`
- `use_allowed_apps_filter`

---

## 6. 知识库文档

- `GET /kb/{app_id}/{kb_key}/documents`
- `POST /kb/{app_id}/{kb_key}/documents`
- `PUT /kb/{app_id}/{kb_key}/documents/{doc_id}`
- `PATCH /kb/{app_id}/{kb_key}/documents/{doc_id}`
- `DELETE /kb/{app_id}/{kb_key}/documents/{doc_id}`

**user_upload** 推荐字段：`wallet_id` / `private_db_id` / `allowed_apps` / `source_url`

---

## 7. 摄取与作业

### 7.1 摄取日志

- `GET /ingestion/logs`

### 7.2 摄取作业

- `POST /ingestion/jobs`
- `GET /ingestion/jobs`
- `GET /ingestion/jobs/{job_id}`
- `POST /ingestion/jobs/{job_id}/run`
- `GET /ingestion/jobs/{job_id}/runs`
- `GET /ingestion/jobs/presets`

---

## 8. 记忆服务

- `POST /memory/push`
- `POST /memory/upload`
- `GET /memory/sessions`
- `DELETE /memory/sessions`
- `DELETE /memory/sessions/{memory_key}`
- `GET /memory/{memory_key}/contexts`
- `PATCH /memory/contexts/{uid}`

---

## 9. 私有数据库（Private DB）

- `POST /private_dbs`
- `GET /private_dbs`
- `GET /private_dbs/{private_db_id}`
- `POST /private_dbs/{private_db_id}/bind`
- `GET /private_dbs/{private_db_id}/sessions`
- `DELETE /private_dbs/{private_db_id}/sessions/{session_id}`

---

## 10. 审计日志

- `GET /audit/logs`

可筛选：`app_id` / `entity_type` / `action` / `operator_wallet_id`

---

## 11. 查询与业务接口

- `POST /query`
- `POST /resume/upload`
- `POST /{app_id}/jd/upload`
