# RAG 中台接口文档

基础说明：
- Base URL：由部署环境决定
- 统一返回 JSON
- `app_id` 对应 `plugins/<app_id>` 目录
- 前端控制台（如启用）：`/console/`

---

## Health

GET `/health`

响应示例：
```json
{"status": "ok"}
```

---

## 应用注册

POST `/app/register`

请求体：
```json
{"app_id": "interviewer", "wallet_id": "wallet_xxx"}
```

响应示例：
```json
{"app_id": "interviewer", "status": "ok"}
```

---

## 应用列表

GET `/app/list?wallet_id=wallet_xxx`

响应示例：
```json
[
  {"app_id": "interviewer", "status": "active", "has_plugin": true, "owner_wallet_id": "wallet_xxx"}
]
```

说明：
- `status` 来自 DB（`active/disabled/deleted/unregistered`）
- `has_plugin` 表示插件目录存在
- 仅返回 `owner_wallet_id == wallet_id` 的 app
- 当 `wallet_id == SUPER_ADMIN_WALLET_ID` 时返回所有 app

---

## 应用状态

GET `/app/{app_id}/status?wallet_id=wallet_xxx`

响应示例：
```json
{
  "app_id": "interviewer",
  "status": "active",
  "owner_wallet_id": "wallet_xxx",
  "has_plugin": true,
  "kb_stats": [
    {
      "kb_key": "jd_kb",
      "collection": "kb_interviewer_jd",
      "total_count": 1280,
      "chunk_count": 1280
    }
  ],
  "last_ingestion": {
    "id": 1,
    "status": "success",
    "message": "jd rebuild finished",
    "app_id": "interviewer",
    "kb_key": "jd_kb",
    "collection": "kb_interviewer_jd",
    "meta_json": "{\"total\": 100}",
    "created_at": "2024-09-04 10:11:12"
  }
}
```

说明：
- `kb_stats` 会按 `wallet_id` 过滤 user_upload 数据
- `last_ingestion` 为空表示暂无记录
- `wallet_id` 必填，需为 app owner 或 SUPER_ADMIN_WALLET_ID

---

## Intent 列表

GET `/app/{app_id}/intents`

响应示例：
```json
{
  "app_id": "interviewer",
  "intents": ["basic_questions", "generate_questions", "project_questions", "scenario_questions"],
  "exposed_intents": ["generate_questions"]
}
```

---

## Knowledge Base 列表

GET `/kb/list?wallet_id=wallet_xxx`

响应示例：
```json
[
  {
    "app_id": "interviewer",
    "kb_key": "jd_kb",
    "kb_type": "static_kb",
    "collection": "kb_interviewer_jd",
    "text_field": "content",
    "top_k": 3,
    "weight": 0.4,
    "use_allowed_apps_filter": false,
    "status": "active"
  }
]
```
说明：
- `wallet_id` 必填，仅返回该租户拥有的 app 对应 KB
- 当 `wallet_id == SUPER_ADMIN_WALLET_ID` 时返回所有 app 的 KB

---

## Knowledge Base 统计

GET `/kb/{app_id}/{kb_key}/stats?wallet_id=wallet_xxx&private_db_id=private_db_xxx&session_id=session_001`

响应示例：
```json
{
  "app_id": "interviewer",
  "kb_key": "jd_kb",
  "collection": "kb_interviewer_jd",
  "total_count": 1280,
  "chunk_count": 1280
}
```
说明：
- `wallet_id` 必填，用于权限校验
- `private_db_id` 可选，仅用于 `user_upload` KB 的私有库过滤
- `session_id` 可选（仅 `user_upload`），会解析为私有库过滤
- `session_id` 与 `private_db_id` 同时传入时需一致，否则返回 400
- 当 KB 类型为 `user_upload` 且开启 `use_allowed_apps_filter` 时，会按 `app_id` 过滤

---

## Knowledge Base 文档列表

GET `/kb/{app_id}/{kb_key}/documents?limit=20&offset=0&wallet_id=wallet_xxx&private_db_id=private_db_xxx&session_id=session_001`

响应示例：
```json
{
  "items": [
    {
      "id": "uuid",
      "properties": {"content": "..."},
      "created_at": "2024-09-04T10:11:12Z",
      "updated_at": "2024-09-04T11:11:12Z"
    }
  ],
  "total": 1280
}
```
说明：
- 当 KB 类型为 `user_upload` 且开启 `use_allowed_apps_filter` 时，会按 `app_id` 过滤
- `wallet_id` 必填，用于权限校验
- `private_db_id` 可选，仅 `user_upload` 用于私有库过滤
- `session_id` 可选（仅 `user_upload`），会解析为私有库过滤
- `session_id` 与 `private_db_id` 同时传入时需一致，否则返回 400

