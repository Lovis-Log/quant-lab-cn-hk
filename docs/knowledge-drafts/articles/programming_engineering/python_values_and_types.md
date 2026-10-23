---
id: python_values_and_types
title: Python 值与类型
english_title: Python Values and Types
aliases: [Python 类型, 值类型, int, float, str, bool, None, 数据类型]
category: programming_engineering
software_status: implemented
related_modules: [代码库, 数据校验, 回测, UI]
prerequisites: []
related_articles: [python_control_flow, python_functions, python_collections, type_hints_and_dataclasses]
source_ids: [S008, P003]
last_verified: 2026-10-23
---

# Python 值与类型（Python Values and Types）

## 快速理解

### 一句话解释

Python 里每个值都有类型：`int` 是整数，`float` 是浮点数，`str` 是文本，`bool` 只有真和假，`None` 表示“没有值”；Quant Lab 用这些类型分别表示股数、价格、代码、条件和不存在的指标。

### 它解决什么问题

类型决定一个值能做什么运算、应该配什么单位。把价格 `10.5` 当成股数、把百分数 `1` 当成 `1%`、把布尔值 `True` 当成数值 `1`，都会让计算在语法上通过、在金融含义上出错。

### 最常见的误解

- **“`bool` 是独立类型，不会参与数值运算”**：`bool` 是 `int` 的子类，`True + True` 等于 `2`，`True == 1` 为真。
- **“浮点数能精确表示十进制小数”**：`0.1 + 0.2` 的结果不是精确的 `0.3`；金融展示可以格式化，但不能假设二进制浮点没有舍入。
- **“代码里写 1 就是 1%”**：程序中的百分数通常写成小数，`1%` 是 `0.01`，`3` 个基点（bps）是 `0.0003`。
- **“`None`、`NaN` 和 `0` 是同一件事”**：`None` 表示缺失对象，`NaN` 是浮点缺失值，`0` 是一个有效数值。
- **“pandas 的 `Timestamp` 就是字符串日期”**：`Timestamp` 支持日期比较和索引对齐；字符串只按文本规则比较。
- **“所有数值都是 Python 原生 `float`”**：pandas 和 NumPy 会返回 `numpy.float64`、`numpy.int64` 等标量，它们通常能与原生数值互操作，但类型并不完全相同。

## 软件实践

### 在 Quant Lab 哪里出现

- `normalize_symbol` 接收字符串代码，返回规范化的字符串代码。
- `BacktestConfig` 的资金、佣金、滑点、涨跌停比例使用浮点数；`lot_size` 使用整数。
- 策略信号由布尔条件生成，再转成整数 `0` 或 `1`。
- `PerformanceStats` 的 `sharpe` 和 `annualized_volatility` 允许 `None`，表示当前样本不足以计算或分母为零。
- 历史行情的 `date` 是 pandas `Timestamp`，`open/high/low/close/volume/amount` 是数值列。
- UI 控件返回的数值进入这些配置对象前，仍应满足各自的业务校验。

### 输入、输出和单位

| 值 | 项目中的典型类型 | 单位或含义 |
| --- | --- | --- |
| 股票代码 | `str` | A 股六位数字、港股五位数字；不是数值，不能做加减 |
| 初始资金 | `float` 或整数输入 | CNY 或 HKD；不同币种不能直接相加 |
| 交易单位 | `int` | 股/手对应的整数股数；当前回测按整手买入 |
| 收盘价 | `float` | 每股价格，CNY/股或 HKD/股 |
| 成交量 | `float` 或 `int` | 股数，不是金额 |
| 成交额 | `float` | 与价格同币种的金额 |
| 简单收益率 | `float` | 小数；`0.01` 表示 1% |
| 佣金/滑点 | `float` | 基点（bps）；`3.0` 表示万分之三 |
| 信号 | `int` | `0` 或 `1`；不是概率 |
| 指标缺失 | `None` 或 `NaN` | “没有有效值”，不是 0 |

### 结果应该怎么读

- 看到 `0.01` 时先确认它是收益率、比例还是价格；收益率和比例通常是小数字，价格通常不是。
- 看到 `3.0` 的佣金参数时，要结合字段名和除以 `10000` 的公式，不能把它读成 3 元或 3%。
- 看到 `None` 时不要把它当成 0；它表示当前无法计算，例如零波动下的夏普比率。
- 看到 `NaN` 时不要直接参与比较；`NaN == NaN` 为假，应该用 `isna()` 或 `np.isfinite()` 检查。
- 看到 `Timestamp` 时，它表示交易日或带时区的时间点；要与字符串日期区分。

### 当前软件边界

