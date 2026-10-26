---
id: schema_migration
title: Schema 迁移
english_title: Schema Migration
aliases: [数据库迁移, schema migration, user_version, 版本升级, 备份]
category: programming_engineering
software_status: implemented
related_modules: [迁移, 存储, 资料库]
prerequisites: [sqlite_and_transactions]
related_articles: [sqlite_and_transactions, hash_and_fingerprint, reproducibility_and_audit, automated_testing_git_and_modular_monolith]
source_ids: [P002, S011, S018]
last_verified: 2026-10-23
---

# Schema 迁移（Schema Migration）

## 快速理解

### 一句话解释

Schema 迁移是在不删除用户数据的前提下，把旧版数据库结构升级到新版；Quant Lab 用 SQLite 的 `PRAGMA user_version` 记录版本，当前支持版本为 4，旧库升级前先备份，升级失败则回滚。

### 它解决什么问题

新功能可能需要新表或新列，但用户已有的实验、行情快照、自选股和笔记不能丢。迁移把结构变化写成有序步骤，用版本号判断是否需要执行，并用事务保证不会停在“改了一半”的状态。

### 最常见的误解

- **“迁移就是删库重建”**：当前明确保留旧实验、行情 BLOB 和指纹，不删除后重建。
- **“版本号存在表里，和业务数据一起查”**：当前使用 SQLite 内置的 `PRAGMA user_version`，不是业务表字段。
- **“备份等于灾难恢复”**：备份通常在同一台机器、同一磁盘；不能替代远程备份和恢复演练。
- **“新版本数据库可以用旧软件打开”**：数据库版本高于软件支持版本时，当前会拒绝打开。
- **“迁移失败会自动恢复到旧版本”**：迁移事务会回滚，但软件不会自动降级；备份用于人工恢复。
- **“复制资料库和 schema 迁移是一回事”**：资料库复制是创建新资料目录并校验副本；schema 迁移是升级现有数据库结构。

## 软件实践

### 在 Quant Lab 哪里出现

- `migrations.SCHEMA_VERSION = 4`。
- `migrate` 读取 `PRAGMA user_version`；大于 4 时拒绝打开，等于 4 时直接返回。
- 旧库如果已有业务表，先在 `backups/` 目录用 SQLite backup API 创建一致性备份。
- 升级使用 `BEGIN IMMEDIATE`；成功后写入 `PRAGMA user_version=4` 并提交；异常时回滚。
- `_upgrade` 创建缺失的表、补充 `company_name`、`category_id`、`deleted_at`、`updated_at` 等列，并建立索引。
- 迁移保留 `experiments` 表中的 `raw_csv`、`signal_csv`、`raw_sha256`、`signal_sha256` 和 `audit_id`。
- `paths.stage_library` 是另一条流程：复制数据库后执行 `PRAGMA integrity_check`，再用临时 bootstrap 文件和 `os.replace` 激活资料库。

### 输入、输出和单位

- 输入是已打开的 SQLite 连接和目标数据库路径。
- 读取的版本号是整数：0 表示未版本化或全新库，4 表示当前版本。
- 备份文件名包含 `pre-v4`、UTC 时间戳和随机后缀，扩展名为 `.sqlite3`。
- 迁移输出是升级后的数据库结构；不返回金融数值。
- 备份大小取决于数据库内容；没有固定上限。

### 结果应该怎么读

- 数据库能正常打开且 `user_version=4`，表示迁移已完成或本来就无需迁移。
- 看到“数据库版本比当前软件新”时，应使用新版软件，不要手工改版本号。
- 看到 `backups/` 下的 `research.pre-v4.*.sqlite3` 时，它是升级前的一致性备份；不要把它当成当前活动库。
- 迁移失败后，活动库应保持旧结构；备份仍在，可用于排查或恢复。
- 资料库复制后的 `integrity_check` 返回 `ok`，只说明副本结构可读，不证明业务数据一定正确。

### 当前软件边界

