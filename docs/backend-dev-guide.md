# SDD-06 后端开发与扩展

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：后端研发、插件研发

---

## 1. 目录结构

```
backend/
  api/                 # FastAPI 路由与接口
  core/                # 编排、记忆、KB、Prompt、LLM/Embedding
  datasource/          # SQLite / MinIO / Weaviate
  plugins/             # 插件目录（每个 app_id 一个插件）
  settings/            # 配置读取
  scripts/             # 验证与冒烟脚本
```

---

## 2. 插件扩展点

插件目录：`backend/plugins/<app_id>/`

最小结构：

```
plugins/<app_id>/
  config.yaml
  intents.yaml
  workflows.yaml
  pipeline.py
  prompts/
    system.md
```

### 2.1 config.yaml

- 定义知识库、记忆策略、上下文策略
- Schema 与向量字段由控制台写入 `knowledge_bases` 中

### 2.2 intents.yaml

- 定义业务意图（Intent），可配置描述、参数、是否对外公开（exposed）

### 2.3 workflows.yaml

- 由多个 Intent 组成的业务流程
- **默认执行规则**：当 `workflow.name` 与对外 Intent 名称一致时，默认 pipeline 会按顺序执行 workflow 内的 intents

### 2.4 pipeline.py

实现 `run(...)` 方法，作为业务编排入口。  
若没有 `pipeline.py`，系统会使用默认 pipeline（支持 workflow 顺序执行）。

---

## 3. 编排流程（后端）

入口：`POST /query`

核心流程：

1) 校验 `app_id` 是否已注册  
2) 解析身份（`wallet_id + app_id + session_id`）  
3) 读取记忆摘要与上下文  
4) 根据 KB 配置做向量检索  
5) 构造 Prompt 调用 LLM  

---

## 4. 新增接口流程

1) 在 `backend/api/routers/` 添加路由  
2) 注册到 `api/main.py`  
3) 使用 `api/deps.get_deps()` 获取依赖  
4) 按照审计规范写入 `audit_logs`（涉及配置或数据变更）

---

## 5. 开发与验证

启动：

```bash
cd backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

脚本：

- `backend/scripts/run_full_validation.py`
- `backend/scripts/smoke_interviewer_flow.py`

---

## 6. 鉴权与安全

- 支持 SIWE/JWT 与 UCAN
- `AUTH_ALLOW_INSECURE_WALLET_ID=true` 仅用于开发调试
- 生产环境必须配置 `JWT_SECRET`

