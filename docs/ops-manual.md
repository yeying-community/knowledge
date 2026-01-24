# 运维手册

本手册面向部署与运维场景，提供环境配置、健康检查、日志排障与验证建议。

---

## 1. 运行环境

建议使用已安装依赖的 Python 环境运行后端（如 conda / venv）。  
前端由后端自动挂载，默认路径 `/console`。

常见启动方式：

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 2. 配置文件与环境变量

后端配置来源：`.env`（自动向上查找）  
读取逻辑：`backend/settings/config.py`

关键参数示例：

- `MINIO_*`：MinIO 连接与 bucket
- `WEAVIATE_*`：向量库连接
- `OPENAI_*` / `EMBED_*`：模型与向量化
- `SQLITE_PATH`：SQLite 文件路径
- `PLUGINS_AUTO_REGISTER`：自动注册插件列表

---

## 3. 健康检查流程

1) `GET /health`
2) `GET /stores/health`
3) `GET /app/list`
4) `GET /kb/list`
5) 可选：`GET /kb/{app}/{kb}/stats`


---

## 4. 典型故障与排查

### 4.1 Weaviate “class already exists”

幂等创建产生的提示，不影响功能。  
重启服务后日志应减少。

### 4.2 KB 查询为空

常见原因：

- user_upload KB 未写入 `wallet_id`
- `allowed_apps` 与 `app_id` 不匹配
- KB collection 实际未创建

建议使用：

- `/kb/{app}/{kb}/documents?wallet_id=xxx&data_wallet_id=user_123`
- `/kb/{app}/{kb}/stats?wallet_id=xxx&data_wallet_id=user_123`

---

## 5. 验证与冒烟

脚本位于 `backend/scripts/`：

- `smoke_interviewer_flow.py`
- `smoke_resume_flow.py`
- `smoke_jd_flow.py`
- `run_full_validation.py`

建议在发布前跑通全链路验证脚本，确保 MinIO / Weaviate / LLM 全部连通。
