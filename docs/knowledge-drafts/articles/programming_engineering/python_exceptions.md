---
id: python_exceptions
title: Python 异常
english_title: Python Exceptions
aliases: [异常, 错误处理, try, except, raise, DataValidationError, DataUnavailableError]
category: programming_engineering
software_status: implemented
related_modules: [数据校验, 市场数据, 存储, 名称服务, UI]
prerequisites: [python_control_flow, python_functions]
related_articles: [python_control_flow, python_functions, missing_data, automated_testing_git_and_modular_monolith]
source_ids: [S008, P004]
last_verified: 2026-10-23
---

# Python 异常（Python Exceptions）

## 快速理解

### 一句话解释

异常是程序遇到无法继续的情况时发出的明确失败信号；Quant Lab 用异常区分“数据不合格”“上游不可用”“参数错误”，并在界面显示可理解的错误，而不是偷偷换成演示数据。

### 它解决什么问题

金融计算最怕“看起来成功、其实用了错误数据”。异常让校验失败立即停止计算，让调用者决定是显示错误、保留旧值还是回滚事务；它比返回一个魔法数字或空表更容易被发现。

### 最常见的误解

- **“异常都应该被捕获，程序才稳定”**：捕获后不处理会隐藏失败；只有明确知道如何恢复时才捕获。
- **“所有异常都会直接传到用户界面”**：缓存和名称查询会捕获较宽异常，保留旧值并标记失败；不是所有异常都向上传播。
- **“名称查询失败说明股票不存在”**：失败只表示这次资料请求没有成功；不能据此断言退市或不存在。
- **“捕获异常后应该显示原始 traceback 或 API 响应”**：用户提示应简洁可读；traceback 写入日志，原始响应和密钥不进入提示。
- **“`except Exception` 可以捕获所有问题”**：它捕获大多数普通异常，但不包括 `KeyboardInterrupt`、`SystemExit` 等 `BaseException`；捕获范围过宽也会掩盖编程错误。
- **“数据校验失败可以用演示数据补齐”**：当前项目明确拒绝这种做法；失败就是失败。

## 软件实践

### 在 Quant Lab 哪里出现

- `processing.clean_stock_history` 在字段缺失、日期或数值无法解析、出现无穷值、重复交易日、非正价格、负成交量、最高价低于最低价等情况下抛出 `DataValidationError`。
- `data.AKShareProvider.history` 在上游请求失败时记录日志并抛出 `DataUnavailableError`；数据校验错误则原样重新抛出。
- `RefreshCache.get` 捕获加载器异常，保留上次有效值和原成功时间，返回“请求失败”的视图。
- `NameCache.lookup` 捕获名称查询异常，保留旧名称；没有旧值时返回空字符串，界面显示“名称暂不可用”。
- `storage._connect` 在上下文内发生异常时执行 `rollback()`，然后重新抛出。
- UI 只显示异常消息和可操作提示；详细 traceback 写入用户目录下的 `logs/data_errors.log`。

### 输入、输出和单位

- 异常没有金融单位；异常消息描述失败原因和可采取的动作。
- `DataValidationError` 表示“数据已返回，但不能安全解释”。
- `DataUnavailableError` 表示“上游没有返回可用响应”。
- `ValueError` 表示参数或状态不满足函数约定。
- 缓存失败视图包含 `value`（可能是旧值）、`cached`、`age_seconds`、`result`、`attempted_at` 和 `error`。
- 名称失败的错误消息保存在内存字典中，可通过 `NameCache.error` 读取；成功查询会清除该错误。

### 结果应该怎么读

- 看到“历史行情包含重复交易日”时，应检查数据源和查询区间，不要继续用该表计算。
- 看到“历史行情暂时无法获取”时，应检查网络或稍后重试；这不是“今天没有行情”的结论。
- 看到“名称暂不可用”时，价格和回测仍可继续；名称不是证券存在性的证明。
- 看到缓存视图的“请求失败”时，数据可能是上次成功的旧值；要同时看缓存年龄和“数据可能过期”。
- 看到迁移失败时，数据库应回滚到迁移前状态；不应手动删除数据库再重来。

### 当前软件边界

- 不是所有异常都向上传播：缓存、名称查询和证券目录会有意捕获异常并保留旧值。
- 失败不会自动重试无限次；缓存等待有超时，名称失败有冷却时间。
- 用户界面不显示 Python traceback、原始 API 响应、请求头或密钥。
- 异常处理不等于数据质量保证；捕获后保留的旧值仍可能过期。
- 当前没有全局异常监控、告警平台或自动恢复服务。

