# SDD-07 后端部署与运行

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：后端部署、联调、运行维护

---

## 1. 运行形态

后端为 FastAPI 服务，启动后自动挂载前端控制台：

- API Base：`/`
- 控制台：`/console`

---

## 2. 启动命令

```bash
cd backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 3. 环境依赖

- SQLite（默认本地文件）
- MinIO（对象存储）
- Weaviate（向量数据库）
- LLM / Embedding 模型（OpenAI 或兼容服务）

---

## 4. 关键环境变量

示例（节选）：

- `SUPER_ADMIN_WALLET_ID`：超级管理员钱包
- `JWT_SECRET`：JWT 密钥
- `AUTH_ALLOW_INSECURE_WALLET_ID`：仅开发调试可开启
- `MINIO_*`：对象存储配置
- `WEAVIATE_*`：向量库配置
- `OPENAI_*` / `EMBED_*`：模型配置
- `SQLITE_PATH`：SQLite 路径

---

## 5. 核心身份模型

身份三元组：

```
wallet_id + app_id + session_id
```

用途：

- 记忆隔离
- 私有数据库聚合
- 查询过滤

---

## 6. 应用与插件

- `app_id` 对应 `plugins/<app_id>`
- 通过 `/app/register` 启用
- 插件包含配置、意图、工作流、pipeline 与 prompts

---

## 7. 知识库配置

知识库类型：

- `public_kb`：公共知识库（共享）
- `user_upload`：用户私有数据库（隔离）

超级管理员可在控制台配置：

- Schema 字段
- 向量化字段（embedding 字段）

---

## 8. 记忆服务

记忆写入：

- `/memory/push`

记忆删除：

- `/memory/sessions` 或 `/memory/sessions/{memory_key}`

---

## 9. 工作流执行

若 `workflow.name` 与对外 Intent 名称一致，默认 pipeline 会依次执行 workflow 内的 intents。  
此能力可让租户无需自定义 pipeline 即可完成流程编排。

---

## 10. 健康检查

1) `/health`  
2) `/stores/health`  
3) `/app/list`  
4) `/kb/list`

