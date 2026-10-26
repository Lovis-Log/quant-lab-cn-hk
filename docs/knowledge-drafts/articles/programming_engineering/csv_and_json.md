---
id: csv_and_json
title: CSV 与 JSON
english_title: CSV and JSON
aliases: [CSV, JSON, 序列化, 快照, BOM, UTF-8, 研究包]
category: programming_engineering
software_status: implemented
related_modules: [存储, 研究笔记, AI 上下文, UI]
prerequisites: [pandas_series_and_dataframe, python_collections]
related_articles: [sqlite_and_transactions, hash_and_fingerprint, reproducibility_and_audit, missing_data]
source_ids: [S008, S009, P004]
last_verified: 2026-10-23
---

# CSV 与 JSON（CSV and JSON）

## 快速理解

### 一句话解释

CSV 用逗号分隔的文本保存表格，JSON 用键值结构保存配置和结果；Quant Lab 把实验行情保存为 UTF-8 CSV 字节，把策略、成本、指标和假设保存为 JSON，并对 CSV 字节计算 SHA-256。

### 它解决什么问题

研究需要可读、可移植、可复核的快照。CSV 适合表格，JSON 适合嵌套参数；两者都是纯文本，便于查看和长期保存，但都不是加密或完整性证明，读取时仍需校验。

### 最常见的误解

- **“CSV 一定用逗号、一定没有编码问题”**：分隔符、引号、换行和编码都可能变化；当前统一使用 UTF-8，部分界面导出带 BOM。
- **“JSON 会自动验证字段类型和范围”**：JSON 只描述结构，不执行 schema 校验；读取方必须自己检查。
- **“JSON 是加密格式”**：不是；任何人都能读取和修改明文 JSON。
- **“CSV 的 SHA-256 能证明数据真实”**：哈希只能检查字节是否变化，不能证明数据来源或金融结论正确。
- **“所有 CSV 导出编码完全相同”**：实验归档 CSV 是 UTF-8 字节；部分界面下载使用 UTF-8 BOM，方便 Excel 识别中文。
- **“CSV 能无损保存所有 pandas 类型”**：时间、缺失值、浮点精度和索引需要明确参数；当前读取使用 `parse_dates` 和 `float_precision="round_trip"`。

## 软件实践

### 在 Quant Lab 哪里出现

- `storage._csv_bytes` 使用 `frame.to_csv(index=False).encode("utf-8")` 生成实验快照字节。
- 实验保存时，原始成交价格和信号价格分别生成两份 CSV，计算 SHA-256，再用 `zlib.compress` 存入 SQLite 的 `raw_csv`、`signal_csv` BLOB。
- 读取时先 `zlib.decompress`，核对 SHA-256，再用 `pd.read_csv(..., parse_dates=["date"], float_precision="round_trip")`。
- 策略、回测配置、指标和训练比例保存为 JSON 文本；`assumptions.json` 写入导出的 ZIP。
- ZIP 研究包包含 `report.md`、`raw_history.csv`、`signal_history.csv`、`assumptions.json`。
- 市场页“导出 CSV”、回测订单“导出订单 CSV”、AI 报告和研究报告使用 `utf-8-sig` 编码，带 BOM。

### 输入、输出和单位

- CSV 的列名和值来自 DataFrame；`index=False` 表示不保存行号索引。
- 日期列保存为文本，读取时用 `parse_dates=["date"]` 转回 `Timestamp`。
- 价格、成交量、成交额的单位与原始表一致；CSV 本身不携带单位元数据。
- JSON 保存字符串、数字、布尔、`null`、数组和对象；时间通常转为字符串。
- 完整 SHA-256：64 个十六进制字符，对应 256 位；`audit_id`：前 16 个十六进制字符，对应 64 位。
- ZIP 是容器，不改变内部文件的编码。

### 结果应该怎么读

- 打开 CSV 时先确认列名、日期格式和小数点；不要用本地化分隔符直接覆盖原文件。
- 看到 BOM 时，Excel 通常能正确识别 UTF-8；用程序读取时应使用 `utf-8-sig` 或允许 BOM。
- 看到 JSON 中的 `null` 时，它对应 Python 的 `None`；不是字符串 `"null"`。
- 看到 JSON 数字 `3.0` 与 `3` 时，类型可能不同；不要假设所有数字都是浮点。
- 看到 SHA-256 不一致时，说明字节被修改或序列化方式不同；不要继续复算。
- 看到 ZIP 中的 `assumptions.json` 时，它记录策略、成本、训练比例、来源、复权和指纹；它不是收益承诺。

### 当前软件边界

- 实验归档 CSV 使用 UTF-8 无 BOM；部分界面下载使用 UTF-8 BOM；两者不完全相同。
- JSON 不是加密、数字签名、身份认证或自动 schema 验证；没有第三方存证。
- 当前没有 CSV schema 版本号、列类型清单或通用迁移器。
- CSV 浮点往返依赖 pandas 和 Python 的序列化行为；跨版本读取需要复核。
- 当前不导出 Excel、Parquet、数据库 dump 或二进制行情格式。
- 文章中的 CSV/JSON 示例是通用 Python，不代表软件提供任意文件编辑或导入功能。

