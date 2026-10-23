---
id: pandas_series_and_dataframe
title: pandas Series 与 DataFrame
english_title: pandas Series and DataFrame
aliases: [pandas, Series, DataFrame, 数据表, 索引, 列, dtype]
category: programming_engineering
software_status: implemented
related_modules: [市场数据, 数据校验, 指标, 统计, 组合, 存储]
prerequisites: [python_collections, python_values_and_types]
related_articles: [numpy_arrays, datetime_and_index, missing_data, rolling_window]
source_ids: [S009, A011, P003]
last_verified: 2026-10-23
---

# pandas Series 与 DataFrame（pandas Series and DataFrame）

## 快速理解

### 一句话解释

Series 是带索引的一列数据，DataFrame 是带索引和多列名的表格；Quant Lab 用 DataFrame 保存行情，用 Series 保存收盘价、收益率、信号和权重。

### 它解决什么问题

行情数据有日期、开盘、最高、最低、收盘、成交量和成交额，列名比位置更重要。pandas 提供按列名选择、按日期索引、向量化计算、缺失值处理、滚动窗口和表连接，让研究者能用接近表格的方式表达计算。

### 最常见的误解

- **“DataFrame 只是二维列表”**：它有列名、索引、dtype 和对齐规则；行序和索引不是一回事。
- **“赋值一定修改原表”**：链式索引可能返回视图或副本，行为不确定；修改前应明确使用 `.loc` 或 `.copy()`。
- **“按索引运算会自动按行号对齐”**：pandas 按索引标签对齐，不是按位置；日期错位会产生 NaN。
- **“缺失值会自动变成 0”**：不会；NaN 会传播，除非显式填充或删除。
- **“`pct_change` 的第一行也是有效收益率”**：第一行没有前值，通常是 NaN。
- **“DataFrame 是持久化格式”**：它主要在内存中使用；保存需要 CSV、JSON、SQLite 或其他序列化方式。

## 软件实践

### 在 Quant Lab 哪里出现

- `clean_stock_history` 接收原始 DataFrame，选择统一列、转换日期和数值、过滤区间、排序并校验。
- `HistoryBundle.frame` 保存历史日线表；`data` 的缓存返回 `frame.copy(deep=True)`，避免调用者修改缓存原值。
- `strategy.build_signals` 从 `date` 和 `close` 列生成均线与信号列。
- `metrics.performance_stats` 接收净值 Series，计算收益率、波动率和回撤。
- `portfolio.align_closes` 把每只股票的 `date` 设为索引，按日期内连接成收盘价表。
- `statistics.supervised_frame` 生成特征列和标签列，再删除含缺失的行。
- `storage.save_experiment` 把行情 DataFrame 转成 CSV 字节保存。

### 输入、输出和单位

- 行情 DataFrame 的列包括 `date`、`open`、`high`、`low`、`close`、`volume`、`amount`。
- `date` 是日期列；价格是每股价格；`volume` 是股数；`amount` 是金额。
- Series 的名称可能表示列含义，例如 `close`、`equity`、`return_1`；名称不是单位。
- 布尔 Series 用于筛选，例如 `close > moving_average`；结果是同索引的布尔序列。
- 索引通常是整数行号或日期；日期索引用于对齐，整数索引用于行位置。

### 结果应该怎么读

- 先看列名和索引，再看数值；列名决定单位，索引决定对齐方式。
- 看到 NaN 时，先判断是预热、缺失交易日、连接造成还是数据错误。
- 看到行数减少时，检查 `dropna()`、日期过滤或滚动预热；不要假设数据源少给了行。
- 看到两张表相加出现大量 NaN 时，检查索引是否一致。
- 看到 `SettingWithCopyWarning` 时，说明修改可能没有写回原表；应使用明确的 `.loc` 或 `.copy()`。

### 当前软件边界

- DataFrame 是核心内存表格，但不是持久化格式；实验保存用 CSV 字节，数据库用 BLOB。
- 项目没有实现通用 ETL 框架、分布式 DataFrame 或数据库下推计算。
- 当前界面不提供任意 pandas 表达式输入；表格和筛选由代码定义。
- pandas 版本变化可能影响默认行为；项目对关键调用显式写出参数，但不能保证所有默认值永远不变。
- 文章中的 DataFrame 示例是通用 Python，不代表软件新增了数据编辑或查询功能。

