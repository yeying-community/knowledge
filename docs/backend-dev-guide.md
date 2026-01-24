# 后端开发指南

本指南面向后端开发者，强调代码结构、核心流程、扩展方式与常见开发任务。路径均以仓库根目录为准。

---

## 1. 快速启动

后端使用 FastAPI（依赖在 `backend/requirements.txt` 中）。常见启动方式：

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

启动后用 `/health` 验证服务状态。

---

## 2. 配置与环境变量

配置加载逻辑：`backend/settings/config.py`  
会向上查找 `.env` 并加载。常用变量：

- `MINIO_*`：MinIO 连接与 bucket
- `WEAVIATE_*`：Weaviate 向量库连接
- `OPENAI_*` / `EMBED_*`：LLM 与向量化模型
- `SQLITE_PATH`：SQLite 文件路径
- `PLUGINS_AUTO_REGISTER`：自动注册插件列表
- `SUPER_ADMIN_WALLET_ID`：超级管理员钱包 ID（用于跨租户管理）

---

## 3. 目录与模块职责

### 3.1 API 层

位置：`backend/api/`

- `api/main.py`：FastAPI 应用入口
- `api/deps.py`：依赖注入与对象生命周期
- `api/routers/*`：路由实现（health, app, kb, stores, ingestion, memory, query, resume, jd）
- `api/schemas/*`：请求/响应模型

### 3.2 核心层（中台能力）

位置：`backend/core/`

- 编排：`core/orchestrator/query_orchestrator.py`
- 记忆：`core/memory/*`
- KB：`core/kb/*`
- Prompt：`core/prompt/*`
- LLM/Embedding：`core/llm/*`、`core/embedding/*`

### 3.3 数据源

位置：`backend/datasource/`

- `connections/*`：各类连接适配
- `objectstores/*`：MinIO 读写与路径约定
- `vectorstores/*`：Weaviate 封装
- `sqlstores/*`：SQLite 表访问（app_registry、memory_*、ingestion_logs 等）

### 3.4 插件

位置：`backend/plugins/<app_id>/`

插件由配置驱动，核心文件：

- `config.yaml`
- `intents.yaml`
- `pipeline.py`
- `prompts/*`

---

## 4. 核心请求流程

### 4.1 `/query`

入口：`backend/api/routers/query.py`  
流程：

1) 校验 app 状态（必须 active）  
2) 解析 Identity  
3) 读取记忆（summary / short-term / aux memory）  
4) KB 检索（按插件配置）  
5) 组装 prompt → LLM  

### 4.2 `/memory/push`

入口：`backend/api/routers/memory.py`  
流程：

- 业务写入 MinIO 的历史会话由 RAG 读取  
- 写入 SQLite 主记忆元信息  
- 写入 Weaviate 辅助记忆  
- 达到阈值时生成摘要写回 MinIO  

### 4.3 `/resume/upload` 与 `/{app_id}/jd/upload`

- `/resume/upload`：上传简历 JSON，返回 `resume_id`
- `/{app_id}/jd/upload`：上传 JD JSON，返回 `jd_id`（路径需包含 app_id）

---

## 5. 关键数据约定

### 5.1 Identity 与 memory_key

身份三元组：

```
wallet_id + app_id + session_id
```

用于：

- 记忆隔离
- MinIO 路径生成
- KB user_upload 过滤

### 5.2 MinIO 路径规范

- 业务文件：`memory/<wallet>/<app>/<session>/<filename>`
- 简历文件：`kb/<wallet>/<app>/resume/<resume_id>.json`
- JD 文件：`kb/<wallet>/<app>/jd/<jd_id>.json`
- 摘要文件：`memory/<wallet>/<app>/<session>/summary/summary_<version>.json`

说明：
- `memory/` 用于会话历史与摘要
- `kb/` 用于用户私有 KB（简历 / JD）

### 5.3 user_upload KB 推荐字段

建议在文档 properties 中包含：

- `wallet_id`
- `allowed_apps`（启用过滤时）
- `resume_id` / `jd_id`
- `source_url`
- `metadata_json`

---

## 6. SQLite 数据表结构

DDL 定义位置：`backend/datasource/connections/sqlite_connection.py`

### 6.1 identity_session

- `memory_key` (PK)：由 `wallet_id + app_id + session_id` 生成
- `wallet_id` / `app_id` / `session_id`
- `created_at` / `updated_at`

用途：身份解析与 memory_key 缓存。

### 6.2 memory_metadata

- `memory_key` (PK)
- `wallet_id` / `app_id` / `session_id`
- `params_json`：会话参数或扩展字段
- `status`：`active/disabled`
- `created_at` / `updated_at`