---

## Knowledge Base 新增文档

POST `/kb/{app_id}/{kb_key}/documents?wallet_id=wallet_xxx`

请求体：
```json
{
  "id": "optional-uuid",
  "text": "optional text for embedding",
  "properties": {"content": "..."},
  "vector": null
}
```

响应示例：
```json
{
  "id": "uuid",
  "properties": {"content": "..."},
  "created_at": "2024-09-04T10:11:12Z",
  "updated_at": "2024-09-04T10:11:12Z"
}
```
说明：
- `user_upload` 建议在 `properties` 中携带 `source_url` / `file_type`

---

## Knowledge Base 替换文档

PUT `/kb/{app_id}/{kb_key}/documents/{doc_id}?wallet_id=wallet_xxx`

请求体同新增文档。

---

## Knowledge Base 更新文档

PATCH `/kb/{app_id}/{kb_key}/documents/{doc_id}?wallet_id=wallet_xxx`

请求体：
```json
{
  "text": "optional text for embedding",
  "properties": {"content": "..."},
  "vector": null
}
```

---

## Knowledge Base 删除文档

DELETE `/kb/{app_id}/{kb_key}/documents/{doc_id}?wallet_id=wallet_xxx`

响应示例：
```json
{"status": "ok"}
```

---

## Store Health

GET `/stores/health`

响应示例：
```json
{
  "stores": [
    {"name": "sqlite", "status": "ok", "details": "SELECT 1 ok"},
    {"name": "minio", "status": "ok", "details": "list_buckets ok"},
    {"name": "weaviate", "status": "ok", "details": "client.is_ready ok"},
    {"name": "llm", "status": "configured", "details": "openai configured"}
  ]
}
```
说明：
- `wallet_id` 必填，用于租户隔离
- `app_id` 必填
说明：
- `wallet_id` 必填，用于租户隔离
- `app_id` 必填

---

## Ingestion Logs

GET `/ingestion/logs?wallet_id=wallet_xxx&limit=50&offset=0&app_id=interviewer&kb_key=jd_kb&status=success`

响应示例：
```json
{
  "items": [
    {
      "id": 1,
      "status": "success",
      "message": "jd rebuild finished",
      "wallet_id": "wallet_xxx",
      "app_id": "interviewer",
      "kb_key": "jd_kb",
      "collection": "kb_interviewer_jd",
      "meta_json": "{\"total\": 100}",
      "created_at": "2024-09-04 10:11:12"
    }
  ]
}
```

POST `/ingestion/logs`

请求体：
```json
{
  "wallet_id": "wallet_xxx",
  "status": "started",
  "message": "ingestion started",
  "app_id": "interviewer",
  "kb_key": "jd_kb",
  "collection": "kb_interviewer_jd",
  "meta": {"bucket": "company-jd"}
}
```
说明：
- `wallet_id` / `app_id` 必填

---

## Ingestion Jobs

POST `/ingestion/jobs`

请求体：
```json
{
  "wallet_id": "wallet_xxx",
  "data_wallet_id": "user_123",
  "session_id": "session_001",
  "private_db_id": "private_db_xxx",
  "app_id": "interviewer",
  "kb_key": "user_profile_kb",
  "source_url": "minio://bucket/kb/wallet_xxx/interviewer/uploads/demo.json",
  "file_type": "json",
  "metadata": {"source": "upload"},
  "options": {"max_chars": 8000}
}
```
或使用 `content`：
```json
{
  "wallet_id": "wallet_xxx",
  "data_wallet_id": "user_123",
  "app_id": "interviewer",
  "kb_key": "user_profile_kb",
  "content": "raw text content",
  "filename": "note.txt"
}
```

响应示例：
```json
{
  "id": 1,
  "wallet_id": "wallet_xxx",
  "data_wallet_id": "user_123",
  "private_db_id": "private_db_xxx",
  "app_id": "interviewer",
  "kb_key": "user_profile_kb",
  "job_type": "kb_ingest",
  "source_url": "minio://bucket/kb/wallet_xxx/interviewer/uploads/demo.json",
  "file_type": "json",
  "status": "pending"
}
```

POST `/ingestion/jobs/{job_id}/run?wallet_id=wallet_xxx`

