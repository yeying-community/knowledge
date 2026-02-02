# SDD-10 业务接入指南

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：业务研发、平台接入

---

## 1. 接入流程总览

1) 管理员启用应用 `/app/register`  
2) 在控制台配置 KB、Schema 与向量字段  
3) 摄取文档数据  
4) 配置 Intent / Workflow  
5) 使用 `/query` 对外调用

---

## 2. 典型接入场景

### 2.1 公共知识库（public_kb）

- 适合共享资料、制度、FAQ  
- 由租户管理员统一摄取

### 2.2 用户私有数据库（user_upload）

- 适合业务用户上传数据  
- 通过 `data_wallet_id` / `private_db_id` 进行隔离

---

## 3. 调用示例（概要）

### 3.1 注册应用

`POST /app/register`

### 3.2 写入文档

`POST /kb/{app_id}/{kb_key}/documents`

### 3.3 查询

`POST /query`

---

## 4. 工作流编排

在控制台配置 Intent 与 Workflow：

- workflow 名称与对外 Intent 一致时自动执行  
- 无需自定义 pipeline 即可运行

---

## 5. 审计与运营

- 使用 `/audit/logs` 查看配置变更  
- 建议接入方在流程中记录 `data_wallet_id` / `session_id`

