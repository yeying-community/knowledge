# SDD-03A 元数据规范

**项目**：yeying-知识库（RAG-中台）  
**版本**：v2.1  
**更新日期**：2026-02-02  
**适用范围**：数据接入、后端研发

---

## 1. 保留字段（user_upload）

用户私有数据库会自动写入/使用以下字段：

- `wallet_id`：数据归属钱包  
- `private_db_id`：私有库 ID  
- `resume_id` / `jd_id`：业务标识（可选）  
- `source_url`：源文件 URL  
- `file_type`：文件类型  
- `metadata_json`：原始元数据  
- `allowed_apps`：应用过滤字段（可选）

---

## 2. 推荐字段

- `title`：标题  
- `summary`：摘要  
- `tags`：标签  
- `source`：来源系统  

---

## 3. Schema 字段类型

Weaviate 字段类型映射在后端完成，建议使用：

- `text` / `string`
- `number`
- `boolean`
- `date`

---

## 4. 写入建议

- 必须保证 `text_field` 有内容  
- 对于 `user_upload`，尽量写入 `wallet_id` 或 `private_db_id`

