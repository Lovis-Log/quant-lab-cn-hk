---
id: datetime_and_index
title: 日期时间与索引
english_title: Datetime and Index
aliases: [日期时间, 时间戳, 索引, 时区, Timestamp, UTC, UTC+08:00]
category: programming_engineering
software_status: implemented
related_modules: [市场数据, 存储, UI, 组合分析]
prerequisites: [pandas_series_and_dataframe]
related_articles: [pandas_series_and_dataframe, trading_calendar, timezone_and_session, alignment_join_and_merge]
source_ids: [S009, S008, P002]
last_verified: 2026-10-23
---

# 日期时间与索引（Datetime and Index）

## 快速理解

### 一句话解释

行情里的 `date` 是交易日期，通常是没有时区的 pandas `Timestamp`；`received_at`、`created_at` 是带 UTC 时区的时间点；界面再把它们转换成北京时间 UTC+08:00 显示。

### 它解决什么问题

日期既可能是“哪一天交易”，也可能是“哪一刻收到数据”。把交易日当成精确报价时间，或把本机接收时间当成交易所时间，会让数据溯源和跨市场比较出错。索引则决定两张表按什么对齐。

### 最常见的误解

- **“行情日期就是精确报价时间”**：日线的 `date` 只表示交易日，没有盘中时刻。
- **“`received_at` 是交易所发出数据的时间”**：它是本机收到上游响应的时间，不是交易所报价时间。
- **“所有时间都可以直接相减”**：无时区时间和带时区时间混用可能报错；应先统一时区。
- **“北京时间就是简单加 8 小时，所以不需要时区库”**：当前中国标准时间没有夏令时，但用 `ZoneInfo("Asia/Shanghai")` 表达更清晰，也避免把其他地区规则套进来。
- **“索引只是行号”**：pandas 索引可以是日期标签，参与对齐；行号只是位置。
- **“日期重复没关系，排序后就好”**：重复交易日会让滚动、收益率和连接结果不可靠；项目会拒绝重复日期。

## 软件实践

### 在 Quant Lab 哪里出现

- `processing.clean_stock_history` 用 `pd.to_datetime(..., errors="coerce")` 解析 `date`，再按日期区间过滤和排序。
- `MarketSnapshot.observation_date` 取最后一个交易日的 `date`，类型是 `datetime.date`。
- `AKShareProvider.snapshot` 以 `ZoneInfo("Asia/Shanghai")` 的当天日期作为查询结束日，再取最近 21 天日线。
- `HistoryBundle.received_at` 使用 `datetime.now(timezone.utc)`。
- `storage` 把 `created_at`、`received_at` 保存为 ISO 字符串；报告显示时转换为北京时间。
- `ui_updates.beijing` 把 UTC 时间转换成 `Asia/Shanghai`，格式为 `YYYY-MM-DD HH:MM:SS UTC+08:00`。
- `portfolio.align_closes` 用 `set_index("date")` 把交易日变为索引，再按索引内连接。
- `strategy`、`backtest`、`statistics` 在计算前检查日期唯一且升序。

### 输入、输出和单位

- `date`：交易日，无时区；单位是“日”，不是秒或毫秒。
- `received_at`：带时区的时间点，通常为 UTC；表示本机收到响应的时间。
- `created_at`：实验保存时间，UTC ISO 字符串。
- `observation_date`：最近收盘价对应的交易日，类型为 `date`。
- 索引：日期索引的标签是 `Timestamp`；整数索引的标签是行号。
- 时区偏移：北京时间显示为 `UTC+08:00`；UTC 显示为 `+00:00`。

### 结果应该怎么读

- 看到“行情日期（交易日）”时，只把它当作价格对应的交易日，不要推断盘中成交时刻。
- 看到“上次成功获取时间”时，它是本机收到上游响应的时间，不是交易所时间。
- 看到“缓存年龄”时，它是当前时间与上次成功获取时间的差，不是行情延迟的精确值。
- 看到日期索引时，确认是否唯一、升序；这决定滚动和收益率的方向。
- 看到两个日期序列长度相同但内容不同，不能直接逐行相减；应显式检查日期是否一致。

### 当前软件边界

