# RAG Validation Guide

This directory provides smoke test scripts and test data to validate the full
RAG platform flow (MinIO, SQLite, Weaviate, memory, KB CRUD, and query).


## Test Data

- `backend/scripts/testdata/resume.json`: sample resume payload (business upload).
- `backend/scripts/testdata/session_history.json`: sample chat history (business upload).
- `backend/scripts/testdata/jd.json`: sample JD payload (business upload).

## Full Validation (recommended)

```bash
python backend/scripts/run_full_validation.py --timeout 120
```

Optional flags:
- `--resume-file /path/to/resume.json`
- `--session-file /path/to/session_history.json`
- `--jd-file /path/to/jd.json`
- `--skip-query` (skip LLM query step)
- `--skip-default` (skip missing resume_id fallback query)

Note:
- New endpoints require `wallet_id` for app/KB/ingestion APIs. Use `--wallet-id` to override.

## Interviewer Session Memory Flow

```bash
python backend/scripts/smoke_interviewer_flow.py --timeout 120
```

## Resume Upload + Resume ID Flow

This flow calls `/resume/upload` and then queries by `resume_id` without `query`.

```bash
python backend/scripts/smoke_resume_flow.py --timeout 120
```

## JD Upload + JD ID Flow

```bash
python backend/scripts/smoke_jd_flow.py --timeout 120
```

## Tenant Console Validation

Validate tenant isolation + app status APIs (no LLM required):

```bash
python backend/scripts/validate_console_access.py --wallet-id wallet_demo --app-id interviewer
```

Optional:
- `--super-admin-id` to check super admin list (defaults to `SUPER_ADMIN_WALLET_ID` env).

## Notes

- MinIO path convention: `memory/{wallet_id}/{app_id}/{session_id}/{filename}`
- Private KB documents must include `wallet_id` (and `allowed_apps` if enabled)
  to enforce data isolation.
