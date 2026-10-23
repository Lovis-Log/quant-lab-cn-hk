---
id: python_collections
title: Python 容器
english_title: Python Collections
aliases: [容器, 列表, 字典, 元组, 集合, list, dict, tuple, set]
category: programming_engineering
software_status: implemented
related_modules: [代码库, 市场数据, 回测, 存储]
prerequisites: [python_values_and_types]
related_articles: [python_values_and_types, pandas_series_and_dataframe, csv_and_json, python_functions]
source_ids: [S008, P003]
last_verified: 2026-10-23
---

# Python 容器（Python Collections）

## 快速理解

### 一句话解释

容器把多个值放在一起：`list` 有序可重复，`tuple` 有序不可变，`dict` 用键查找值，`set` 只保留唯一元素但不保证业务顺序。

### 它解决什么问题

程序需要组织多个对象：一组行情列、一组特征名、一个缓存键、一批订单行、一组缺失列。选对容器能表达“是否允许重复”“是否需要顺序”“是否要按键查找”，也能避免把集合的偶然打印顺序误当成业务排序。

### 最常见的误解

- **“`set` 会保留插入顺序”**：`set` 不保证顺序；打印顺序可能随运行、版本和元素变化。需要顺序时应使用 `list`、`tuple` 或对结果排序。
- **“`dict` 是无序的”**：现代 Python 的 `dict` 保留插入顺序；但按键查找仍是主要用途，不应把插入顺序当作金融排序。
- **“`tuple` 完全不可变”**：元组本身不能增删元素，但它可以包含可变对象，例如列表；内部列表仍可修改。
- **“`list` 可以当作字典键”**：列表不可哈希，不能作为 `dict` 的键或 `set` 的元素。
- **“容器里的重复值会被自动去掉”**：只有 `set` 和字典键会去重；`list` 和 `tuple` 保留重复。
- **“`DataFrame` 就是一个大字典”**：DataFrame 有列、索引、dtype 和对齐规则，不能只用字典语义理解。

## 软件实践

### 在 Quant Lab 哪里出现

- `COLUMNS`、`PRICE_COLUMNS`、`FEATURES` 使用元组，表示固定的字段顺序。
- `HistoryCache` 的缓存键是元组 `(market, symbol, start, end, adjustment)`。
- 回测订单和每日净值先收集到 `list[dict]`，再转换成 DataFrame。
- `RefreshCache._entries` 和 `_flight` 使用字典，按键保存缓存条目和并发事件。
- `STRATEGY_NAMES` 使用字典把策略 ID 映射到中文名称。
- 数据清洗用 `set(COLUMNS) - set(raw.columns)` 找出缺失字段，再用 `sorted(...)` 生成稳定错误消息。
- 信号校验用 `set(close_signals.unique()).issubset({0, 1})` 判断取值集合。
- 证券目录用 `rows` 字典按规范代码去重，再按优先代码和代码排序生成目录。

### 输入、输出和单位

- 列表和元组的元素单位由内容决定；容器本身不携带单位。
- 缓存键元组中的 `start`、`end` 是日期，`adjustment` 是复权口径字符串；它们共同决定一次查询。
- 字典的值可以是数据类、DataFrame、缓存视图或错误消息。
- 集合只表示“有哪些值”，不表示顺序、次数或金额。
- 订单列表中的每个字典包含方向、状态、股数、价格、费用和现金余额；这些字段的单位各不相同。

### 结果应该怎么读

- 看到列表顺序时，要确认代码是否显式排序；没有排序的列表顺序只是插入顺序或生成顺序。
- 看到字典时，按键读取比按位置读取可靠；键不存在会抛出 `KeyError`。
- 看到集合时，只把它当作唯一值集合；不要依赖打印顺序做业务判断。
- 看到元组时，可以把它当作不可变的记录或复合键；但内部可变对象仍可能变化。
- 看到 DataFrame 时，按列名和索引读取，不要把它降级成普通字典。

### 当前软件边界