## 专业原理

### 正式定义

`pandas.Series` 是一维带标签数组，包含值数组和索引。`pandas.DataFrame` 是二维带标签表格，包含列、索引和每列的 dtype。DataFrame 可以看作共享同一索引的 Series 集合。

常用操作：

- 选择列：`frame["close"]` 返回 Series；
- 按条件筛选：`frame.loc[frame["close"] > 10]`；
- 新增列：`frame["signal"] = ...`；
- 排序：`frame.sort_values("date")`；
- 设置索引：`frame.set_index("date")`；
- 复制：`frame.copy(deep=True)`；
- 删除缺失：`frame.dropna()`。

### 公式与符号

以收盘价收益率为例：

`r_t = close_t / close_{t-1} - 1`

pandas 的 `close.pct_change()` 对每个位置使用前一行；第一行没有前值，结果为 NaN。

滚动均值：

`MA_N(t) = mean(close_{t-N+1}, ..., close_t)`

由 `close.rolling(N).mean()` 生成；不足 N 行时为 NaN。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
import pandas as pd

frame = pd.DataFrame({
    "date": pd.to_datetime(["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22"]),
    "close": [10.0, 11.0, 10.5, 12.0],
})
frame["return_1"] = frame["close"].pct_change()
filtered = frame.loc[frame["close"] > 10.5]
```

计算：

- 行数 4；
- `return_1` 第一行 NaN；
- 第二行 `11/10 - 1 = 0.10`；
- 第三行 `10.5/11 - 1 ≈ -0.04545`；
- 第四行 `12/10.5 - 1 ≈ 0.14286`；
- `filtered` 只保留收盘价大于 10.5 的行，即第四行。

复制示例：

```python
cached = frame.copy(deep=True)
cached.loc[0, "close"] = 99.0
```

修改 `cached` 不会改变 `frame` 的第一行收盘价；这就是历史缓存返回深拷贝的原因。

### 前提假设

- 列名和索引含义明确；同一列内的单位一致。
- 日期索引唯一且升序；重复日期会导致对齐和滚动结果不可靠。
- 缺失值用 NaN 表示，并在进入计算前按业务规则处理。
- 运算按索引标签对齐；需要按位置运算时使用 `.iloc` 或先重置索引。
- DataFrame 的 dtype 足以表示数据；整数列插入 NaN 可能自动变为浮点列。

### 边界情况

- 空 DataFrame：列可能存在但没有行；部分函数返回空表，部分函数抛出“没有可计算交易日”。
- 索引重复：`set_index` 后可能出现重复标签，连接和对齐会膨胀或报错；项目在清洗阶段拒绝重复日期。
- 索引未排序：滚动和 `pct_change` 按当前行序计算；应先按日期排序。
- 链式赋值：`frame[frame["close"] > 10]["signal"] = 1` 可能只修改临时副本；应使用 `.loc`。
- 列缺失：`frame["missing"]` 抛出 `KeyError`；清洗函数会先检查必需列。
- dtype 变化：整数列加入 NaN 后变为浮点；不要把 dtype 当作业务类型保证。
- 深拷贝与浅拷贝：`copy(deep=True)` 复制数据；浅拷贝可能共享底层数组。
- 不同币种或不同复权口径的表直接拼接：语法可行，金融含义错误。

## 相关知识

### 前置概念

- `python_collections`：DataFrame 不是普通字典，但列选择返回类似序列的对象。
- `python_values_and_types`：列有 dtype，值有单位。

### 相关词条

- `numpy_arrays` NumPy 数组
- `datetime_and_index` 日期时间与索引
- `missing_data` 缺失数据
- `rolling_window` 滚动窗口

### 建议下一篇

`datetime_and_index`：理解日期列、索引和时区如何影响对齐。

## 参考资料

- `S009` pandas 文档：Series、DataFrame、索引、选择和复制；页面未联网复核。
- `A011` McKinney（2010）：pandas 数据结构与统计计算的背景；书目信息待复核。
- `P003` docs/METHODOLOGY.md：行情字段、收益率和滚动窗口的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
