# SDD-12 示例插件：interviewer

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：示例业务插件、测试联调

---

## 1. 插件定位

`interviewer` 是内置示例插件，用于演示：

- 公共知识库与用户私有数据库的组合
- Intent + Workflow 的业务编排
- 简历 / JD 结构化接入

---

## 2. 身份与权限

基础身份字段：

- `wallet_id`：操作者身份
- `app_id`：`interviewer`
- `session_id`：业务会话
- `data_wallet_id`：业务用户钱包（私有库隔离）

超级管理员由 `SUPER_ADMIN_WALLET_ID` 指定。

---

## 3. 数据写入

### 3.1 简历

- 通过 `POST /resume/upload` 写入 `user_upload` KB
- 返回 `resume_id` 供后续查询使用

### 3.2 JD

- 通过 `POST /{app_id}/jd/upload` 写入 `public_kb` 或 `user_upload`（视插件配置）

---

## 4. 业务调用

使用 `/query` 调用对外 Intent，例如：

- `intent: generate_questions`

具体参数与提示词在插件 `intents.yaml` / `prompts` 中定义。

---

## 5. 插件配置文件

```
plugins/interviewer/
  config.yaml
  intents.yaml
  workflows.yaml
  pipeline.py
  prompts/
```

可在控制台“插件开发”面板直接编辑这些文件。
