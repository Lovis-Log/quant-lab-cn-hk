---
id: python_functions
title: Python 函数
english_title: Python Functions
aliases: [函数, 参数, 返回值, 纯函数, 副作用, function, pure function]
category: programming_engineering
software_status: implemented
related_modules: [代码库, 回测, 市场数据, 存储]
prerequisites: [python_values_and_types, python_control_flow]
related_articles: [python_modules_and_packages, python_control_flow, type_hints_and_dataclasses, python_exceptions]
source_ids: [S008, P003]
last_verified: 2026-10-23
---

# Python 函数（Python Functions）

## 快速理解

### 一句话解释

函数把一段计算或操作命名、接收输入、返回结果；Quant Lab 用函数区分“只做计算的纯函数”和“会联网、读文件、写数据库的副作用函数”。

### 它解决什么问题

函数让同一套规则只写一次，例如收益率、均线、费用和指纹。调用者只需关心输入和输出，不必重复实现公式；测试也可以针对小样本单独验证函数。

### 最常见的误解

- **“函数一定会返回值”**：没有 `return` 的函数返回 `None`；它可能只产生副作用，例如写日志。
- **“带默认参数的函数每次调用都会重新创建默认值”**：默认值在函数定义时求值一次；可变默认参数会在调用间共享。
- **“纯函数和副作用函数可以随便互换”**：纯函数不联网、不读写文件、不改全局状态；副作用函数失败方式和测试方式都不同。
- **“函数抛异常就说明程序坏了”**：校验失败、数据不可用和参数错误都用异常表达；异常是明确的失败信号。
- **“函数参数名和类型注解会自动校验”**：类型注解主要帮助阅读和静态检查；运行时校验需要显式代码。
- **“函数内部修改列表不会影响调用者”**：列表、字典和 DataFrame 是可变对象；函数可以修改传入对象，除非先复制。

## 软件实践

### 在 Quant Lab 哪里出现

- 纯计算函数：`simple_price_return`、`moving_average`、`_fee`、`performance_stats`。
- 有网络副作用：`AKShareProvider.history`、`NameProvider.lookup`、`fetch_directory`。
- 有文件或数据库副作用：`save_experiment`、`save_security_name`、`_record_failure`、`stage_library`。
- 接收其他函数作为参数：`RefreshCache.get(key, loader, ...)` 把加载逻辑作为 `loader` 传入，缓存层只负责 TTL、合并和失败保留。
- 返回数据类对象：`run_experiment` 返回 `ExperimentResult`，`analyze_portfolio` 返回 `PortfolioAnalysis`。

### 输入、输出和单位

- 纯计算函数的输入是数值、序列或配置对象；输出是同一口径的数值或数据类。
- `simple_price_return(first_close, last_close)` 返回小数收益率；输入价格必须是正的有限数值。
- `moving_average(close, window)` 返回与输入等长的价格序列；单位与收盘价相同。
- `_fee(notional, side, config)` 返回金额；`notional` 和返回值使用同一币种。
- `fetch_history(...)` 返回 `HistoryBundle`，包含行情表、市场、代码、来源、币种、复权、接收时间和缓存状态。
- 副作用函数通常返回 ID、路径或对象；失败时抛出异常或保留旧值，不会伪造成功。

### 结果应该怎么读

- 纯函数的输出只由输入决定；同样的输入应得到同样的输出。
- 副作用函数的输出还取决于网络、文件系统和数据库状态；同一天再次调用可能得到缓存值或失败提示。
- 返回 `None` 不一定是错误：它可能表示“没有值”，例如不足两个价格时的区间收益率。
- 抛出异常时应阅读错误消息，而不是把异常当成空结果。
- 函数返回的 DataFrame 可能是副本，也可能是内部对象；当前历史缓存返回深拷贝，调用者修改不会污染缓存。

### 当前软件边界

