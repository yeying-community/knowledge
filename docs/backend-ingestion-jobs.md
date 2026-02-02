# SDD-04 摄取作业与调度

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：后端研发、数据运营

---

## 1. 目的

将摄取流程标准化为可追踪作业，便于异步处理与审计回溯。

---

## 2. 作业生命周期

- `pending` → `running` → `success/failed`
- 每次执行产生一条 run 记录

---

## 3. 主要接口

- `POST /ingestion/jobs`：创建作业  
- `GET /ingestion/jobs`：查询作业列表  
- `GET /ingestion/jobs/{job_id}`：获取作业详情  
- `POST /ingestion/jobs/{job_id}/run`：执行作业  
- `GET /ingestion/jobs/{job_id}/runs`：查看执行记录  
- `GET /ingestion/jobs/presets`：获取预设配置  

---

## 4. 数据来源

支持：

- MinIO URL
- 内联文本

解析器逻辑见 `docs/backend-ingestion-parsers.md`。

