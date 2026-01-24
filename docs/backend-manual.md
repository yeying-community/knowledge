# 后端运行手册

本手册面向后端开发与联调，覆盖后端服务结构、核心流程、插件机制、数据流与排障要点。路径均以仓库根目录为准，不依赖项目名。

---

## 1. 服务结构与职责

后端入口：`backend/api/main.py`

- API 层：`backend/api/routers/*`
  - 通用：health、stores、app、kb、ingestion、memory
  - 业务：query、resume、jd
- 核心层：`backend/core/*`
  - 编排：`core/orchestrator/query_orchestrator.py`
  - 记忆：`core/memory/*`
  - KB：`core/kb/*`
  - Prompt：`core/prompt/*`
  - LLM/Embedding：`core/llm/*`、`core/embedding/*`
- 数据源：`backend/datasource/*`
  - SQLite / MinIO / Weaviate
- 插件：`backend/plugins/<app_id>/`

---

## 2. 基础启动与依赖

建议在已安装依赖的 Python 环境中启动后端（如 conda 或 venv）。服务启动后，可访问 `/health` 验证状态。

环境变量读取逻辑：`backend/settings/config.py`  
会自动向上查找 `.env` 并加载。

---

## 3. 身份模型（Identity）

核心身份由三元组构成：

```
wallet_id + app_id + session_id
```

它生成 `memory_key`，用于：

- 记忆隔离（SQLite + Weaviate）
- MinIO 路径构造
- 用户级检索过滤

---

## 4. 核心工作流

### 4.1 应用注册

- `POST /app/register`  
  用于将 app 进入 `active` 状态，供 `/query` 与 `/memory/push` 使用。
- 请求体需包含 `wallet_id`，注册后 app 归属该钱包（租户隔离）。
- 可用 `GET /app/{app_id}/status?wallet_id=...` 查看 app 状态与 KB 统计。
- 超级管理员钱包由 `SUPER_ADMIN_WALLET_ID` 指定，可跨租户查看应用与 KB。

### 4.2 记忆写入

- 业务先把 `session_history.json` 写入 MinIO
- 调用 `POST /memory/push`
  - 写入 SQLite（主记忆元数据）
  - 写入 Weaviate（辅助记忆向量）
  - 达到阈值后生成摘要，写回 MinIO

### 4.3 KB 文档写入

接口：`POST /kb/{app_id}/{kb_key}/documents?wallet_id=...`

在 `user_upload` 类型下建议至少写入：

- `wallet_id`
- `allowed_apps`（当 KB 配置启用时）
- `source_url`
- `resume_id`
- `jd_id`
- `metadata_json`
- `file_type`（建议从文件后缀解析）

补充：文档写入会同步记录到 SQLite `kb_documents` 表，用于后续统计与审计。详情见：

- `docs/backend-kb-metadata.md`
- `docs/backend-kb-ingestion.md`

### 4.4 查询编排

入口：`POST /query`  
流程由 `QueryOrchestrator` 负责，核心步骤：

1) 校验 app 状态 + owner  
2) 解析身份  
3) 读取短期/长期记忆  
4) 根据插件 KB 配置做向量检索  
5) 构造 Prompt 调用 LLM  

### 4.5 简历上传（推荐）

接口：`POST /resume/upload`

说明：
- 默认写入 app 下第一个 `user_upload` KB
- 返回 `resume_id`，供 `/query` 使用

### 4.6 JD 上传（推荐）

接口：`POST /{app_id}/jd/upload`

说明：
- 默认写入 app 下第一个 `user_upload` KB
- 返回 `jd_id`，供 `/query` 使用

### 4.7 摄取作业（Jobs）

用途：
- 将摄取流程拆分为可追踪作业
- 支持先创建作业，再执行

入口：
- `POST /ingestion/jobs`
- `POST /ingestion/jobs/{job_id}/run`

说明文档：
- `docs/backend-ingestion-jobs.md`
- `docs/backend-ingestion-parsers.md`

### 4.8 私有数据库（Private DB）

用途：
- 通过 `session_id` 自动绑定私有库
- 支持将多个会话绑定到同一私有库（用户聚合）

入口：
- `POST /private_dbs`
- `POST /private_dbs/{private_db_id}/bind`
- `GET /private_dbs`（支持 `owner_wallet_id` 过滤，超级管理员可用）
- `GET /private_dbs/{private_db_id}/sessions`（会话绑定列表）
- `DELETE /private_dbs/{private_db_id}/sessions/{session_id}`（解绑会话）

---

## 5. 插件机制

插件目录：`backend/plugins/<app_id>/`

- `config.yaml`：声明 KB、memory、context、权重等
- `intents.yaml`：声明对外意图（exposed）
- `pipeline.py`：业务编排逻辑
- `prompts/`：提示词模板

插件通过 `PluginContext` 读取 MinIO 文件（`resume_url` / `jd_url`）。

---

## 6. 状态判定与健康检查

最小服务判定：

- `/health` 返回 `{"status":"ok"}`
- `/stores/health` 四项均为 `ok` / `configured`
- `/app/list` 显示 app 处于 `active`
- `/kb/list` 返回 KB 配置

---

## 7. 常见排障

### 7.1 Weaviate “already exists” 日志

这是幂等创建的常见提示。重启后端后应减少噪音，不影响功能。

### 7.2 user_upload 查询为空

排查：

- 文档是否写入 `wallet_id`
- `allowed_apps` 是否与当前 `app_id` 一致
- `/kb/{app}/{kb}/documents?wallet_id=xxx&private_db_id=...` 或 `session_id=...` 是否能查到

---

## 8. 时序图

### 8.1 记忆写入

```mermaid
sequenceDiagram
  participant Biz as 业务端
  participant MinIO as MinIO
  participant API as /memory/push
  participant SQLite as SQLite
  participant Weaviate as Weaviate
  participant LLM as LLM

  Biz->>MinIO: 上传 session_history.json
  Biz->>API: POST /memory/push
  API->>MinIO: 读取会话历史
  API->>SQLite: 写入主记忆元数据
  API->>Weaviate: 写入辅助记忆向量
  API->>LLM: 触发摘要（可选）
  API->>MinIO: 写回摘要
  API-->>Biz: 返回写入结果
```

### 8.2 查询编排

```mermaid
sequenceDiagram
  participant Biz as 业务端
  participant API as /query
  participant Memory as MemoryManager
  participant KB as KnowledgeBaseManager
  participant LLM as LLM

  Biz->>API: POST /query
  API->>Memory: 读取 summary + short-term + aux memory
  API->>KB: 读取 KB hits（按插件配置）
  API->>LLM: 组装 prompt 并生成
  API-->>Biz: 返回结果
```
