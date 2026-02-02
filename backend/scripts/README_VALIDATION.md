# 验证脚本说明（yeying-知识库）

**更新日期**：2026-02-02  
**适用范围**：联调、发布前验证

---

## 1. 测试数据

- `backend/scripts/testdata/resume.json`
- `backend/scripts/testdata/session_history.json`
- `backend/scripts/testdata/jd.json`

---

## 2. 全量验证

```bash
python backend/scripts/run_full_validation.py --timeout 120
```

可选参数：

- `--resume-file /path/to/resume.json`
- `--session-file /path/to/session_history.json`
- `--jd-file /path/to/jd.json`
- `--skip-query`
- `--skip-default`

---

## 3. 冒烟脚本

- `python backend/scripts/smoke_interviewer_flow.py`
- `python backend/scripts/smoke_resume_flow.py`
- `python backend/scripts/smoke_jd_flow.py`

---

## 4. 控制台权限校验

```bash
python backend/scripts/validate_console_access.py --wallet-id wallet_demo --app-id interviewer
```

可选：

- `--super-admin-id`（默认读取 `SUPER_ADMIN_WALLET_ID`）

---

## 5. 注意事项

- 生产环境建议使用 SIWE/JWT；开发调试可通过 `AUTH_ALLOW_INSECURE_WALLET_ID=true` 放行
- 私有库写入需保证 `wallet_id` 与 `allowed_apps` 字段正确

