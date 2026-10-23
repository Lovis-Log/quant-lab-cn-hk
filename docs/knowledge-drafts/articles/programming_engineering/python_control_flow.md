---
id: python_control_flow
title: Python 控制流
english_title: Python Control Flow
aliases: [控制流, 条件分支, 循环, if, elif, for, while, early return]
category: programming_engineering
software_status: implemented
related_modules: [策略, 回测, 市场数据, 存储]
prerequisites: [python_values_and_types]
related_articles: [python_values_and_types, python_functions, python_exceptions, python_collections]
source_ids: [S008, P003]
last_verified: 2026-10-23
---

# Python 控制流（Python Control Flow）

## 快速理解

### 一句话解释

控制流决定程序“先做什么、什么时候重复、什么情况下提前结束”；Quant Lab 用 `if/elif` 选择策略条件，用 `for` 逐日推进回测，用 `while` 调整买入手数，用早返回跳过不必要的计算。

### 它解决什么问题

同一段程序需要根据数据状态走不同路径：有持仓才考虑卖出，没有持仓才考虑买入；缓存未过期就直接返回，过期才请求上游；迁移版本已是最新就不重复执行。控制流把这些业务规则写成可读的分支和循环。

### 最常见的误解

- **“`if` 只判断 `True` 和 `False`”**：Python 会把空容器、`0`、`""`、`None` 等当作假；但 `NaN` 是真值，不能靠真值判断缺失。
- **“`elif` 会继续检查后面的条件”**：`if/elif` 命中一个分支后就跳过同链其余分支。
- **“`for` 循环里的列表可以在迭代时随意增删”**：迭代时修改容器可能导致跳过元素或行为混乱；项目通常生成新列表。
- **“`while` 一定会自己结束”**：循环变量必须向终止条件推进；否则会无限循环。
- **“早返回会让代码不完整”**：早返回是常见写法，用于在前提不满足时立即结束，减少嵌套。
- **“向量化计算不需要控制流”**：pandas 表达式内部仍有条件逻辑；回测的逐日状态推进通常需要显式循环。

## 软件实践

### 在 Quant Lab 哪里出现

- 策略信号：`strategy.py` 用 `if/elif/else` 在 `single_ma`、`dual_ma`、`trend` 三种条件间选择。
- 回测：`backtest.py` 用 `for i in range(len(raw_history))` 逐日推进，用 `if/elif` 判断买入、卖出和拒单原因。
- 买入数量：`while lots > 0` 逐手减少，直到成交额加费用不超过现金。
- 缓存：`refresh.py` 在 TTL 未过期时早返回缓存，避免请求上游。
- 迁移：`migrations.py` 在数据库版本等于当前版本时早返回，在版本高于支持版本时抛出错误。
- 名称查询：`names.py` 在冷却期内直接返回旧名称或空字符串，不重复请求。

### 输入、输出和单位

- 条件输入是布尔表达式，例如“收盘价大于长均线”“缓存年龄小于 TTL”。
- 循环输入是序列、日期范围或待处理行；回测按交易日顺序推进。
- 输出是分支结果：`0/1` 信号、`filled/blocked` 订单状态、缓存视图或数据库版本号。
- 控制流本身不改变单位；但它决定某个数值是否参与计算，因此会影响最终金额和收益率的含义。

### 结果应该怎么读

- 信号为 0 可能来自“条件不成立”，也可能来自“均线尚未预热”；要区分原因。
- 订单 `blocked` 可能来自零成交量、涨跌停假设或资金不足；`reason` 字段给出具体分支。
- 缓存返回旧值不代表本次上游请求成功；要同时看 `cached`、`update_result` 和 `update_error`。
- 迁移没有执行不代表失败；版本已是最新时会直接返回。
- 回测循环按行推进，前一行信号影响下一行成交；不能把行序打乱后得到同样的结果。

### 当前软件边界

- 控制流是程序内部逻辑，不是用户可编辑的规则引擎；界面不提供任意 `if/else` 或脚本输入。
- 回测的分支是固定的只做多规则：有信号且空仓才买入，无信号且持仓才卖出；不做空、不加杠杆。
- 循环按日线行推进，不模拟盘中多笔订单、队列或逐笔成交。
- 缓存和名称查询的控制流只覆盖当前进程内的请求；不是分布式调度。
- 早返回和异常分支的具体条件以代码为准，不能把文章示例当成新增功能。