- 软件不是 Python 解释器，不向用户提供任意函数定义、导入或执行入口。
- 函数是代码组织方式，不是用户可以配置的策略插件；当前策略只有内置三种。
- 纯计算函数不导入 Streamlit，也不直接读写界面状态。
- 副作用函数没有统一的事务边界；数据库写入通过 `_connect` 的上下文管理器管理，网络请求没有自动重试队列。
- 文章中的通用函数示例只用于解释语言行为，不代表软件新增了接口。

## 专业原理

### 正式定义

函数是带名字的代码块，可以接收位置参数、关键字参数、默认参数和可变参数，并通过 `return` 返回结果。调用函数时，Python 创建局部作用域；函数结束后局部变量通常被释放。

纯函数满足：

1. 相同输入总是产生相同输出；
2. 不修改外部可变状态；
3. 不产生可观察的 I/O 副作用。

副作用包括写文件、写数据库、发网络请求、修改全局变量、打印输出等。

### 公式与符号

以费用函数为例：

`fee(notional, side, config) = max(min_commission, notional × commission_bps / 10000) + notional × tax_bps(side) / 10000`

其中 `tax_bps(buy) = buy_tax_bps`，`tax_bps(sell) = sell_tax_bps`。

区间收益率函数：

`simple_price_return(P_0, P_1) = P_1 / P_0 - 1`

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
def fee(notional, commission_bps=3.0, min_commission=5.0):
    commission = max(min_commission, notional * commission_bps / 10_000)
    return commission

fee(10_000)    # 5.0
fee(100_000)   # 30.0
```

逐步计算：

- `10,000 × 3 / 10,000 = 3`，低于最低佣金 5，返回 `5.0`；
- `100,000 × 3 / 10,000 = 30`，高于最低佣金 5，返回 `30.0`。

这个函数是纯函数：不联网、不写文件，只根据参数返回金额。

副作用示例（通用 Python，不是软件功能）：

```python
def record_failure(path, message):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(message + "\n")
```

这个函数返回 `None`，但它修改了文件；调用两次会追加两行。它不能像纯函数那样只靠输入输出测试，还要检查文件状态和失败处理。

### 前提假设

- 调用者传入的参数满足函数约定；函数内部的显式校验只覆盖已写出的条件。
- 默认参数使用不可变值，例如数字、字符串、`None`；避免用列表或字典作为默认值。
- 纯函数不依赖全局可变状态；副作用函数明确说明其 I/O 行为。
- 异常被视为失败信号；调用者应决定是显示错误、保留旧值还是终止流程。
- 返回的可变对象由调用者决定是否复制；共享对象需要额外的复制约定。

### 边界情况

- 可变默认参数：`def f(items=[])` 的列表会在多次调用间共享，可能累积上一次的结果；应使用 `None` 再在函数内创建新列表。
- 默认值在定义时求值：默认值是对象时，后续修改该对象会影响所有调用。
- 函数没有 `return`：返回 `None`；不要把它与“返回 0”混淆。
- 函数修改传入列表：调用者的列表也会改变；需要保留原值时先复制。
- 函数返回 DataFrame：可能是视图或副本；当前缓存层显式 `copy(deep=True)`，其他函数不一定。
- 递归没有终止条件：会导致递归深度错误；项目主要使用循环，不依赖深递归。
- 异常在函数内部被捕获但不重新抛出：调用者可能看不到失败；缓存和名称查询会有意捕获较宽异常以保留旧值，并在结果中标记失败。
- 函数参数类型错误：Python 不一定在调用时检查；错误可能在函数内部运算时才出现。

## 相关知识

### 前置概念

- `python_values_and_types`：参数和返回值都有类型与单位。
- `python_control_flow`：函数内部使用条件、循环和早返回。

### 相关词条

- `python_modules_and_packages` 模块与包
- `type_hints_and_dataclasses` 类型注解与数据类
- `python_exceptions` 异常
- `automated_testing_git_and_modular_monolith` 自动化测试、Git 与模块化单体

### 建议下一篇

`python_collections`：函数经常接收和返回列表、字典、元组和集合。

## 参考资料

- `S008` Python 3 文档：函数定义、参数、默认值和返回值；页面未联网复核。
- `P003` docs/METHODOLOGY.md：费用和收益函数的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