也可以在创建时加 `?run=true` 立即执行。

GET `/ingestion/jobs?wallet_id=wallet_xxx&app_id=interviewer&status=success&session_id=session_001`

GET `/ingestion/jobs/{job_id}?wallet_id=wallet_xxx`

GET `/ingestion/jobs/{job_id}/runs?wallet_id=wallet_xxx`

说明：
- `wallet_id` 必填，用于权限校验
- 目前仅支持 MinIO URL
- `data_wallet_id` 仅在 `user_upload` 类型 KB 生效（业务用户数据归属）
- `session_id` 可用于过滤作业（需要 `app_id`），会解析为私有库
- `session_id` 与 `private_db_id` 同时传入时需一致，否则返回 400

---

GET `/ingestion/jobs/presets?wallet_id=wallet_xxx&data_wallet_id=user_123&app_id=interviewer&kb_key=user_profile_kb`

响应示例：
```json
{
  "bucket": "rag-data",
  "prefix": "kb/user_123/interviewer/user_profile_kb/",
  "recent_keys": [
    "kb/user_123/interviewer/user_profile_kb/uploads/demo.json"
  ]
}
```

说明：
- 返回推荐的 MinIO 前缀与最近文件

---

## Ingestion 文件上传

POST `/ingestion/upload`（`multipart/form-data`）

表单字段：
- `wallet_id` / `app_id` / `kb_key` 必填
- `data_wallet_id` 可选（user_upload 用于路径隔离）
- `filename` 可选
- `file` 必填

响应示例：
```json
{
  "bucket": "rag-data",
  "key": "kb/wallet_xxx/interviewer/user_profile_kb/uploads/demo.json",
  "source_url": "minio://rag-data/kb/wallet_xxx/interviewer/user_profile_kb/uploads/demo.json",
  "file_type": "json",
  "size_bytes": 2048,
  "content_sha256": "..."
}
```

---

## 私有数据库管理

POST `/private_dbs`

请求体：
```json
{
  "wallet_id": "wallet_xxx",
  "app_id": "interviewer"
}
```

响应示例：
```json
{
  "private_db_id": "e3c6b11d-2c91-4b55-93b3-1b3cd1b4c1d9",
  "app_id": "interviewer",
  "owner_wallet_id": "wallet_xxx",
  "status": "active"
}
```

POST `/private_dbs/{private_db_id}/bind`

请求体：
```json
{
  "wallet_id": "wallet_xxx",
  "app_id": "interviewer",
  "session_ids": ["session_001", "session_002"]
}
```

说明：
- 用于把多个 session 聚合到同一个私有库

GET `/private_dbs?wallet_id=wallet_xxx&app_id=interviewer`

可选参数：
- `owner_wallet_id`（仅超级管理员可用，用于按租户过滤）
- `app_id` 省略时返回该钱包下全部私有库
- `session_id` 可选，按会话绑定过滤私有库（需配合 `app_id`）

GET `/private_dbs/{private_db_id}/sessions?wallet_id=wallet_xxx&app_id=interviewer`

响应示例：
```json
{
  "private_db_id": "private_db_xxx",
  "app_id": "interviewer",
  "owner_wallet_id": "wallet_xxx",
  "sessions": [
    {"session_id": "session_001", "created_at": "2024-09-04T10:11:12Z"}
  ]
}
```

DELETE `/private_dbs/{private_db_id}/sessions/{session_id}?wallet_id=wallet_xxx&app_id=interviewer`

响应示例：
```json
{
  "private_db_id": "private_db_xxx",
  "session_id": "session_001",
  "removed_count": 1
}
```

---

## 简历上传

POST `/resume/upload`

请求体：
```json
{
  "wallet_id": "wallet_xxx",
  "app_id": "interviewer",
  "session_id": "session_001",
  "private_db_id": "optional-private-db",
  "resume_id": "optional-resume-id",
  "kb_key": "optional-user-upload-kb",
  "metadata": {"source": "biz"},
  "resume": {
    "name": "Alex Chen",
    "skills": ["python", "golang"],
    "text": "Backend engineer with 5 years of experience."
  }
}
```

响应示例：
```json
{
  "resume_id": "a8a3c9c0-2fd5-4d32-9c95-0f7c4c8763f4",
  "kb_key": "user_profile_kb",
  "collection": "kb_user_profile",
  "doc_id": "b367956c-41b6-444c-881c-ef8bd62bcc98",
  "source_url": "minio://bucket/kb/user_123/interviewer/resume/a8a3c9c0-2fd5-4d32-9c95-0f7c4c8763f4.json"
}
```

