# SDD-03 数据入库与向量化

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：后端研发、数据接入、运营

---

## 1. 目的

规范知识库文档写入与向量化流程，确保数据可检索、可审计、可隔离。

---

## 2. 数据流

1) 业务侧调用 KB 文档接口  
2) 写入 Weaviate（向量检索）  
3) 写入 SQLite（审计与统计）  

---

## 3. 知识库类型与隔离

- `public_kb`：公共共享  
- `user_upload`：用户私有数据库（基于 `data_wallet_id` / `private_db_id` 隔离）

当 `use_allowed_apps_filter=true` 时，写入/检索会基于 `allowed_apps` 过滤。

---

## 4. Schema 与向量字段

控制台允许超级管理员配置：

- 字段 Schema（字段名、类型、描述）
- 向量化字段（用于 embedding）

写入文档时：

- `text_field` 为默认向量化字段
- `vector_fields` 可配置多个字段进行向量化

---

## 5. 主要接口

- `POST /kb/{app_id}/{kb_key}/documents`  
- `GET /kb/{app_id}/{kb_key}/documents`  
- `PUT /kb/{app_id}/{kb_key}/documents/{doc_id}`  
- `PATCH /kb/{app_id}/{kb_key}/documents/{doc_id}`  
- `DELETE /kb/{app_id}/{kb_key}/documents/{doc_id}`

详细字段见 `backend/docs/api.md`。