## 专业原理

### 正式定义

控制流是程序语句的执行顺序。常用结构包括：

- 条件语句：`if condition:`、`elif condition:`、`else:`；
- 循环语句：`for item in iterable:`、`while condition:`；
- 循环控制：`break` 提前结束循环，`continue` 跳过本次迭代；
- 函数级控制：`return` 提前结束函数，`raise` 抛出异常；
- 布尔运算：`and`、`or`、`not`，采用短路求值。

### 公式与符号

回测的逐日决策可以写成：

`decision_t = signal_{t-1}`

`side_t = buy`，当 `decision_t = 1` 且 `shares_{t-1} = 0`；

`side_t = sell`，当 `decision_t = 0` 且 `shares_{t-1} > 0`；

否则 `side_t = none`。

买入手数的循环条件：

`lots = floor(cash / (fill_price × lot_size))`

当 `lots × lot_size × fill_price + fee > cash` 时，`lots = lots - 1`，直到满足约束或 `lots = 0`。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
cash = 10_000.0
price = 10.0
lot_size = 100
min_commission = 5.0
commission_bps = 3.0

lots = int(cash // (price * lot_size))  # 10
while lots > 0:
    shares = lots * lot_size
    notional = shares * price
    fee = max(min_commission, notional * commission_bps / 10_000)
    if notional + fee <= cash:
        break
    lots -= 1
```

逐轮计算：

- `lots = 10`：`notional = 10 × 100 × 10 = 10,000`，`fee = max(5, 3) = 5`，`10,000 + 5 > 10,000`，不满足；
- `lots = 9`：`notional = 9 × 100 × 10 = 9,000`，`fee = max(5, 2.7) = 5`，`9,000 + 5 ≤ 10,000`，满足，`break`。

最终买入 `900` 股，现金减少 `9,005`。这个例子只演示分支和循环，不包含滑点、税费或涨跌停。

条件分支示例：

| 前一日信号 | 当前持股 | 结果 |
| --- | --- | --- |
| 1 | 0 | 买入分支 |
| 0 | 900 | 卖出分支 |
| 1 | 900 | 不交易 |
| 0 | 0 | 不交易 |

### 前提假设

- 回测按交易日升序推进；当前行的决策只能使用前一行及更早的信号。
- `while` 循环的变量必须单调向终止条件推进；项目通过 `lots -= 1` 保证这一点。
- 条件表达式使用明确的数值比较，不依赖隐式真值转换。
- `break` 只退出当前循环，不退出整个函数。
- 异常分支与正常分支分开处理；失败不应伪装成成功。

### 边界情况

- `lots` 初始为 0：`while` 不执行，订单被标记为资金不足。
- 现金刚好等于成交额加费用：条件 `<=` 成立，可以买入。
- 现金略低于一个交易单位：循环减到 0，买入被拒绝。
- 零成交量：在进入买入数量循环前就被拒单，不会继续计算手数。
- 信号缺失或不是 0/1：回测在开始前校验并报错，不进入逐日循环。
- `NaN` 作为条件是真值；如果数据未校验，可能在错误分支继续执行。项目在进入回测前检查有限值。
- 空 DataFrame：部分函数直接返回空表；另一些函数抛出“没有可计算交易日”的错误。要按具体函数阅读。

## 相关知识

### 前置概念

- `python_values_and_types`：条件表达式和循环变量都依赖值和类型。

### 相关词条

- `python_functions` 函数
- `python_exceptions` 异常
- `python_collections` 容器
- `signal_position_order_trade` 信号、持仓、订单与成交

### 建议下一篇

`python_functions`：把分支和循环封装成可复用、可测试的函数。

## 参考资料

- `S008` Python 3 文档：`if`、`for`、`while`、`break`、`continue` 和布尔运算的语言定义；页面未联网复核。
- `P003` docs/METHODOLOGY.md：回测信号、成交和费用的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
