# yeying-知识库（RAG-中台）

面向业务租户的知识库与检索增强（RAG）中台，提供多租户隔离、知识库配置、向量化管理、记忆服务、工作流编排与插件化扩展，并配套可视化控制台。

**文档更新时间**：2026-02-02

---

## 核心能力

- 多租户隔离：应用（`app_id`）与业务用户（`data_wallet_id`）双层隔离
- 知识库类型：公共知识库（`public_kb`）与用户私有数据库（`user_upload`）
- Schema + 向量字段：超级管理员可配置字段与向量化字段
- 记忆服务：会话记忆写入、检索与删除
- 摄取作业：作业化摄取与执行记录
- 工作流编排：Intent + Workflow 配置与执行
- 插件化扩展：`config.yaml` / `intents.yaml` / `workflows.yaml` / `pipeline.py` / `prompts`
- 审计日志：数据库配置与私有库变更可追踪

---

## 快速启动

1) 安装依赖
```bash
pip install -r backend/requirements.txt
```

2) 启动后端（自动挂载前端控制台）
```bash
cd backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

3) 打开控制台
- 登录页：`/console/login.html`
- 总览：`/console/index.html`
- 应用控制台：`/console/app.html?app_id=<app_id>`

---

## 文档索引（SDD）

- `docs/product-baseline.md`：SDD-01 产品与范围
- `docs/system-architecture.md`：SDD-02 系统架构与核心概念
- `docs/backend-kb-ingestion.md`：SDD-03 数据入库与向量化
- `docs/backend-kb-metadata.md`：SDD-03A 元数据规范
- `docs/backend-ingestion-jobs.md`：SDD-04 摄取作业与调度
- `docs/backend-ingestion-parsers.md`：SDD-04A 摄取解析器
- `docs/interviewer-collaboration.md`：SDD-05 插件设计与协作
- `docs/backend-dev-guide.md`：SDD-06 后端开发与扩展
- `docs/backend-manual.md`：SDD-07 后端部署与运行
- `docs/frontend-manual.md`：SDD-08 前端控制台使用手册
- `docs/ops-manual.md`：SDD-09 运维与监控
- `docs/integration.md`：SDD-10 业务接入指南
- `backend/docs/api.md`：SDD-11 API 参考（概览）
- `openapi.yaml`：API 文档源（OpenAPI 3.0.3）
