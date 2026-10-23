---
id: hash_and_fingerprint
title: 哈希与指纹
english_title: Hash and Fingerprint
aliases: [哈希, 指纹, SHA-256, audit_id, 摘要, 校验和]
category: programming_engineering
software_status: implemented
related_modules: [研究实验, 存储, 研究笔记, AI 上下文]
prerequisites: [csv_and_json]
related_articles: [reproducibility_and_audit, csv_and_json, sqlite_and_transactions, data_provenance]
source_ids: [S008, P002]
last_verified: 2026-10-23
---

# 哈希与指纹（Hash and Fingerprint）

## 快速理解

### 一句话解释

哈希把任意长度的字节映射成固定长度的摘要；Quant Lab 用完整 SHA-256 校验实验行情和附件，用 SHA-256 前 16 个十六进制字符作为短的实验指纹 `audit_id`。

### 它解决什么问题

研究需要判断“这份快照有没有变”“两份实验是不是同一组输入”。完整哈希用于完整性校验；短指纹用于显示、比较和 AI 上下文作用域。它们让复算和审计有可核对的标识。

### 最常见的误解

- **“哈希是加密”**：哈希不是加密，没有密钥，也不能还原原文；它只提供摘要。
- **“哈希能证明数据真实”**：相同哈希只能说明字节相同，不能证明来源可靠、数据无偏或结论正确。
- **“`audit_id` 是完整 SHA-256”**：它是前 16 个十六进制字符，只有 64 位，不是完整 256 位摘要。
- **“相同哈希一定代表同一个实验”**：哈希输入不包含所有溯源字段；市场、代码、来源和时间不一定进入指纹。
- **“哈希是数字签名”**：没有私钥签名，任何人都能重新计算哈希；它不提供身份认证或第三方存证。
- **“重新保存 CSV 一定得到相同哈希”**：列顺序、浮点格式、换行和 pandas 版本都可能改变字节。

## 软件实践

### 在 Quant Lab 哪里出现

- `research.run_experiment` 计算 `audit_id`：对原始 CSV 字节、信号 CSV 字节、`repr(spec)`、`repr(config)` 和 `str(train_fraction)` 依次更新 SHA-256，取前 16 个十六进制字符。
- `storage.save_experiment` 分别保存 `raw_sha256` 和 `signal_sha256` 的完整 64 位十六进制摘要。
- 读取实验时先解压 BLOB，再核对完整 SHA-256；不一致时拒绝复算。
- 笔记附件保存完整 SHA-256，读取和导出时复核。
- `ai_context.bundle_context` 对行情 CSV 计算 SHA-256 前 16 位，作为 `data_fingerprint`。
- `ai_context.context_scope` 对选定的上下文字段做 JSON 序列化（键排序），再取 SHA-256 前 16 位。
- 实验 ZIP 的 `assumptions.json` 同时包含 `audit_id`、`raw_sha256` 和 `signal_sha256`。

### 输入、输出和单位

- 输入是字节串；字符串必须先编码，例如 UTF-8。
- 完整 SHA-256 输出是 64 个十六进制字符，对应 256 位。
- `audit_id` 输出是 16 个十六进制字符，对应 64 位。
- 哈希值没有金融单位；它标识内容，不表示价格、收益或风险。
- CSV 哈希针对未压缩字节；SQLite 中保存的是压缩后的 BLOB，读取时先解压再校验。

### 结果应该怎么读

- 完整 SHA-256 一致，说明读取到的字节与保存时一致；不说明数据来源或计算正确。
- `audit_id` 一致，说明当前复算的五类输入与保存记录一致；不说明样本外表现好。
- `audit_id` 不一致，可能是输入数据、策略参数、成本配置或训练比例发生变化；应逐项排查。
- 两个实验的 `audit_id` 相同，不代表来源、接收时间、市场、代码、名称和复权都相同；这些字段不全部进入指纹。
- 附件哈希不一致时，文件可能被修改或损坏；应停止使用该附件。

### 当前软件边界

