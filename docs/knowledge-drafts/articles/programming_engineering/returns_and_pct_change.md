---
id: returns_and_pct_change
title: 收益率与 pct_change
english_title: Returns and pct_change
aliases: [pct_change, 百分比变化, 简单收益率, 收益率序列, percent change]
category: programming_engineering
software_status: implemented
related_modules: [指标, 统计, 组合分析, 机器学习]
prerequisites: [pandas_series_and_dataframe, missing_data]
related_articles: [simple_return, log_return, rolling_window, missing_data]
source_ids: [S009, P003]
last_verified: 2026-10-23
---

# 收益率与 pct_change（Returns and pct_change）

## 快速理解

### 一句话解释

`pct_change` 把相邻两行的值转成“相对前值变化了多少”，公式是 `r_t = P_t / P_{t-1} - 1`；Quant Lab 用它从收盘价生成日收益率，第一行没有前值，所以是 NaN。

### 它解决什么问题

价格的绝对变化不能直接比较：涨 1 元对 10 元股票是 10%，对 1000 元股票是 0.1%。收益率把价格变化归一化，便于跨股票、跨区间比较，也便于计算波动率和相关矩阵。

### 最常见的误解

- **“收益率是价格差”**：`P_t - P_{t-1}` 是价格变化，单位是货币；收益率是比例，没有货币单位。
- **“第一行收益率是 0”**：第一行没有前值，通常是 NaN，随后被删除。
- **“收益率可以直接相加得到累计收益”**：多期简单收益率需要复利相乘，不是直接相加。
- **“`pct_change` 会自动处理所有缺失值”**：缺失值会影响结果；当前项目只在明确需要的地方写 `fill_method=None`。
- **“10% 和 0.1 是同一个显示”**：数值上 10% = 0.1，但代码里写成 10 会表示 1000%。
- **“收益率包含分红”**：价格收益率不自动包含分红、税费或公司行动现金流。

## 软件实践

### 在 Quant Lab 哪里出现

- `metrics.performance_stats` 对净值序列调用 `pct_change().dropna()`，再计算波动率和夏普。
- `statistics.one_sample_return_test` 对收盘价调用 `pct_change().dropna()`，检验平均日收益是否为零。
- `portfolio.analyze_portfolio` 对共同收盘价表调用 `pct_change().dropna()`，生成组合收益矩阵。
- `statistics.supervised_frame` 生成 `return_1 = close.pct_change()`、`return_5 = close.pct_change(5)` 和 `volume_change = volume.pct_change(fill_method=None)`。
- `metrics.simple_price_return` 用首尾收盘价计算区间收益率，不经过 `pct_change`。

### 输入、输出和单位

- 输入是价格或净值序列；价格必须是正的有限数值。
- 输出是小数收益率；`0.01` 表示 1%，显示时可乘 100。
- `pct_change()` 默认与前 1 行比较；`pct_change(5)` 与前 5 行比较。
- 第一行（或前 5 行）没有足够前值，结果为 NaN。
- 收益率没有币种单位；但价格序列的币种仍影响结果的可比性。
- 成交量变化也是比例，但成交量不是价格，不能与价格收益率混为一谈。

### 结果应该怎么读

- 日收益率 `0.02` 表示当天相对前一天上涨 2%，不是上涨 2 元。
- 负收益率 `-0.02` 表示下跌 2%；连续收益不能直接相加。
- 第一行 NaN 是正常的预热，不是数据源缺一天。
- `return_5` 的前 5 行 NaN 表示 5 日变化尚不可计算。
- 价格不变时收益率为 0；价格为零或负时不能使用当前比值模型。
- 组合收益矩阵的日期来自共同收盘日，不是所有资产的全部日期。

### 当前软件边界

