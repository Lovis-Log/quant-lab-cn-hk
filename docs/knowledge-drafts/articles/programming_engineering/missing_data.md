---
id: missing_data
title: 缺失数据
english_title: Missing Data
aliases: [缺失值, 缺失数据, NaN, None, NaT, dropna, 空值]
category: programming_engineering
software_status: implemented
related_modules: [数据校验, 组合分析, 机器学习, 研究笔记]
prerequisites: [pandas_series_and_dataframe, datetime_and_index]
related_articles: [data_quality_and_bias, pandas_series_and_dataframe, alignment_join_and_merge, returns_and_pct_change]
source_ids: [S009, P004, P003]
last_verified: 2026-10-23
---

# 缺失数据（Missing Data）

## 快速理解

### 一句话解释

缺失数据是“本来应该有的值没有拿到”；Quant Lab 对必需行情字段中的缺失直接报错，对组合只保留共同交易日，对机器学习删除含缺失特征或标签的行，不用演示数据填补。

### 它解决什么问题

缺失值会让收益率、均线、相关性和回归结果悄悄偏移。明确区分“没有这一天的行情”“不是共同交易日”“字段缺失”“成交量为零”，才能选择正确的处理方式，而不是把所有空值都当成 0。

### 最常见的误解

- **“周末和节假日是缺失数据”**：日线数据只包含交易日；周末没有行是正常的，不是缺失。
- **“停牌一定表现为 NaN”**：不同数据源可能省略停牌日、保留零成交量或返回其他值；当前软件不单独建模停牌。
- **“缺失值填 0 最安全”**：价格填 0 会产生无穷或错误的收益率；成交量填 0 会被误解为真实无成交。
- **“`dropna()` 总是删一行”**：默认删除任何含缺失值的行；也可以按列或全部缺失删除。
- **“组合内连接会补齐所有日期”**：内连接只保留共同日期；不共同的日子被排除，不是补值。
- **“机器学习删除缺失行不影响结果”**：删除会减少样本，并可能改变训练/测试区间；当前有 60 行有效样本门槛。

## 软件实践

### 在 Quant Lab 哪里出现

- `clean_stock_history`：必需列缺失、日期或数值无法解析、出现 NaN 或无穷值时报 `DataValidationError`。
- 查询区间内没有行时，返回带列名的空 DataFrame；这是“区间内没有数据”，不是字段缺失。
- `portfolio.align_closes`：按日期内连接各资产收盘价，再 `dropna()`；共同交易日少于 8 天时报错。
- `statistics.supervised_frame`：成交量 0 先替换为 NaN；正负无穷替换为 NaN；最后 `dropna()` 删除含缺失特征或标签的行。
- `statistics.one_sample_return_test`：日收益率至少 3 个有效值，且必须全部有限。
- `backtest.run_backtest`：零成交量不是缺失值，但会作为“无法成交”的原因阻止订单。
- `notes` 和存储层对缺失的可选字段使用空字符串或 `None`，不把缺失当作 0。

### 输入、输出和单位

- 数值缺失通常表示为 `NaN`（浮点）或 `None`（对象）；日期缺失表示为 `NaT`。
- `NaN` 没有单位；它不是 0 股、0 元或 0%。
- 行情必需字段：`date/open/high/low/close/volume/amount`；任一字段不可解析都会报错。
- 组合共同日期：只有所有资产都有有效收盘价的日期才进入收益矩阵。
- 机器学习有效样本：五个特征和标签都必须非缺失。
- 缺失率可以表示为 `missing_count / expected_count`，但当前软件没有单独的缺失率指标。

### 结果应该怎么读

- 看到行情加载报“包含无法解析的日期或数值”时，说明上游数据有缺失或格式异常；不要继续使用。
- 看到组合曲线日期变少时，先检查共同交易日；不是所有资产都在同一天有收盘价。
- 看到机器学习样本数明显少于行情行数时，通常是均线预热、波动率窗口、零成交量和最后一行标签造成的。
- 看到零成交量被拒单时，这是交易假设，不是缺失值处理。
- 看到空 DataFrame 时，先区分“查询区间没有交易日”和“数据源失败”。

### 当前软件边界

- 当前没有通用插值、前向填充、均值填补、回归填补或缺失机制模型。
- 不把失败的真实行情替换为演示数据。
- 不自动补齐停牌日或缺失交易日；滚动窗口按实际行数计算。
- 组合内连接只保留共同日期，不做外连接后填补。
- 机器学习删除含缺失的行，而不是填补；这会减少样本。
- 当前没有单独的缺失率表、缺失模式图或缺失原因分类器。