- 哈希不是加密、数字签名、身份认证或第三方存证。
- `audit_id` 是截短指纹，碰撞概率高于完整 SHA-256；它用于标识，不用于安全对抗。
- 当前没有 HMAC、密钥盐、时间戳服务或区块链存证。
- 哈希不能证明金融结论真实、数据无偏或策略可盈利。
- 当前没有对源码提交、输入契约版本或运行环境做哈希；实验档案也不全部保存这些信息。
- 哈希算法或序列化方式变化会影响历史指纹的兼容性；需要迁移或兼容策略。
- 文章中的哈希示例是通用 Python，不代表软件提供哈希计算工具。

## 专业原理

### 正式定义

密码学哈希函数把任意长度输入映射为固定长度输出，理想性质包括：

- 确定性：相同输入得到相同输出；
- 快速计算；
- 抗原像性：难以从摘要反推输入；
- 抗第二原像性：难以找到另一个输入得到相同摘要；
- 抗碰撞性：难以找到两个不同输入得到相同摘要。

SHA-256 输出 256 位，通常写成 64 个十六进制字符。截短到 16 个十六进制字符后只有 64 位，抗碰撞强度显著降低。

### 公式与符号

完整摘要：

`H = SHA256(bytes)`

实验指纹：

`audit_id = first16hex(SHA256(raw_csv_bytes ‖ signal_csv_bytes ‖ repr(spec) ‖ repr(config) ‖ str(train_fraction)))`

完整性校验：

`valid = SHA256(stored_bytes) == stored_sha256`

附件校验同理。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
import hashlib

digest = hashlib.sha256(b"abc").hexdigest()
print(digest)
print(digest[:16])
print(len(digest))
```

结果：

- 完整摘要：`ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`；
- 前 16 位：`ba7816bf8f01cfea`；
- 长度：64 个十六进制字符。

若输入改为 `b"abd"`，摘要会完全不同；哈希不保留“只改了一个字符”的可读信息。

指纹输入示意：

```text
raw_csv_bytes
signal_csv_bytes
repr(StrategySpec(...))
repr(BacktestConfig(...))
str(train_fraction)
```

把这些字节依次送入同一个 SHA-256 对象，再取前 16 位，就是 `audit_id` 的构造方式。

### 前提假设

- 输入字节的序列化方式稳定；相同 DataFrame 和相同 pandas 版本才能复现相同 CSV。
- 哈希算法和截短长度在研究期间不变。
- 完整摘要用于完整性校验；短指纹用于标识，不用于安全认证。
- 比较哈希时使用常量时间比较可以降低时序攻击风险；当前场景是本地完整性检查，不是远程认证。
- 保存的哈希与数据一起存放；如果攻击者能同时修改数据和哈希，完整性检查不能阻止篡改。

### 边界情况

- 空输入：SHA-256 也有固定摘要；空文件不是“没有哈希”。
- 相同内容、不同列顺序：CSV 字节不同，哈希不同。
- 相同内容、不同浮点格式：文本不同，哈希不同。
- 相同 DataFrame、不同 pandas 版本：`to_csv` 输出可能变化，哈希可能不同。
- 截短指纹碰撞：64 位空间比 256 位小得多；大量实验时碰撞概率上升。
- 哈希与压缩：先压缩再哈希与先哈希再压缩是不同输入；当前哈希未压缩 CSV。
- 手工修改 JSON：`assumptions.json` 中的哈希可以被改写；它不是签名。
- 文件权限：有权限的人可以替换数据和哈希；哈希不提供访问控制。
- 源码或环境变化：当前指纹不覆盖源码提交和依赖版本；相同输入在不同代码版本下可能得到不同结果。

## 相关知识

### 前置概念

- `csv_and_json`：哈希输入通常是序列化后的 CSV 或 JSON 字节。

### 相关词条

- `reproducibility_and_audit` 可复现性与审计
- `sqlite_and_transactions` SQLite 与事务
- `data_provenance` 数据来源与时间戳
- `schema_migration` Schema 迁移

### 建议下一篇

`provider_api_cache_and_concurrency`：了解数据在进入指纹之前如何获取、缓存和合并并发请求。

## 参考资料

- `S008` Python 3 文档：`hashlib` 和 SHA-256 的接口；页面未联网复核。
- `P002` ARCHITECTURE.md：实验快照、SHA-256 和复算指纹的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
