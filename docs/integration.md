# 简历 JSON 规范模板与业务接入示例

本文件用于业务方接入时的参考模板与示例流程，覆盖简历 JSON 规范、MinIO 存储路径与接口调用。

---

## 1. 简历 JSON 规范模板

推荐字段（可按业务扩展）：

```json
{
  "resume_id": "uuid-or-business-id",
  "name": "Alex Chen",
  "email": "alex.chen@example.com",
  "skills": ["python", "golang", "redis"],
  "projects": [
    "Built a task scheduler with idempotent execution and compensation flows."
  ],
  "education": [
    {"school": "Example University", "degree": "B.S. Computer Science", "year": "2019"}
  ],
  "text": "Backend engineer with 5 years of experience in distributed systems."
}
```

解析规则：

- 若存在 `text` / `content` / `resume` 字段，直接用作文本
- 否则使用 `segments` 数组拼接
- 若字段都不存在，将整个 JSON 作为文本写入

---

## 2. MinIO 路径规范

业务端上传文件建议遵循：

```
memory/<wallet_id>/<app_id>/<session_id>/<filename>
```

如：

```
memory/wallet_demo/interviewer/session_001/resume/profile.json
```

说明：
- `memory/` 前缀用于会话历史与业务自管文件
- 简历 / JD 通过 `/resume/upload` 与 `/{app_id}/jd/upload` 上传时由中台写入 `kb/` 前缀

示例：

```
kb/wallet_demo/interviewer/resume/<resume_id>.json
kb/wallet_demo/interviewer/jd/<jd_id>.json
```

---

## 3. 业务接入流程（示例）

### 3.1 上传简历 JSON 到 MinIO

业务侧将简历文件上传到 MinIO，得到可访问 URL 或对象 key。

### 3.2 上传简历（推荐）

调用 `POST /resume/upload`，中台会返回 `resume_id`：

```json
{
  "wallet_id": "wallet_demo",
  "app_id": "interviewer",
  "resume_id": "optional-resume-id",
  "kb_key": "optional-user-upload-kb",
  "metadata": {"source": "biz"},
  "resume": {
    "name": "Alex Chen",
    "skills": ["python", "golang"],
    "text": "Backend engineer with 5 years of experience in distributed systems."
  }
}
```

### 3.3 上传 JD（推荐）

调用 `POST /{app_id}/jd/upload`，中台会返回 `jd_id`：

```json
{
  "wallet_id": "wallet_demo",
  "app_id": "interviewer",
  "jd_id": "optional-jd-id",
  "kb_key": "optional-user-upload-kb",
  "metadata": {"source": "biz"},
  "jd": {
    "title": "Backend Engineer",
    "requirements": ["Python", "Distributed Systems"],
    "text": "We are looking for a Backend Engineer..."
  }
}
```

响应示例：

```json
{
  "jd_id": "7a4f0b4e-9d9f-4b9f-9b25-8f7b5a92a8a1",
  "kb_key": "user_profile_kb",
  "collection": "kb_user_profile",
  "doc_id": "d2b5d3e4-1c1b-4d3f-8b5d-9e1f2a3b4c5d",
  "source_url": "minio://bucket/kb/wallet_demo/interviewer/jd/7a4f0b4e-9d9f-4b9f-9b25-8f7b5a92a8a1.json"
}
```

响应示例：

```json
{
  "resume_id": "a8a3c9c0-2fd5-4d32-9c95-0f7c4c8763f4",
  "kb_key": "user_profile_kb",
  "collection": "kb_user_profile",
  "doc_id": "b367956c-41b6-444c-881c-ef8bd62bcc98",
  "source_url": "minio://bucket/kb/wallet_demo/interviewer/resume/a8a3c9c0-2fd5-4d32-9c95-0f7c4c8763f4.json"
}
```

---

## 4. 会话历史写入与记忆推送

会话历史结构：

```json
{
  "messages": [
    {"role": "user", "content": "你好，我准备面试后端岗位。"},
    {"role": "assistant", "content": "好的，我们开始。"}
  ]
}
```

上传后调用：

```
POST /memory/push
{
  "wallet_id": "wallet_demo",
  "app_id": "interviewer",
  "session_id": "session_001",
  "filename": "history/session.json"
}
```

---

## 5. 业务查询示例

调用 `/query`：

```json
{
  "wallet_id": "wallet_demo",
  "app_id": "interviewer",
  "session_id": "session_001",
  "intent": "generate_questions",
  "query": "我是后端工程师，准备面试，请给我一些问题。",
  "intent_params": {
    "basic_count": 2,
    "project_count": 2,
    "scenario_count": 1,
    "target_position": "后端工程师"
  }
}
```

若业务希望由简历驱动，可传 `resume_id`：

```json
{
  "wallet_id": "wallet_demo",
  "app_id": "interviewer",
  "session_id": "session_001",
  "intent": "generate_questions",
  "resume_id": "a8a3c9c0-2fd5-4d32-9c95-0f7c4c8763f4",
  "target": "后端工程师",
  "company": "示例公司"
}
```

若业务希望由 JD 驱动，可传 `jd_id`：

```json
{
  "wallet_id": "wallet_demo",
  "app_id": "interviewer",
  "session_id": "session_001",
  "intent": "generate_questions",
  "jd_id": "7a4f0b4e-9d9f-4b9f-9b25-8f7b5a92a8a1",
  "target": "后端工程师",
  "company": "示例公司"
}
```

若业务同时提供简历与 JD，可同时传：

```json
{
  "wallet_id": "wallet_demo",
  "app_id": "interviewer",
  "session_id": "session_001",
  "intent": "generate_questions",
  "resume_id": "a8a3c9c0-2fd5-4d32-9c95-0f7c4c8763f4",
  "jd_id": "7a4f0b4e-9d9f-4b9f-9b25-8f7b5a92a8a1",
  "target": "后端工程师"
}
```