- 当前 `SCHEMA_VERSION=4`；没有为未来版本预写迁移步骤。
- 只有向上迁移，没有自动向下迁移或回滚到旧版软件。
- 备份不自动上传远程，不验证异机恢复，也不替代用户自己的备份策略。
- 迁移不删除旧行情快照，不重写实验指纹。
- 迁移不修复业务数据错误；它只调整结构和补充必需列。
- 资料库复制、数据库迁移和 ZIP 导出是三条不同流程，不能混为一谈。
- 文章中的 SQL 示例是通用 SQLite，不代表软件提供数据库管理界面。

## 专业原理

### 正式定义

Schema 是数据库表、列、约束和索引的结构定义。迁移是把一个 schema 版本转换为下一个版本的操作序列。版本化迁移通常包含：

1. 读取当前版本；
2. 判断是否需要升级；
3. 备份或快照；
4. 在事务中执行升级步骤；
5. 更新版本号；
6. 提交或回滚。

SQLite 的 `PRAGMA user_version` 是数据库文件头中的 32 位整数，适合保存应用自定义的 schema 版本。

### 公式与符号

版本判断：

- `v > 4`：拒绝打开；
- `v = 4`：无需迁移；
- `v < 4`：执行升级。

迁移事务：

`BEGIN IMMEDIATE → _upgrade → PRAGMA user_version=4 → COMMIT`

任一步失败：

`ROLLBACK`，数据库保持迁移前状态。

### 可手算的小例子

通用 SQLite 示例（不是软件功能）：

```python
import sqlite3

connection = sqlite3.connect(":memory:")
print(connection.execute("PRAGMA user_version").fetchone()[0])  # 0

connection.execute("BEGIN IMMEDIATE")
connection.execute("CREATE TABLE example (id INTEGER PRIMARY KEY)")
connection.execute("PRAGMA user_version=4")
connection.commit()

print(connection.execute("PRAGMA user_version").fetchone()[0])  # 4
```

计算：

- 新库版本为 0；
- 迁移后版本为 4；
- 事务提交后，表和版本号同时生效。

版本分支示例：

| 当前版本 | 软件支持版本 | 行为 |
| --- | --- | --- |
| 0（空库） | 4 | 创建结构，写入版本 4 |
| 0（有旧表） | 4 | 先备份，再升级 |
| 3 | 4 | 先备份，再升级 |
| 4 | 4 | 直接返回 |
| 5 | 4 | 拒绝打开 |

### 前提假设

- 旧数据库可以通过 SQLite 正常打开，且没有未提交的写事务。
- 备份路径可写，磁盘空间足够。
- 迁移步骤是幂等的或由版本号保证只执行一次。
- 升级不依赖网络、用户交互或外部服务。
- 迁移期间没有其他进程同时写入同一数据库。
- 旧实验的 BLOB 和指纹在升级中保持不变。

### 边界情况

- 空数据库：没有业务表，不需要备份；直接创建结构。
- 未版本化旧库：`user_version=0` 但有表；需要备份后升级。
- 数据库版本更高：拒绝打开，避免旧代码破坏新结构。
- 备份失败：不应继续迁移；当前备份步骤在事务前执行。
- 迁移中断：事务回滚，但已创建的备份文件保留。
- 磁盘满：迁移或备份失败；需要释放空间后重试。
- 并发打开：SQLite 锁可能让迁移等待或失败；不要在迁移时同时运行多个写入进程。
- 手工修改版本号：可能导致结构不匹配；不要绕过版本检查。
- 资料库复制：复制后执行 `integrity_check`；这与 schema 迁移的备份和事务是不同保障。

## 相关知识

### 前置概念

- `sqlite_and_transactions`：迁移依赖事务、连接和 SQLite 文件。

### 相关词条

- `hash_and_fingerprint` 哈希与指纹
- `reproducibility_and_audit` 可复现性与审计
- `automated_testing_git_and_modular_monolith` 自动化测试、Git 与模块化单体
- `sqlite_and_transactions` SQLite 与事务

### 建议下一篇

`hash_and_fingerprint`：了解迁移保留的实验快照如何用哈希校验完整性。

## 参考资料

- `P002` ARCHITECTURE.md：`PRAGMA user_version=4`、备份、`BEGIN IMMEDIATE` 和旧实验保留口径。
- `S011` SQLite 文档：`PRAGMA user_version`、事务、备份 API 和完整性检查；页面未联网复核。
- `S018` Python sqlite3 文档：连接、事务和 `backup` 方法；页面未联网复核。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