说明：
- 默认写入 app 下第一个 `user_upload` 类型 KB
- `resume_id` 用于后续 `/query` 调用
- `session_id` 用于绑定私有库（建议必填）
- 也可直接传 `private_db_id` 绑定指定私有库
- `session_id` 与 `private_db_id` 同时传入时需一致

---

## JD 上传

POST `/{app_id}/jd/upload`

请求体：
```json
{
  "wallet_id": "wallet_xxx",
  "app_id": "interviewer",
  "session_id": "session_001",
  "private_db_id": "optional-private-db",
  "jd_id": "optional-jd-id",
  "kb_key": "optional-user-upload-kb",
  "metadata": {"source": "biz"},
  "jd": {
    "title": "Backend Engineer",
    "requirements": ["Python", "Distributed Systems"],
    "text": "We are looking for a Backend Engineer..."
  }
}
```

响应示例：
```json
{
  "jd_id": "7a4f0b4e-9d9f-4b9f-9b25-8f7b5a92a8a1",
  "kb_key": "user_profile_kb",
  "collection": "kb_user_profile",
  "doc_id": "d2b5d3e4-1c1b-4d3f-8b5d-9e1f2a3b4c5d",
  "source_url": "minio://bucket/kb/user_123/interviewer/jd/7a4f0b4e-9d9f-4b9f-9b25-8f7b5a92a8a1.json"
}
```

说明：
- 默认写入 app 下第一个 `user_upload` 类型 KB
- `jd_id` 用于后续 `/query` 调用
- 路径中的 `app_id` 为必填，Body 的 `app_id` 可选
- 也可直接传 `private_db_id` 绑定指定私有库
- `session_id` 与 `private_db_id` 同时传入时需一致

---

## 查询入口

POST `/query`

请求体：
```json
{
  "wallet_id": "user_123",
  "app_id": "interviewer",
  "session_id": "session_001",
  "intent": "generate_questions",
  "query": "我是后端工程师，准备面试，请给我一些问题。",
  "resume_id": "optional-resume-id",
  "jd_id": "optional-jd-id",
  "target": "后端工程师",
  "company": "示例公司",
  "intent_params": {
    "basic_count": 2,
    "project_count": 1,
    "scenario_count": 1,
    "target_position": "后端工程师",
    "company": "示例公司"
  }
}
```

响应示例（interviewer）：
```json
{
  "answer": {
    "questions": ["..."],
    "meta": {"basic_count": 2, "project_count": 1, "scenario_count": 1}
  }
}
```

说明：
- `intent_params` 为插件自定义参数
- 若不提供 `query`，则插件可根据 `resume/jd` 补全
- `wallet_id` 必须是该 `app_id` 的 owner
- `resume_id` 为 `/resume/upload` 返回的简历 ID
- `jd_id` 为 `/{app_id}/jd/upload` 返回的 JD ID
- `target/company` 为快捷参数，内部会映射到 `intent_params.target_position/company`
- 当 `resume_id` 不存在时，会走默认路径生成通用问题（不报错）
- 当 `jd_id` 存在且可读取时，将跳过 JD 静态库检索
- 当 `jd_id` 缺失或无效时，仍走默认 JD 检索通路

场景说明：
- 只有简历：传 `resume_id` 或 `intent_params.resume_text`，可省略 `query`
- 简历 + JD：传 `resume_id + jd_id`（推荐）或直接传 `intent_params.resume_text/jd_text`
- 简历/JD 都没有：必须传 `query`（否则 400）

---

## 记忆写入

POST `/memory/push`

请求体：
```json
{
  "wallet_id": "user_123",
  "app_id": "interviewer",
  "session_id": "session_001",
  "filename": "history/session_history.json",
  "description": "可选说明",
  "summary_threshold": 20
}
```

响应示例：
```json
{
  "status": "ok",
  "messages_written": 2,
  "metas": [
    {
      "uid": "uuid",
      "memory_key": "sha256",
      "role": "user",
      "url": "memory/user_123/interviewer/session_001/history/session_history.json",
      "description": "history/session_history.json",
      "content_sha256": "..."
    }
  ]
}
```

说明：
- `filename` 对应 MinIO 路径：`memory/<wallet>/<app>/<session>/<filename>`
- 文件内容示例：
  ```json
  {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
  ```
- `summary_threshold` 可覆盖插件配置中的 `memory.summary_threshold`