- 软件使用 Python 原生数值、字符串和 pandas/NumPy 类型，没有引入 `Decimal` 作为价格或金额的统一类型。
- 不同币种不会自动换算；CNY 与 HKD 的金额不能直接相加。
- 当前界面不是 Python 控制台，不提供任意代码执行，也不能让用户输入 Python 表达式参与计算。
- 参数校验由各配置对象和函数完成；不能因为 Python 允许某种运算，就认为该运算具有金融意义。

## 专业原理

### 正式定义

Python 的值可以按类型分类。常用类型包括：

- `int`：任意精度整数，例如 `100`、`-3`。
- `float`：双精度二进制浮点数，例如 `10.5`、`0.01`。
- `str`：Unicode 文本，例如 `"600519"`。
- `bool`：`True` 或 `False`；它是 `int` 的子类。
- `NoneType`：只有一个值 `None`，表示缺失对象。
- `datetime.date`、`datetime.datetime`、`pandas.Timestamp`：日期或时间点。
- `numpy.float64`、`numpy.int64`：NumPy 标量；`pandas` 的缺失数值常用 `NaN`。

### 公式与符号

百分数、基点和收益率的换算：

- `1% = 0.01`；
- `1 bp = 0.0001`；
- `3 bps = 3 / 10000 = 0.0003`；
- 简单收益率 `r_t = P_t / P_{t-1} - 1`，结果是小数。

单笔佣金（当前项目公式）：

`fee = max(min_commission, notional × commission_bps / 10000) + notional × tax_bps / 10000`

其中 `notional` 是成交金额，`commission_bps` 和 `tax_bps` 以基点为单位。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
price = 10.5          # float，价格
lots = 3              # int，交易单位数量
shares = lots * 100   # int，股数
rate = 0.01           # float，1%
is_up = price > 10.0  # bool
missing = None        # 缺失指标
```

计算：

- `price * shares = 10.5 × 300 = 3150.0`，单位是每股价格乘股数，即金额；
- `0.01` 表示 1%，不是 1；
- `is_up` 是 `True`，参与加法时会变成 `1`。

浮点表示示例：

```python
0.1 + 0.2 == 0.3      # False
0.1 + 0.2             # 0.30000000000000004
```

这不是 Quant Lab 的计算错误，而是二进制浮点的表示结果。比较浮点数时，应使用容差或按业务规则四舍五入，而不是直接要求完全相等。

佣金示例：

- 成交额 `10,000`，佣金 3 bps：`10,000 × 3 / 10,000 = 3`，低于最低佣金 5，收取 `5`；
- 成交额 `100,000`，佣金 3 bps：`100,000 × 3 / 10,000 = 30`，高于最低佣金 5，收取 `30`；
- 若卖出附加费 5 bps：`100,000 × 5 / 10,000 = 50`，总费用 `30 + 50 = 80`。

### 前提假设

- 价格、成交额和收益率使用二进制浮点；不承诺十进制精确运算。
- 金额的币种由市场决定，不能只从数值大小推断。
- 收益率以小数存储；显示为百分数时再乘 100。
- `None` 和 `NaN` 都表示缺失，但适用对象不同；不能统一替换为 0。
- 布尔值可以用作条件，但在需要数值的金融参数中应显式拒绝，避免 `True` 被当作 `1`。

### 边界情况

- `bool` 是 `int` 的子类：`isinstance(True, int)` 为 `True`。因此参数校验不能只检查“是不是数字”，还要检查“是不是布尔值”。
- `math.isfinite(True)` 返回 `True`；仅用有限性检查无法排除布尔值。当前 UI 的数值控件不产生布尔值，但自定义校验仍应明确拒绝。
- `None` 不能参与算术；`None + 1` 会抛出 `TypeError`。
- `NaN` 是浮点数，`NaN == NaN` 为假；`bool(float("nan"))` 为真，不能用简单的真值判断检查缺失。
- 字符串数字 `"10"` 与数值 `10` 不相等，也不会自动转成数值；进入计算前必须显式转换。
- 整数除法 `/` 返回浮点数；股数等必须是整数的量应使用 `//` 或显式转换，并检查余数。
- 不同币种的价格、金额不能直接相加；代码层面相加不会报错，但金融含义错误。
- pandas 的 `Timestamp` 与带时区时间不能随意混用；无时区与有时区的时间比较可能报错。

## 相关知识

### 前置概念

- 无。本文是 Python 数据类型的基础。

### 相关词条

- `python_control_flow` 控制流
- `python_functions` 函数
- `python_collections` 容器
- `type_hints_and_dataclasses` 类型注解与数据类

### 建议下一篇

`python_control_flow`：了解条件、循环和早返回如何根据这些值改变程序路径。

## 参考资料

- `S008` Python 3 文档：内置类型、布尔类型、浮点数和 `None` 的语言定义；页面未联网复核。
- `P003` docs/METHODOLOGY.md：收益率、基点和交易费用的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