## 专业原理

### 正式定义

CSV（Comma-Separated Values）是用分隔符分隔字段的文本表格格式。常见变体包括：

- 分隔符：逗号、分号、制表符；
- 引号：字段含分隔符、引号或换行时使用引号；
- 编码：UTF-8、UTF-8 BOM、GBK 等；
- 表头：第一行是否为列名；
- 缺失值：空字符串、`NA`、`NaN` 等约定。

JSON（JavaScript Object Notation）是键值文本格式，支持对象、数组、字符串、数字、布尔和 `null`。JSON 标准不允许注释和尾随逗号；Python 的 `json` 模块默认可以输出 `NaN`/`Infinity`，但这不是严格 JSON，跨语言读取时需注意。

### 公式与符号

实验指纹使用 CSV 字节：

`raw_sha256 = SHA256(UTF8(CSV(raw_history, index=False)))`

`signal_sha256 = SHA256(UTF8(CSV(signal_history, index=False)))`

`audit_id = first16hex(SHA256(raw_csv_bytes ‖ signal_csv_bytes ‖ repr(spec) ‖ repr(config) ‖ str(train_fraction)))`

JSON 假设文件包含：

`{strategy, config, train_fraction, source, adjustment, market, symbol, company_name, audit_id, raw_sha256, signal_sha256}`

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
import hashlib
import pandas as pd

frame = pd.DataFrame({
    "date": ["2026-10-20", "2026-10-21"],
    "close": [10.0, 11.0],
})
csv_bytes = frame.to_csv(index=False).encode("utf-8")
print(csv_bytes.decode("utf-8"))
print(hashlib.sha256(csv_bytes).hexdigest()[:16])
```

CSV 文本为：

```text
date,close
2026-10-20,10.0
2026-10-21,11.0
```

文本包含表头、两行数据和末尾换行；哈希针对这些字节计算。若改成 `index=True`，会多出一列行号，字节和哈希都会变化。

JSON 示例：

```python
import json

payload = {
    "market": "A 股",
    "symbol": "600519",
    "commission_bps": 3.0,
    "limit_pct": 0.10,
    "note": None,
}
text = json.dumps(payload, ensure_ascii=False, indent=2)
```

`note` 保存为 `null`；`commission_bps` 是数字，不是字符串。JSON 解析后仍需检查 `commission_bps` 是否为非负有限数，不能只因为格式正确就认为参数有效。

### 前提假设

- CSV 的编码、分隔符、表头和日期格式在写入与读取之间保持一致。
- 浮点数按 round-trip 方式读取，减少精度损失；但不承诺十进制精确。
- JSON 字段名和类型在当前代码版本内稳定；跨版本变更需要兼容策略。
- 哈希针对原始字节，不是针对解析后的 DataFrame；重新序列化可能得到不同字节。
- 文件访问权限由操作系统管理；CSV/JSON 本身不提供访问控制。

### 边界情况

- BOM：UTF-8 BOM 会让某些读取器把首列名读成 `﻿date`；应使用 `utf-8-sig` 或去除 BOM。
- 分隔符冲突：字段内含逗号时必须加引号；手工编辑容易破坏结构。
- 换行：字段内含换行时 CSV 仍可表示，但简单按行读取会出错。
- 缺失值：空字符串、`NaN`、`null` 的语义不同；读取后要显式处理。
- 浮点格式：不同 pandas 版本或 `float_format` 可能改变文本；哈希随之变化。
- 时区：CSV 中的日期通常无时区；JSON 中的时间字符串可能带偏移；不要混读。
- JSON 数字精度：极大或极小数字可能丢失精度；金额和价格应确认格式。
- JSON 非标准值：Python 可能输出 `NaN`，严格 JSON 解析器可能拒绝。
- 手工修改：任何有文件权限的人都能改 CSV/JSON；哈希只能发现变化，不能阻止修改。
- 大文件：一次性读入内存可能造成压力；当前实验快照规模受研究范围限制，没有流式导出。

## 相关知识

### 前置概念

- `pandas_series_and_dataframe`：CSV 的主要来源是 DataFrame。
- `python_collections`：JSON 对象对应字典，数组对应列表。

### 相关词条

- `sqlite_and_transactions` SQLite 与事务
- `hash_and_fingerprint` 哈希与指纹
- `reproducibility_and_audit` 可复现性与审计
- `missing_data` 缺失数据

### 建议下一篇

`sqlite_and_transactions`：了解这些序列化字节如何写入数据库并保证提交或回滚。

## 参考资料

- `S008` Python 3 文档：`json` 模块、编码和文件 I/O；页面未联网复核。
- `S009` pandas 文档：`to_csv`、`read_csv`、`parse_dates` 和 `float_precision`；页面未联网复核。
- `P004` docs/DATA.md：UTF-8、CSV 导出和数据校验的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
