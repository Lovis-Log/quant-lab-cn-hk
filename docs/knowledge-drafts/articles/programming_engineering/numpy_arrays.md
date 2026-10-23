---
id: numpy_arrays
title: NumPy 数组
english_title: NumPy Arrays
aliases: [NumPy, 数组, ndarray, 向量化, 有限值, isfinite]
category: programming_engineering
software_status: implemented
related_modules: [数据校验, 回测, 统计, Quant Academy]
prerequisites: [python_values_and_types, python_collections]
related_articles: [pandas_series_and_dataframe, returns_and_pct_change, rolling_window, missing_data]
source_ids: [S010, A012, P003]
last_verified: 2026-10-23
---

# NumPy 数组（NumPy Arrays）

## 快速理解

### 一句话解释

NumPy 数组是同类型数值组成的多维容器，支持一次对整个数组做运算；Quant Lab 用它检查 NaN 和无穷值、计算年化因子、方向一致率和教学模拟中的正弦曲线。

### 它解决什么问题

逐元素写 Python 循环既慢又啰嗦。数组运算可以一次性检查整列价格是否有限、一次性比较预测方向，代码更短，也更容易在小样本上验证。

### 最常见的误解

- **“`np.isfinite` 只检查 NaN”**：它也检查正无穷和负无穷；三者都返回 `False`。
- **“NumPy 数组能保存任意混合类型”**：常规数组有统一 dtype；混合类型会退化为 `object`，失去数值运算优势。
- **“数组切片一定是副本”**：基本切片通常返回视图，修改视图可能影响原数组；花式索引通常返回副本。
- **“NumPy 是项目的主要持久化格式”**：不是；核心表格主要用 pandas，持久化用 CSV 字节和 SQLite BLOB。
- **“`np.nan` 等于它自己”**：`np.nan == np.nan` 为假；应使用 `np.isnan` 或 `np.isfinite`。
- **“数组运算不会产生缺失值”**：除法、无穷和无效输入都可能产生 `nan` 或 `inf`。

## 软件实践

### 在 Quant Lab 哪里出现

- `processing.clean_stock_history` 把行情数值列转成 NumPy 数组，用 `np.isfinite(...).all()` 拒绝 NaN 和正负无穷。
- `backtest.run_backtest` 检查开盘价、收盘价和成交量是否为有限数值。
- `metrics.performance_stats` 检查净值序列是否有限且为正。
- `statistics.one_sample_return_test` 检查日收益率是否有限。
- `statistics` 用 `np.sqrt(252)` 计算年化波动率，用 `np.mean` 计算方向一致率，用 `np.zeros_like` 生成零收益基线。
- `learning.py` 的 Quant Academy 过拟合课程用 `np.sin` 和 `np.cos` 生成固定教学曲线；这是模拟样本，不是真实行情。

### 输入、输出和单位

- 输入通常是 pandas 列、列表或二维表格转换后的数组。
- 一维数组形状为 `(n,)`；二维数组形状为 `(行数, 列数)`。
- 数值 dtype 常见为 `float64`；布尔检查返回 `bool` 数组。
- 数组本身不携带列名、索引、币种或单位；这些信息由外层 pandas 对象或项目约定保存。
- `np.isfinite` 返回与输入形状相同的布尔数组，不返回单个布尔值；通常再用 `.all()` 或 `.any()` 聚合。

### 结果应该怎么读

- `np.isfinite(array).all()` 为 `True` 表示所有元素都是有限数值；为 `False` 表示至少有一个 NaN 或无穷值。
- `np.isfinite(array).sum()` 表示有限元素的数量；可用于统计缺失规模。
- `np.sqrt(252)` 是年化因子的常数部分，约为 `15.8745`；它不包含资产波动信息。
- 方向一致率 `np.mean((predicted >= 0) == (actual >= 0))` 是比例，范围 0 到 1，不是收益率。
- 数组中的 `nan` 不能直接参与大小比较；比较结果通常为 `False`。

### 当前软件边界