## 专业原理

### 正式定义

缺失数据指目标变量或字段在应有位置没有可观察值。常见表示：

- `None`：Python 的空对象；
- `NaN`：浮点“非数字”，用于数值缺失；
- `NaT`：pandas 的缺失时间戳；
- 空字符串：文本缺失的一种表示，但可能与合法空文本混淆。

缺失机制常分为：

- 完全随机缺失（MCAR）：缺失与任何变量无关；
- 随机缺失（MAR）：缺失与已观察变量有关；
- 非随机缺失（MNAR）：缺失与未观察值本身有关。

当前软件不估计缺失机制。

### 公式与符号

缺失率：

`missing_rate = missing_count / expected_count`

组合共同日期：

`D_common = D_1 ∩ D_2 ∩ ... ∩ D_n`

组合收益矩阵只使用 `D_common` 中的日期。

机器学习有效样本：

`valid = finite(features) ∧ finite(target)`

含缺失的行被删除，不参与训练或测试。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
import pandas as pd

a = pd.Series([10.0, 11.0, 12.0], index=pd.to_datetime(["2026-10-19", "2026-10-20", "2026-10-21"]))
b = pd.Series([20.0, 21.0, 22.0], index=pd.to_datetime(["2026-10-20", "2026-10-21", "2026-10-22"]))
common = pd.concat([a, b], axis=1, join="inner").dropna()
print(common.index.strftime("%Y-%m-%d").tolist())
```

计算：

- A 的日期是 10-19、10-20、10-21；
- B 的日期是 10-20、10-21、10-22；
- 共同日期是 10-20、10-21，共 2 天；
- 10-19 和 10-22 被排除，不是补值。

缺失行示例：

```python
frame = pd.DataFrame({"x": [1.0, None, 3.0], "y": [None, 2.0, 3.0]})
print(len(frame))          # 3
print(len(frame.dropna())) # 1
```

三行中只有第三行两个字段都非缺失；`dropna()` 后剩 1 行。

### 前提假设

- 缺失值用统一的表示方式，进入计算前已经识别。
- 删除缺失行不会系统性破坏时间顺序；当前机器学习仍按时间排序。
- 内连接保留的共同日期足以支持组合分析；当前要求至少 8 天。
- 零成交量与缺失值不同；是否可成交由回测规则判断。
- 缺失处理不会引入未来信息；删除行不改变剩余行的先后顺序。

### 边界情况

- 全部缺失：`dropna()` 后为空，下游函数报样本不足。
- 单列全部缺失：按行删除会删掉所有行；按列删除会删除整列。
- 价格缺失：不能用 0 填补；当前直接报错。
- 成交量缺失：当前报错；成交量 0 是有效值，但机器学习将其视为缺失。
- 收益率第一行：`pct_change` 天生产生 NaN，不是数据源缺失；随后通常 `dropna()`。
- 均线预热：前 N−1 行为 NaN，是窗口不足，不是数据缺失。
- 最后一行标签：`shift(-1)` 使最后一行标签缺失，必须删除；这不是数据源错误。
- 停牌：可能表现为缺行、零成交量或其他形式；当前没有统一停牌标记。
- 不同市场交易日历不同：共同日期可能明显少于单个资产的日期数。
- 外连接：会引入 NaN 行；当前组合不使用外连接填补。
- `NaN` 在条件判断中为真：不要用 `if value:` 检查缺失；应使用 `pd.isna` 或 `np.isfinite`。

## 相关知识

### 前置概念

- `pandas_series_and_dataframe`：缺失值存在于 Series 和 DataFrame 中。
- `datetime_and_index`：日期索引决定连接和对齐。

### 相关词条

- `data_quality_and_bias` 数据质量与偏差
- `alignment_join_and_merge` 对齐、连接与合并
- `returns_and_pct_change` 收益率与 `pct_change`
- `features_and_targets` 特征与标签

### 建议下一篇

`returns_and_pct_change`：理解收益率计算为什么会产生第一行缺失值。

## 参考资料

- `S009` pandas 文档：缺失值表示、`dropna`、索引对齐和连接；页面未联网复核。
- `P004` docs/DATA.md：字段验证、空区间和不使用演示数据替换真实行情的口径。
- `P003` docs/METHODOLOGY.md：组合共同日期和机器学习样本处理口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
