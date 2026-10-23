---
id: sqlite_and_transactions
title: SQLite 与事务
english_title: SQLite and Transactions
aliases: [SQLite, 事务, transaction, commit, rollback, 数据库连接]
category: programming_engineering
software_status: implemented
related_modules: [存储, 研究笔记, 迁移, 自选股]
prerequisites: [python_functions, python_exceptions]
related_articles: [schema_migration, hash_and_fingerprint, csv_and_json, reproducibility_and_audit]
source_ids: [S011, S018, P004]
last_verified: 2026-10-23
---

# SQLite 与事务（SQLite and Transactions）

## 快速理解

### 一句话解释

SQLite 是把整个数据库保存在一个文件里的嵌入式数据库；事务把一组写入当作一个整体，全部成功才提交，任何一步失败就回滚，避免留下写了一半的研究档案。

### 它解决什么问题

保存实验要同时写入标题、参数、两份行情 BLOB、哈希和指标。如果中途失败，只写了一半的记录会破坏复算。事务保证这些写入要么全部生效，要么全部不生效；连接管理还负责外键、行访问方式和关闭。

### 最常见的误解

- **“SQLite 是小型服务器”**：它是嵌入式库，数据库就是一个文件；没有独立数据库服务进程。
- **“提交后一定永久安全”**：提交保证事务生效，但不等于远程备份、磁盘冗余或灾难恢复。
- **“回滚能撤销所有副作用”**：只撤销当前事务内的数据库修改；已写出的文件、日志或网络请求不会回滚。
- **“SQLite 自动提供用户隔离和加密”**：默认没有用户账户隔离，也没有数据库文件加密；有文件权限的人可以读取。
- **“有外键声明就会自动检查”**：SQLite 需要每个连接执行 `PRAGMA foreign_keys=ON`。
- **“`timeout=15` 表示永不锁死”**：它只是等待锁的最长时间；超时仍可能报“database is locked”。

## 软件实践

### 在 Quant Lab 哪里出现

- `storage._connect` 打开活动数据库，设置 `timeout=15`、`row_factory=sqlite3.Row` 和 `PRAGMA foreign_keys=ON`，然后调用 `migrate`。
- 上下文正常结束时 `commit()`；发生异常时 `rollback()` 并重新抛出；最后 `close()`。
- `save_experiment` 在一次连接中插入实验记录，包括两份压缩 CSV、SHA-256、参数、来源和指纹。
- `save_security_name`、`add_watchlist`、`save_learning_note` 都通过同一个连接上下文写入。
- `migrations.migrate` 在升级时使用 `BEGIN IMMEDIATE`，成功后更新 `PRAGMA user_version` 并提交。
- 数据库路径来自 `paths.database_path()`，位于用户可写资料库；安装目录视为只读。

### 输入、输出和单位

- 输入是 SQL 语句和参数；参数使用 `?` 占位符，避免拼接字符串。
- 输出是 `sqlite3.Row`，可以按列名读取。
- SQLite 存储类型包括 `INTEGER`、`REAL`、`TEXT`、`BLOB` 和 `NULL`。
- 时间通常保存为 ISO 8601 文本；金额和比例保存为 `REAL`。
- 两份 CSV 以 `zlib` 压缩后的 BLOB 保存；数据库文件本身不保存原始 DataFrame 对象。
- 事务没有金融单位；它保证写入的原子性。

### 结果应该怎么读

- 实验保存成功表示事务已提交；失败表示回滚，不应出现半条实验记录。
- 读取实验时，先解压 BLOB，再核对 SHA-256；不一致时拒绝复算。
- 看到“database is locked”时，说明另一个连接持有写锁超过等待时间；不是数据损坏。
- 看到外键错误时，检查引用的分类、实验或笔记是否存在。
- 看到数据库版本错误时，说明数据库比当前软件新；不要用旧版软件强行打开。
- 看到数据库文件很大时，可能是行情 BLOB 和附件元数据；当前没有自动清理历史实验。

### 当前软件边界

