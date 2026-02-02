# SDD-08 前端控制台使用手册

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：运营、业务租户、平台管理员

---

## 1. 入口

- 登录：`/console/login.html`
- 总览：`/console/index.html`
- 应用控制台：`/console/app.html?app_id=<app_id>`
- 设置：`/console/settings.html`
- 摄取作业：`/console/ingestion_jobs.html`

---

## 2. 身份与角色

- 控制台使用 SIWE 登录
- 超级管理员由 `SUPER_ADMIN_WALLET_ID` 指定
- 页面右上角显示当前角色

---

## 3. 应用控制台模块

### 3.1 知识库

- 展示当前应用的 KB 列表与统计
- 支持配置 **公共知识库 / 用户私有数据库**
- 超级管理员可配置 Schema 字段与向量化字段

### 3.2 文档管理

- 分页、排序、列偏好
- 批量删除 / 导出
- 支持 `data_wallet_id` / `private_db_id` / `session_id` 过滤

### 3.3 记忆管理

- 记忆会话列表
- 查看上下文记录
- 支持删除记忆会话

### 3.4 业务编排

- Intent 管理
- 工作流设计（Workflow）
- **规则**：workflow 名称与对外 Intent 一致时会自动执行

### 3.5 插件开发

- 直接编辑 `config.yaml` / `intents.yaml` / `workflows.yaml` / `pipeline.py`
- 编辑 `prompts/*.md`
- 保存后即时生效（自动清缓存）

### 3.6 私有数据库

- 创建与查看私有库
- 绑定 / 解绑 session

### 3.7 审计日志

- 追踪 KB 配置、私有库、插件变更
- 支持按 action / entity / 操作钱包过滤

---

## 4. 控件与交互

- 侧边栏支持折叠
- 长 ID 自动缩略，悬停显示完整值