- NumPy 数组不是项目的主要持久化格式；实验快照保存为 CSV 字节，再压缩进 SQLite。
- 项目没有使用 NumPy 做通用线性代数求解、优化器或深度学习。
- 数组运算不携带单位；价格、收益率、成交量混在一个数组里不会自动校验单位。
- `np.sin`/`np.cos` 只出现在固定教学模拟中，不用于真实行情预测。
- 文章中的数组示例是通用 Python，不代表软件向用户提供 NumPy 控制台。

## 专业原理

### 正式定义

NumPy 的 `ndarray` 是同质元素的多维数组，包含：

- `shape`：各维度长度；
- `dtype`：元素类型；
- `strides`：各维度步长；
- 数据缓冲区。

向量化运算对整个数组执行同一操作，通常比 Python 逐元素循环更快。广播（broadcasting）允许不同形状的数组在兼容维度上运算。

### 公式与符号

有限值检查：

`finite_mask_i = isfinite(x_i)`

`all_finite = ∧_i finite_mask_i`

年化波动率：

`σ_ann = std_daily × √252`

方向一致率：

`accuracy = (1/n) × Σ_i 1[sign(ŷ_i) = sign(y_i)]`

当前代码把 0 视为非负方向，因此 `predicted >= 0` 与 `actual >= 0` 同号才算一致。

### 可手算的小例子

通用 Python 示例（不是软件功能）：

```python
import numpy as np

values = np.array([1.0, np.nan, np.inf, -np.inf, 3.0])
mask = np.isfinite(values)
print(mask.tolist())        # [True, False, False, False, True]
print(mask.sum())           # 2
print(np.sqrt(252))         # 15.874507866387544
```

计算：

- 5 个元素中，`1.0` 和 `3.0` 是有限值，共 2 个；
- `NaN`、`inf`、`-inf` 都不是有限值；
- `√252 ≈ 15.8745`。

方向一致率示例：

```python
predicted = np.array([0.01, -0.02, 0.00, 0.03])
actual = np.array([0.02, 0.01, -0.01, 0.00])
agreement = (predicted >= 0) == (actual >= 0)
print(agreement.tolist())   # [True, False, True, True]
print(agreement.mean())     # 0.75
```

四行中三行方向一致，一致率为 `3/4 = 0.75`，即 75%。

### 前提假设

- 数组元素是同一数值类型，通常是浮点数。
- 缺失值用 `nan` 表示；无穷值用 `inf` 或 `-inf` 表示。
- 数组形状与业务含义匹配；一维数组不区分列名。
- 向量化运算不会修改原数组，除非显式赋值或使用视图。
- 浮点比较使用容差；不要用 `==` 判断两个计算结果是否完全相等。

### 边界情况

- 空数组：`np.isfinite([]).all()` 返回 `True`（全称量词对空集为真）；业务上仍需单独检查样本量。
- 全为 NaN：`isfinite(...).all()` 为 `False`，`sum()` 为 0。
- `object` dtype：`np.isfinite` 可能抛出 `TypeError`；进入检查前应转换为数值类型。
- 整数数组：`np.isfinite` 对所有整数返回 `True`；整数不会表示 NaN 或无穷。
- 视图中修改元素：可能改变原数组；需要独立副本时使用 `.copy()`。
- 形状不匹配：广播失败会抛出 `ValueError`；不要依赖隐式广播处理业务维度。
- 除零：浮点除法可能得到 `inf` 或 `nan`，随后被有限值检查捕获；整数除零会抛出 `ZeroDivisionError`。
- 方向一致率在预测或实际为 NaN 时结果不可靠；当前机器学习流程先删除含缺失的行。

## 相关知识

### 前置概念

- `python_values_and_types`：数组元素是数值类型。
- `python_collections`：数组与列表的容器差异。

### 相关词条

- `pandas_series_and_dataframe` pandas Series 与 DataFrame
- `returns_and_pct_change` 收益率与 `pct_change`
- `rolling_window` 滚动窗口
- `missing_data` 缺失数据

### 建议下一篇

`pandas_series_and_dataframe`：了解带索引和列名的表格如何承载行情数据。

## 参考资料

- `S010` NumPy 文档：`ndarray`、`isfinite`、广播和数组运算；页面未联网复核。
- `A012` Harris 等（2020）：NumPy 数组编程的学术背景；书目信息待复核。
- `P003` docs/METHODOLOGY.md：年化波动率和方向一致率的项目口径。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