用途：会话级元数据管理。

### 6.3 memory_primary

- `memory_key` (PK)
- `wallet_id` / `app_id`
- `summary_url` / `summary_version`
- `summary_threshold`
- `recent_qa_count` / `total_qa_count`
- `last_summary_index` / `last_summary_at`
- `created_at` / `updated_at`

用途：记忆摘要与统计。

### 6.4 memory_contexts

- `uid` (PK)
- `memory_key` / `wallet_id` / `app_id`
- `role` / `url` / `description`
- `content_sha256`（去重）
- `qa_count`
- `is_summarized` / `summarized_at`
- `created_at` / `updated_at`

用途：短期对话与辅助记忆的索引元信息。

### 6.5 app_registry

- `app_id` (PK)
- `owner_wallet_id`：租户/开发者钱包 ID（app 归属）
- `status`：`active/disabled/deleted`
- `created_at` / `updated_at`

用途：应用注册状态 + 多租户归属。

### 6.6 ingestion_logs

- `id` (PK, auto increment)
- `app_id` / `kb_key` / `collection`
- `status` / `message`
- `meta_json`
- `created_at`

用途：摄取任务记录。

---

## 7. 插件开发流程

### 6.1 新建插件目录

```
backend/plugins/<app_id>/
  config.yaml
  intents.yaml
  pipeline.py
  prompts/
```

### 6.2 配置 KB 与记忆策略

在 `config.yaml` 中声明：

- `memory.enabled` / `memory.summary_threshold`
- `knowledge_bases`（type/collection/text_field/top_k/weight/use_allowed_apps_filter）
- `prompt.kb_aliases`（如 `resume_text`、`jd_text`）

### 6.3 Pipeline 处理

`pipeline.py` 负责业务逻辑，可通过 `PluginContext` 读取 MinIO 文件。  
注册应用后即可通过 `/query` 调用。

---

## 8. 插件开发模板（最小可运行）

目录结构：

```
backend/plugins/sample_app/
  config.yaml
  intents.yaml
  pipeline.py
  prompts/
    system.md
    generate.md
```

### 8.1 config.yaml

```yaml
app_id: sample_app
display_name: 示例插件
enabled: true

memory:
  enabled: true
  summary_threshold: 20
  retrieval_top_k: 5

context:
  max_chars: 1200

prompt:
  kb_aliases:
    resume_text: user_profile_kb
    jd_text: user_profile_kb

knowledge_bases:
  user_profile_kb:
    type: user_upload
    use_allowed_apps_filter: true
    collection: kb_user_profile
    text_field: text
    weight: 1.0
    top_k: 5
```

### 8.2 intents.yaml

```yaml
intents:
  generate:
    description: 生成示例结果
    exposed: true
    params:
      - target_position
      - company
```

### 8.3 prompts/system.md

```md
你是一个业务助手，输出结构化 JSON。
```

### 8.4 prompts/generate.md

```md
请结合以下上下文生成结果，输出 JSON：

【用户输入】
{{query}}

【记忆】
{{memory}}

【知识库】
{{kb}}
```

### 8.5 pipeline.py

```python
from __future__ import annotations

from typing import Dict, Optional


class SamplePipeline:
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.context = None

    def run(
        self,
        *,
        identity,
        intent: str,
        user_query: str,
        intent_params: Optional[Dict] = None,
    ) -> Dict:
        if self.orchestrator is None:
            raise RuntimeError("Orchestrator not injected into pipeline")
        if intent != "generate":
            raise ValueError(f"Unsupported intent: {intent}")

        result = self.orchestrator.run_with_identity(
            identity=identity,
            intent=intent,
            user_query=user_query,
            intent_params=intent_params or {},
        )

        # Query API 会包装为 {"answer": result}
        if isinstance(result, dict) and "answer" in result:
            return result["answer"]
        return {"content": result}
```

注册后可通过 `/query` 调用 `intent=generate`。

---

## 9. 扩展 API

流程：

1) 新增 router 文件（`backend/api/routers/*.py`）
2) 挂载到 `api/main.py`
3) 增加 schema（`backend/api/schemas/*`）
4) 更新接口文档 `backend/docs/api.md`
5) 增加冒烟脚本（`backend/scripts/`）

---

## 10. 测试与验证

推荐脚本：

- `backend/scripts/smoke_interviewer_flow.py`
- `backend/scripts/smoke_resume_flow.py`
- `backend/scripts/smoke_jd_flow.py`
- `backend/scripts/run_full_validation.py`

参数说明见 `backend/scripts/README_VALIDATION.md`。