- 当前只有本地 SQLite 文件，没有远程数据库、数据库服务器或云同步。
- 没有用户账户、行级权限或多租户隔离；同一操作系统用户可访问同一资料库。
- 没有数据库加密、透明加密或防篡改保证；文件权限由操作系统管理。
- 没有连接池、ORM 或异步数据库驱动；每次操作通过上下文打开连接。
- 事务只覆盖数据库写入，不覆盖网络请求、文件写入和 UI 状态。
- SQLite 的备份、迁移和完整性检查是不同流程；备份不等于灾难恢复。
- 文章中的 SQL 示例是通用 SQLite，不代表软件提供 SQL 控制台。

## 专业原理

### 正式定义

SQLite 是嵌入式关系数据库，数据存储在单个文件中。事务是具有 ACID 属性的操作单元：

- 原子性（Atomicity）：全部成功或全部失败；
- 一致性（Consistency）：约束在事务结束时成立；
- 隔离性（Isolation）：并发事务的可见性规则；
- 持久性（Durability）：提交后的修改在崩溃后仍应存在（取决于日志和文件系统）。

SQLite 使用回滚日志（默认）或 WAL 模式实现事务；当前项目没有显式切换日志模式，使用默认配置。

### 公式与符号

事务结果可以抽象为：

`commit(T)`：T 的所有写入生效；

`rollback(T)`：T 的所有写入撤销。

读取时的校验：

`valid_snapshot = SHA256(decompress(blob)) == stored_sha256`

只有校验通过，才把字节解析为 DataFrame。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
import sqlite3

connection = sqlite3.connect(":memory:")
connection.execute("CREATE TABLE t (v INTEGER)")

connection.execute("BEGIN IMMEDIATE")
connection.execute("INSERT INTO t VALUES (1)")
connection.rollback()
print(connection.execute("SELECT COUNT(*) FROM t").fetchone()[0])  # 0

connection.execute("BEGIN IMMEDIATE")
connection.execute("INSERT INTO t VALUES (2)")
connection.commit()
print(connection.execute("SELECT COUNT(*) FROM t").fetchone()[0])  # 1
```

计算：

- 第一次插入后回滚，表中行数为 0；
- 第二次插入后提交，表中行数为 1；
- 回滚没有留下第一行。

连接管理示意（伪代码）：

```text
open connection
try:
    configure
    yield connection
    commit
except:
    rollback
    raise
finally:
    close
```

### 前提假设

- 数据库文件位于可写目录，且当前用户有读写权限。
- 每个连接都设置 `foreign_keys=ON`；外键约束才会生效。
- 写入使用参数化查询，不把用户输入拼进 SQL。
- 事务内的操作在同一个连接上执行；跨连接事务不由当前代码协调。
- 数据库文件不会被多个不兼容版本的软件同时写入；版本检查在连接时进行。
- 备份和完整性检查使用 SQLite 提供的机制，而不是直接复制正在写入的文件。

### 边界情况

- 并发写入：SQLite 允许并发读，但写入需要锁；等待超过 `timeout=15` 可能报错。
- 进程崩溃：事务未提交则回滚；已提交的数据取决于日志和磁盘状态。
- 磁盘满：写入失败并回滚；需要释放空间后重试。
- 外键关闭：如果忘记 `PRAGMA foreign_keys=ON`，无效引用可能写入。
- 数据库文件被手工修改：SQLite 可能报损坏或返回异常数据；当前没有防篡改保证。
- 直接复制活动数据库文件：可能得到不一致副本；迁移使用 SQLite backup API，资料库复制使用 backup API，而不是简单文件复制。
- 事务中执行网络请求：会长时间持锁；当前存储函数不在事务内发网络请求。
- 嵌套连接：不同函数各自打开连接，可能在同一线程内竞争锁；当前没有跨函数的长事务。

## 相关知识

### 前置概念

- `python_functions`：存储操作封装为函数。
- `python_exceptions`：异常触发回滚。

### 相关词条

- `schema_migration` Schema 迁移
- `hash_and_fingerprint` 哈希与指纹
- `csv_and_json` CSV 与 JSON
- `reproducibility_and_audit` 可复现性与审计

### 建议下一篇

`schema_migration`：了解数据库结构变化如何通过版本号和事务升级。

## 参考资料

- `S011` SQLite 文档：数据库、事务、锁和 `PRAGMA`；页面未联网复核。
- `S018` Python sqlite3 文档：连接、游标、事务和 `row_factory`；页面未联网复核。
- `P004` docs/DATA.md：活动数据库位于用户目录、安装目录只读的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