- 容器是代码内部结构，不是用户可编辑的数据表或策略配置界面。
- `set` 用于成员判断和去重，不用于展示有业务顺序的列表；需要展示顺序时，代码会排序或使用列表。
- 当前缓存键只区分市场、规范代码、日期区间和复权方式；不包含用户、账户或进程 ID。
- 当前没有插件注册表、依赖注入容器或跨进程共享字典。
- 文章中的容器示例是通用 Python，不代表软件提供控制台或任意数据结构编辑。

## 专业原理

### 正式定义

- `list`：有序、可变、允许重复的序列。
- `tuple`：有序、不可变、允许重复的序列；元素可哈希时，元组本身可哈希。
- `dict`：键值映射；键唯一且必须可哈希；现代 Python 保留插入顺序。
- `set`：唯一元素的无序集合；元素必须可哈希；支持并集、交集、差集等运算。
- `frozenset`：不可变的集合，可作为字典键。

容器的时间复杂度（平均情况）：

- 列表按下标访问 `O(1)`，按值查找 `O(n)`；
- 字典和集合按键/元素查找平均 `O(1)`；
- 元组按下标访问 `O(1)`。

### 公式与符号

集合差集用于找缺失字段：

`missing = set(required_columns) - set(available_columns)`

缓存键：

`key = (market, normalized_symbol, start, end, adjustment)`

同一组键值对应同一个缓存条目；任一字段不同就是不同查询。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
required = ("date", "open", "high", "low", "close", "volume", "amount")
available = ("date", "open", "high", "low", "close", "volume")
missing = set(required) - set(available)
sorted_missing = sorted(missing)
```

计算：

- `missing = {"amount"}`；
- `sorted(missing) = ["amount"]`；
- 缺失字段数量为 1。

缓存键示例：

```python
key_a = ("A 股", "600519", "2026-01-01", "2026-10-23", "")
key_b = ("港股", "600519", "2026-01-01", "2026-10-23", "")
key_a == key_b   # False
```

两个键的代码文本相同，但市场不同，所以是不同的缓存条目。

去重示例：

```python
values = [0, 1, 1, 0]
unique = set(values)
```

`unique` 的元素是 `{0, 1}`，数量为 2；它不记录原来出现了几次，也不保证打印顺序。

### 前提假设

- 字典键和集合元素可哈希；列表、字典和 DataFrame 不能直接作为键。
- 需要稳定展示顺序时，显式排序或使用有序容器。
- 容器的可变性由代码控制；共享容器可能被多个调用者修改。
- 字典的键比较使用相等性和哈希；自定义对象需要正确的 `__eq__` 和 `__hash__`。
- 容器的嵌套结构不会自动深拷贝。

### 边界情况

- `set()` 创建空集合；`{}` 创建空字典，不是空集合。
- 空列表、空字典、空集合在条件判断中为假；但“空”不等于“缺失”。
- 列表在迭代时增删元素可能跳过元素；需要修改时先复制。
- 元组包含列表时，元组整体不可重新赋值，但内部列表可以 `append`。
- 字典键重复时，后写入的值覆盖前值；不会保留两个条目。
- 集合元素重复时自动去重；丢失了重复次数信息。
- 浮点 `NaN` 作为字典键或集合元素时，相等性行为特殊；不要用 `NaN` 作为业务键。
- 不同币种或不同市场的值放在同一容器里不会自动换算；容器不做金融校验。

## 相关知识

### 前置概念

- `python_values_and_types`：容器元素本身有类型和单位。

### 相关词条

- `pandas_series_and_dataframe` pandas Series 与 DataFrame
- `csv_and_json` CSV 与 JSON
- `python_functions` 函数
- `cache_and_freshness` 缓存与新鲜度

### 建议下一篇

`pandas_series_and_dataframe`：从 Python 容器进入带索引和列名的表格计算。

## 参考资料

- `S008` Python 3 文档：内置容器类型、可变性、哈希性和集合运算；页面未联网复核。
- `P003` docs/METHODOLOGY.md：行情字段和缓存查询的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
