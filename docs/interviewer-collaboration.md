# SDD-05 插件设计与协作

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：插件研发、业务租户

---

## 1. 插件定义

插件是业务能力的最小承载单元，目录结构如下：

```
plugins/<app_id>/
  config.yaml
  intents.yaml
  workflows.yaml
  pipeline.py
  prompts/
```

---

## 2. 关键文件

### 2.1 config.yaml

- 配置知识库（knowledge_bases）
- 配置记忆策略（memory）
- 配置上下文策略（context）

### 2.2 intents.yaml

- Intent 名称、描述、参数
- `exposed: true` 表示对外可调用

### 2.3 workflows.yaml

- Workflow 名称、描述、执行 intents 列表
- **默认规则**：workflow 名称与对外 intent 一致时，默认 pipeline 依次执行 workflow 内 intents

### 2.4 pipeline.py

业务编排入口，需实现 `run(...)` 方法  
未提供时将使用默认 pipeline（支持 workflow 执行）

### 2.5 prompts

提示词模板，以 `prompts/*.md` 形式存在  
支持在控制台直接编辑

---

## 3. 协作方式

- 平台管理员可创建租户插件目录
- 租户可通过控制台“插件开发”面板编辑配置与代码
- 所有更新会记录审计日志（`plugin.update`）

---

## 4. 最小示例

```
config.yaml
intents.yaml
workflows.yaml
pipeline.py
prompts/system.md
```

对应的 Intent/Workflow 可以通过控制台配置，并由默认 pipeline 自动执行。