- 当前使用简单收益率，不使用对数收益率。
- 价格收益率不包含分红、税费、滑点或公司行动现金流。
- 项目没有统一给所有 `pct_change` 调用写 `fill_method=None`；机器学习中的 `volume_change` 明确使用 `fill_method=None`，价格序列依赖已验证的完整输入。
- 不自动填补缺失价格后再计算收益率；缺失数据先按各自流程处理。
- 不把收益率当作未来收益预测；它只是历史价格变化。
- 文章中的 `pct_change` 示例是通用 pandas，不代表软件提供任意数据查询。

## 专业原理

### 正式定义

简单收益率定义为：

`r_t = P_t / P_{t-1} - 1`

其中 `P_t` 是 t 期价格，`P_{t-1}` 是上一期价格。若价格为 100 和 110，则：

`r = 110 / 100 - 1 = 0.10`，即 10%。

多期累计收益：

`R_cum = ∏_{t=1}^{n}(1 + r_t) - 1 = P_n / P_0 - 1`

简单收益率不是对数收益率；对数收益率为 `ln(P_t / P_{t-1})`，当前软件未实现。

### 公式与符号

- `P_t`：t 期价格或净值；
- `r_t`：t 期简单收益率，小数；
- `n`：收益间隔数；
- `∏`：连乘；
- `pct_change(k)`：与 k 行前的值比较。

第一行：

`r_1 = NaN`，因为没有 `P_0`。

### 可手算的小例子

收盘价：100、110、99。

- 第 1 行：NaN；
- 第 2 行：`110 / 100 - 1 = 0.10`，即 +10%；
- 第 3 行：`99 / 110 - 1 = -0.10`，即 −10%。

注意第 3 行是从 110 跌到 99，跌幅是 `11/110 = 10%`，不是从 100 算的 1%。

累计收益：

`99 / 100 - 1 = -0.01`，即 −1%。

如果用收益率相加会得到 `0.10 + (-0.10) = 0`，与真实的 −1% 不同；这就是复利与直接相加的区别。

通用 Python 示例（不是软件功能）：

```python
import pandas as pd

close = pd.Series([100.0, 110.0, 99.0])
returns = close.pct_change()
print(returns.tolist())
```

结果约为 `[nan, 0.10000000000000009, -0.09999999999999998]`；显示时可格式化为 `+10.00%` 和 `−10.00%`。

### 前提假设

- 价格为正且有限；零价格会导致除零，负价格没有当前比值模型的金融含义。
- 行按时间升序排列；`pct_change` 使用当前行序，不会自动按日期排序。
- 相邻行代表相邻观察期；缺失行不会被自动补齐。
- 收益率使用同一复权口径；不同口径的价格不能混合计算。
- 价格收益率不含分红和费用；总回报需要另外建模。

### 边界情况

- 第一行：NaN；`dropna()` 后样本数变为 `N-1`。
- 前 k 行：`pct_change(k)` 为 NaN；样本数减少 k。
- 价格为零：除零或无穷；当前校验拒绝非正价格。
- 价格缺失：结果为 NaN；不能用 0 填补。
- 价格恒定：收益率为 0；波动率为 0，夏普可能无法计算。
- 极小的前值：收益率可能很大；这不是错误，但需要检查数据质量。
- 复权口径变化：收益率会跳变；应使用同一口径的连续序列。
- 成交量 0：`volume_change` 先替换为 NaN，再 `pct_change(fill_method=None)`；价格收益率不采用同一处理。
- 不同频率：日收益率与月收益率不能直接比较；年化时需要匹配周期数。

## 相关知识

### 前置概念

- `pandas_series_and_dataframe`：`pct_change` 是 Series/DataFrame 方法。
- `missing_data`：第一行 NaN 和缺失值处理。

### 相关词条

- `simple_return` 简单收益率
- `log_return` 对数收益率
- `rolling_window` 滚动窗口
- `volatility` 波动率

### 建议下一篇

`rolling_window`：把日收益率放进滚动窗口，计算波动率和均线。

## 参考资料

- `S009` pandas 文档：`pct_change`、缺失值和索引对齐；页面未联网复核。
- `P003` docs/METHODOLOGY.md：简单收益率、样本标准差和年化口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
