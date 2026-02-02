# SDD-02 系统架构与核心概念

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：研发、架构、运维

---

## 1. 总体架构

```
控制台(Frontend) ──> API(FastAPI) ──> Core(编排/记忆/KB/Prompt)
                                 ├─ SQLite（审计/元数据）
                                 ├─ MinIO（对象存储）
                                 └─ Weaviate（向量检索）
```

---

## 2. 核心概念

- **App**：业务租户容器（`app_id`）
- **KB**：知识库（公共/私有）
- **Private DB**：私有库（`app_id + data_wallet_id`）
- **Identity**：`wallet_id + app_id + session_id`
- **Plugin**：业务配置与编排的最小单元

---

## 3. 关键流程

### 3.1 查询流程

1) 校验 app 状态  
2) 解析身份  
3) 读取记忆  
4) KB 检索  
5) Prompt 生成与 LLM 调用

### 3.2 摄取流程

1) 数据入库（KB 文档或作业）  
2) 向量化写入 Weaviate  
3) 元数据写入 SQLite

---

## 4. 多租户隔离

- 应用级隔离：`app_id`
- 数据级隔离：`data_wallet_id` / `private_db_id`
- 审计级隔离：操作钱包与应用记录

