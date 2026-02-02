# SDD-09 运维与监控

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：运维、SRE、发布人员

---

## 1. 部署模式

建议单实例或小规模水平扩展部署：

- API 服务（FastAPI）
- SQLite（本地或共享存储）
- MinIO
- Weaviate
- LLM/Embedding 服务

---

## 2. 基础启动

```bash
cd backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 3. 健康检查

1) `/health`  
2) `/stores/health`  
3) `/app/list`  
4) `/kb/list`

---

## 4. 日志与审计

- 审计日志表：`audit_logs`
- 关键操作（KB 配置、私有库、插件更新）均写入审计日志

---

## 5. 数据备份

- SQLite：定期快照备份
- MinIO：桶级别备份与生命周期配置
- Weaviate：集合级别快照

---

## 6. 安全建议

- 生产环境必须设置 `JWT_SECRET`
- 建议开启 `COOKIE_SECURE=true`
- 不建议在生产环境开启 `AUTH_ALLOW_INSECURE_WALLET_ID`

---

## 7. 常见排障

- 控制台离线：检查 `/health`
- KB 查询为空：确认 `wallet_id` / `allowed_apps` 过滤条件
- Weaviate 报 “already exists”：幂等创建提示