## 专业原理

### 正式定义

异常是中断正常控制流并向上层传播的对象。`try` 块中抛出的异常会寻找匹配的 `except` 分支；`else` 在无异常时执行；`finally` 无论是否异常都执行。`raise` 主动抛出异常，`raise ... from ...` 保留异常链。

Python 的异常层次以 `BaseException` 为根，常用的 `Exception` 是其子类。`KeyboardInterrupt` 和 `SystemExit` 不继承 `Exception`，通常不应被普通错误处理吞掉。

### 公式与符号

以数据校验为例：

`valid(raw) = 必需列存在 ∧ 日期可解析 ∧ 数值有限 ∧ 日期唯一 ∧ 价格 > 0 ∧ 成交量 ≥ 0 ∧ high ≥ low`

若 `valid(raw)` 为假，函数抛出 `DataValidationError`，不返回部分结果。

缓存失败的保留规则：

- 若存在旧值：`result = (old_value, old_success_time, "请求失败")`；
- 若不存在旧值：`result = None`，调用层抛出 `DataUnavailableError`。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
class DataValidationError(ValueError):
    pass

def require_positive(price):
    if price <= 0:
        raise DataValidationError("价格必须大于零。")
    return price

try:
    value = require_positive(-1)
except DataValidationError as exc:
    print("校验失败：", exc)
else:
    print("价格：", value)
finally:
    print("本次检查结束")
```

执行结果：

- `require_positive(-1)` 抛出 `DataValidationError`；
- `except` 分支打印“校验失败：价格必须大于零。”；
- `else` 不执行；
- `finally` 一定执行，打印“本次检查结束”。

失败保留示例（逻辑示意，不是直接调用项目函数）：

| 场景 | 旧值 | 本次结果 | 用户看到 |
| --- | --- | --- | --- |
| 首次请求成功 | 无 | 新数据 | 正常数据 |
| 后续请求失败 | 有效 | 保留旧值 | 旧数据 + 可能过期 |
| 首次请求失败 | 无 | `None` | 明确失败提示 |
| 缓存未过期 | 有效 | 不请求上游 | 缓存数据 + 缓存年龄 |

### 前提假设

- 异常消息对用户可读，且不包含密钥、完整原始响应或内部路径细节。
- 调用者知道哪些异常可以恢复，哪些必须终止流程。
- 捕获宽泛异常时，必须在结果中保留失败状态，不能把失败伪装成成功。
- 事务内的异常会触发回滚；事务外的副作用（例如已经写出的日志）不会自动撤销。
- 异常链保留原始原因，便于日志排查，但不直接展示给用户。

### 边界情况

- `except Exception` 不会捕获 `KeyboardInterrupt`；用户中断不应被当成数据失败。
- 捕获异常后返回空字符串：调用者必须区分“没有名称”和“名称查询失败”；项目通过单独的 `error` 字典保留失败原因。
- `finally` 中再次抛出异常会覆盖原异常；应避免在清理代码中制造新错误。
- `raise` 不带参数只能在 `except` 块内重新抛出当前异常。
- 捕获异常后不重新抛出，会让上层误以为成功；只有明确设计为“保留旧值”的缓存层才这样做。
- 失败重试可能放大上游压力；当前缓存只在 TTL 到期或手动强制时重试，并有并发合并。
- 数据校验错误与上游不可用是不同问题：前者应检查数据源字段和值，后者应检查网络和服务状态。

## 相关知识

### 前置概念

- `python_control_flow`：`try/except` 也是控制流的一种。
- `python_functions`：函数通过返回值和异常表达结果与失败。

### 相关词条

- `missing_data` 缺失数据
- `data_quality_and_bias` 数据质量与偏差
- `cache_and_freshness` 缓存与新鲜度
- `automated_testing_git_and_modular_monolith` 自动化测试、Git 与模块化单体

### 建议下一篇

`python_modules_and_packages`：了解这些异常和函数如何按模块组织。

## 参考资料

- `S008` Python 3 文档：异常层次、`try/except/else/finally`、`raise` 和异常链；页面未联网复核。
- `P004` docs/DATA.md：数据验证失败、来源回退和不使用演示数据替换真实行情的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