- 当前只处理日线，不建模盘中交易时段、集合竞价、午休或收市时刻。
- 不提供交易所级时间戳、报价时钟或延迟测量；确切延迟未知。
- 日期索引只包含上游返回的交易日，不补齐周末、节假日或停牌日。
- `received_at` 缺失时显示“未记录”，不会推断为当前时间。
- 旧记录如果没有时区信息，显示函数会按 UTC 解释；这不证明原始时间确实是 UTC。
- 文章中的时区示例是通用 Python，不代表软件提供时区转换工具。

## 专业原理

### 正式定义

- 无时区时间（naive datetime）：只有年月日时分秒，没有 UTC 偏移，无法确定绝对时刻。
- 带时区时间（aware datetime）：带 `tzinfo`，可以转换为其他时区。
- `pandas.Timestamp`：pandas 的时间点类型，可带时区；`DatetimeIndex` 是时间索引。
- 交易日：市场实际开市的日期；日线数据通常每个交易日一行。
- 时间索引对齐：两个带日期索引的对象运算时，按日期标签匹配，而不是按行号。

### 公式与符号

UTC 到北京时间的转换：

`t_Beijing = t_UTC + 8 小时`

北京时间显示格式：

`YYYY-MM-DD HH:MM:SS UTC+08:00`

缓存年龄：

`age = now_UTC - received_at`

其中 `received_at` 必须是带时区时间；否则不能直接与 `now_UTC` 相减。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

received = datetime(2026, 10, 23, 1, 30, tzinfo=timezone.utc)
beijing = received.astimezone(ZoneInfo("Asia/Shanghai"))
print(beijing.isoformat())   # 2026-10-23T09:30:00+08:00
print(beijing.strftime("%Y-%m-%d %H:%M:%S UTC+08:00"))
```

结果：

- UTC `2026-10-23 01:30` 对应北京时间 `2026-10-23 09:30`；
- 偏移为 `+08:00`；
- 这只是时间转换，不表示当天 09:30 有报价，也不表示数据在 09:30 到达。

索引对齐示例：

```python
import pandas as pd

a = pd.Series([10.0, 11.0], index=pd.to_datetime(["2026-10-20", "2026-10-21"]))
b = pd.Series([20.0, 21.0], index=pd.to_datetime(["2026-10-21", "2026-10-22"]))
print((a + b).tolist())   # [nan, 31.0, nan]
```

两个序列只在 `2026-10-21` 有共同索引；其他日期对齐后没有值，结果为 NaN。

### 前提假设

- `date` 表示交易日，不含盘中时刻；同一交易日内可能有多个报价，但日线只保留一个收盘值。
- `received_at` 由本机时钟生成，时钟可能不准确；它不是交易所时间。
- 日期索引唯一且升序；重复或乱序会破坏滚动和收益率。
- 时区转换使用 IANA 时区标识；中国标准时间当前为 UTC+08:00。
- 显示时间与存储时间分开：存储通常用 UTC，显示转换为本地时间。

### 边界情况

- 无时区与带时区时间比较：可能抛出 `TypeError`；应先统一。
- 夏令时：不同市场可能实行夏令时；中国内地和香港当前不实行，但代码不应把“+8”硬编码到所有市场。
- 日期字符串格式不统一：`pd.to_datetime` 可能解析失败；当前代码用 `errors="coerce"` 后检查缺失并报错。
- 重复日期：清洗阶段报错；组合和策略也要求日期唯一。
- 乱序日期：必须先排序；当前清洗和策略检查会拒绝乱序输入。
- 空日期区间：可能返回空 DataFrame；下游函数会提示没有可计算交易日。
- 旧记录无时区：显示函数按 UTC 解释；这是一项兼容假设，不是原始事实。
- 交易日与自然日混用：滚动窗口按行数，不按自然日；两者不可互换。

## 相关知识

### 前置概念

- `pandas_series_and_dataframe`：索引和列是 pandas 表格的基础。

### 相关词条

- `trading_calendar` 交易日历
- `timezone_and_session` 时区与交易时段
- `alignment_join_and_merge` 对齐、连接与合并
- `data_provenance` 数据来源与时间戳

### 建议下一篇

`missing_data`：理解缺失日期、缺失字段和缺失值如何进入计算。

## 参考资料

- `S009` pandas 文档：`Timestamp`、`DatetimeIndex`、时区和对齐；页面未联网复核。
- `S008` Python 3 文档：`datetime`、`timezone` 和 `zoneinfo`；页面未联网复核。
- `P002` ARCHITECTURE.md：UTC 存储、北京时间显示和快照时间语义。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
