# Claude Code 交接：使用手册与专业知识库内容搜集

> 历史任务文档：仅适用于 2026-10-22 的手册内容任务。2026-10-27 桌面升级请从 [当前交接](HANDOFF.md) 和 [路线图](ROADMAP.md) 开始；本文件的只写内容范围不限制新升级任务。

状态：已锁定的内容工作单  
日期：2026-10-22  
目标版本：Quant Lab CN/HK `2.2.0-rc.1` 的内容输入  
当前发行基线：`2.1.0-rc.1`，源码发布提交 `fb760b7af859ee26c1907a03f4fe3e067d21a6ff`

## 0. 给 Claude Code 的启动指令

把下面这段作为首次消息，并让 Claude Code 直接读取本文件：

```text
请先阅读项目 AGENTS.md 和 docs/CLAUDE_MANUAL_CONTENT_HANDOFF.md，严格按交接文档执行。
本次只完成“批次 1：10 篇使用手册”，只允许写 docs/knowledge-drafts/，不要修改程序、测试、数据库、版本号或发行文件。
开始前只读核对交接文档列出的项目事实文件；完成后更新 CATALOG.md、REVIEW_NOTES.md，并按交接文档第 9 节回报。遇到不确定的软件事实请标记 needs_code_review，不要猜测或自行改代码。
```

每次只交付一个批次。前一批经人工或 Codex 复核后，再把批次编号替换为下一批继续，不要在一个上下文里一次生成 95 篇文档。

## 1. 你的角色与边界

你是本任务的**资料研究员和中文技术作者**。你的工作是搜集、核对并撰写使用手册和专业知识文章，产出可由 Codex 后续转换为应用内结构化内容的 Markdown 草稿。

你不负责实现软件功能。不得修改：

- `quant_lab/`、`tests/`、`app.py`、`desktop_launcher.py`；
- SQLite schema、迁移、Provider、金融计算或回测代码；
- `VERSION`、安装器、构建脚本、Release 文件；
- 现有用户资料、数据库、缓存或凭据；
- 本交接文档之外的既有项目文档。

允许新增或更新的路径仅限：

```text
docs/knowledge-drafts/
  README.md
  CATALOG.md
  manual/
  articles/
  references/
  REVIEW_NOTES.md
```

如果代码事实与本工作单冲突，先在 `REVIEW_NOTES.md` 记录证据和建议，不要自行修改程序。不得调用付费模型 API，不得写入或索取任何密钥。

## 2. 已锁定的产品决定

这些决定不再由你重新设计：

1. 顶栏“新手使用指引”将改名为“使用手册”。
2. 手册继续使用现有右侧停靠面板，不改成独立页面。
3. 学习体系改为纯阅读和检索，不再有任务、打卡、完成度、测验、错题、学习目标或首次学习欢迎页。
4. 手册只有三个主入口：`快速开始`、`功能说明`、`专业知识库`。
5. 专业文章采用“三级分层＋百科词条”：快速理解、软件实践、专业原理。
6. 默认先显示白话解释；公式、符号、推导和手算放在可展开的专业层。
7. Quant Academy 保留为可选固定样本实验，不再承担进度和测验。
8. 现有“新手模式／专业模式”将改为“显示详细解释提示”，只影响提示密度，不影响计算。
9. 原有任务、测验和进度数据会在后续 schema v5 迁移中从活动数据库删除；研究笔记和实验必须保留。
10. 专业知识覆盖金融、统计、机器学习、Python、pandas、SQLite、测试、版本管理和模块化架构。

## 3. 项目事实与不可突破的口径

写作必须服从以下现状，不能把计划功能写成已经实现：

- 软件是 Python 模块化单体、Streamlit 前端、pywebview Windows 桌面壳。
- 当前支持 A 股和港股历史日线研究；不提供实时行情，不执行实盘交易。
- A 股历史主链路为 AKShare 腾讯接口；港股主链路为 AKShare 东方财富接口，失败时可能回退新浪并显示来源。
- 自选股价格只是最近历史日线收盘参考，不是实时价格。
- 收盘信号只能使用当日及更早数据，最早下一交易日开盘模拟成交。
- 复权价可生成信号；成交和估值使用同日不复权价格。
- 费用、滑点、整手和涨跌停都是研究假设，不声称完整覆盖交易所规则。
- 不同币种不能直接加总；当前组合要求同市场、同币种。
- 当前策略只有内置单均线、双均线和趋势过滤。
- 当前统计能力包括收益描述、均值为零的 t 检验和时间顺序线性回归。
- 当前机器学习不是分类器、因子框架、深度学习或自动交易系统。
- 当前组合包括等权和训练期逆波动率示例，未完整计入组合调仓成本。
- DeepSeek 只在用户明确发送时请求模型；AI 文字不是计算事实。
- 模拟或教学数据必须始终明确标记，不能称为真实行情或完成真实数据任务。
- “理论扩展”可讲解软件尚未实现的知识，但必须明确标记 `当前软件未实现`。

开始写作前，应只读检查以下事实来源：

```text
README.md
ARCHITECTURE.md
LEARNING.md
docs/METHODOLOGY.md
docs/DATA.md
quant_lab/knowledge.py
quant_lab/guidance.py
quant_lab/learning.py
quant_lab/backtest.py
quant_lab/statistics.py
quant_lab/portfolio.py
```

## 4. 交付物

### 4.1 总目录

创建 `docs/knowledge-drafts/CATALOG.md`，包含：

- 所有手册章节和专业词条的稳定 ID、中文标题、英文名、分类；
- 功能状态：`implemented`、`academy_demo`、`theory_only`、`needs_code_review`；
- 关联软件模块和关联词条；
- 文章状态：`todo`、`drafted`、`source_checked`、`review_needed`；
- 主要来源编号；
- 重复、合并、缺口和待 Codex 判断事项。

### 4.2 使用手册草稿

在 `docs/knowledge-drafts/manual/` 交付以下 10 篇：

| ID | 文件 | 内容 |
| --- | --- | --- |
| `quick_start` | `quick_start.md` | 从选择资料库到保存第一份可复现实验的完整流程 |
| `workspace` | `workspace.md` | 顶栏、左侧导航、三个面板、设置和资料库 |
| `market_data` | `market_data.md` | 代码、名称、区间、复权、来源、缓存、图表、自选股 |
| `strategy` | `strategy.md` | 策略类型、窗口、收盘信号、预热和常见无信号原因 |
| `backtest` | `backtest.md` | 下一开盘、费用、滑点、订单、基准、样本内外、存档 |
| `risk_portfolio` | `risk_portfolio.md` | 单资产风险、组合输入、共同日期、权重和币种限制 |
| `statistics_ml` | `statistics_ml.md` | t 检验、时间切分、基线、MAE、R²、方向一致率 |
| `academy` | `academy.md` | 固定教学样本、参数实验、代码和与真实行情的区别 |
| `deepseek` | `deepseek.md` | Key、模型、显式请求、上下文、研究实验和安全边界 |
| `research_notes` | `research_notes.md` | 分类、草稿、附件、回收站、实验复算和导出 |

每篇手册必须按此顺序写：

```markdown
# 标题

## 这一页是做什么的
## 使用前需要什么
## 控件和结果说明
## 推荐操作顺序
## 一个可复现的小例子
## 怎么判断结果是否有效
## 常见错误与处理
## 数据、计算和适用边界
## 相关术语
## 参考资料
```

不要加入复选框、任务状态、测验或“完成本章”措辞。

### 4.3 专业知识文章

在 `docs/knowledge-drafts/articles/` 下按分类建立子目录。每篇文章一个文件，文件名为稳定英文 ID。

每篇文章必须使用以下模板，不得缺节：

```markdown
---
id: stable_english_id
title: 中文标题
english_title: English Title
aliases: [中文别名, English alias, 缩写]
category: market_data | return_risk | strategy_execution | backtest_research | portfolio | statistics | machine_learning | programming_engineering
software_status: implemented | academy_demo | theory_only | needs_code_review
related_modules: [市场数据]
prerequisites: []
related_articles: []
source_ids: []
last_verified: 2026-10-22
---

# 中文标题（English Title）

## 快速理解
### 一句话解释
### 它解决什么问题
### 最常见的误解

## 软件实践
### 在 Quant Lab 哪里出现
### 输入、输出和单位
### 结果应该怎么读
### 当前软件边界

## 专业原理
### 正式定义
### 公式与符号
### 可手算的小例子
### 前提假设
### 边界情况

## 相关知识
### 前置概念
### 相关词条
### 建议下一篇

## 参考资料
```

### 4.4 参考文献库

在 `docs/knowledge-drafts/references/` 建立：

- `official.md`：Python、pandas、NumPy、SQLite、交易所、监管机构和数据服务官方文档；
- `academic.md`：论文、教材和大学课程资料；
- `source-map.md`：文章 ID 到来源 ID 的映射与用途说明。

每条来源至少记录：来源 ID、标题、作者或机构、年份、URL/DOI/ISBN、核验日期、支持的具体主张。网页链接应指向原始页面，不使用搜索结果链接。

## 5. 必须覆盖的 85 个专业词条

### 5.1 市场与数据（10）

```text
instrument_identity
ohlcv
trading_calendar
timezone_and_session
currency_and_fx
price_adjustment
corporate_actions
data_provenance
cache_and_freshness
data_quality_and_bias
```

其中 `data_quality_and_bias` 必须分清缺失自然日、缺失交易日、停牌、重复行、异常值、幸存者偏差和前视偏差，不能把它们混为一件事。

### 5.2 收益与风险（10）

```text
simple_return
log_return
compound_return
annualized_return
arithmetic_vs_geometric_mean
variance
standard_deviation
volatility
maximum_drawdown
sharpe_ratio
```

### 5.3 策略与执行（10）

```text
signal_position_order_trade
moving_average
moving_average_crossover
trend_following
mean_reversion
lookahead_bias
next_open_execution
lot_size_and_fractional_shares
trading_costs
slippage_liquidity_market_impact
```

`mean_reversion`、碎股和市场冲击若当前软件未实现，必须标记 `theory_only`。

### 5.4 回测与研究（10）

```text
benchmark
equity_curve
cash_position_and_pnl
in_sample_out_of_sample
temporal_split
walk_forward_analysis
parameter_sensitivity
overfitting
data_snooping_and_multiple_testing
reproducibility_and_audit
```

### 5.5 组合分析（8）

```text
covariance
correlation
diversification
portfolio_weights_and_constraints
equal_weight
inverse_volatility
rebalancing_and_turnover
multi_currency_portfolio
```

### 5.6 统计推断（9）

```text
sample_and_population
mean_and_median
sampling_distribution
standard_error
null_and_alternative_hypothesis
t_test
p_value
confidence_interval
autocorrelation_and_stationarity
```

### 5.7 机器学习（8）

```text
features_and_targets
time_ordered_split
data_leakage
feature_scaling
prediction_baseline
mae_and_rmse
r_squared
time_series_cross_validation
```

方向一致率、超参数和模型过拟合应分别放入最相关文章的相关知识与常见误解部分。

### 5.8 Python、数据处理与工程（20）

```text
python_values_and_types
python_control_flow
python_functions
python_collections
python_exceptions
python_modules_and_packages
type_hints_and_dataclasses
numpy_arrays
pandas_series_and_dataframe
datetime_and_index
missing_data
returns_and_pct_change
rolling_window
alignment_join_and_merge
csv_and_json
sqlite_and_transactions
schema_migration
hash_and_fingerprint
provider_api_cache_and_concurrency
automated_testing_git_and_modular_monolith
```

最后一篇需要拆成清晰小节，不把测试、Git 和架构写成同一个概念；它们共享一篇只是为了控制首版文章数量。

## 6. 内容质量标准

### 6.1 写作层次

- 面向第一次接触量化研究的中文用户，但不能牺牲专业准确性。
- 第一屏先给白话结论，不用公式作为开场。
- 首次出现英文术语时写成“中文（English）”，之后使用中文或约定缩写。
- 句子应直接、具体，避免营销语言、空泛鼓励和 AI 套话。
- 不写“显然”“一定”“稳赚”“精准预测”等无证据措辞。
- 不把相关性写成因果，不把 p 值写成假设为真的概率，不把回测写成未来收益。

### 6.2 数学与例子

- 每篇涉及计算的文章至少包含一个可手算的小样本。
- 明确输入、公式、单位、结果和解释边界。
- 说明样本分母与总体分母、百分数与小数、价格与收益率的区别。
- 覆盖空样本、样本不足、零波动、无效值或分母为零等相关边界。
- 时间序列示例必须保持先后顺序，不能随机混合未来样本。
- 涉及软件当前算法时，必须与代码和 `docs/METHODOLOGY.md` 一致。

### 6.3 软件状态

- `implemented`：代码中确实存在且当前界面可用。
- `academy_demo`：只在固定教学样本中演示。
- `theory_only`：专业扩展，当前软件没有对应计算或按钮。
- `needs_code_review`：无法根据现有代码可靠判断，交回 Codex 复核。
- 不得为了让文章完整而虚构按钮、页面、模型、字段或数据源。

### 6.4 来源

- 会变化的交易规则、市场制度、费用、结算、数据接口和软件 API 必须优先引用官方资料，并写明适用市场、生效日期和核验日期。
- Python、pandas、NumPy、SQLite 优先引用官方文档。
- 数学和统计优先引用经典教材、原始论文或大学公开课程资料。
- 不使用聚合转载、SEO 内容农场、自媒体帖子作为关键定义的唯一来源。
- 不大段复制原文；应独立归纳，并让来源映射到具体主张。
- 无法核实的事实标记 `NEEDS_REVIEW`，不得猜测。

## 7. 搜集与写作顺序

不要一次生成全部文章。按以下批次工作，每批完成后更新 `CATALOG.md` 和 `REVIEW_NOTES.md`：

1. 手册 10 篇；核对所有控件名称和当前能力。
2. 市场与数据、收益与风险，共 20 篇。
3. 策略与执行、回测与研究，共 20 篇。
4. 组合分析、统计推断、机器学习，共 25 篇。
5. Python、数据处理与工程，共 20 篇。
6. 全局术语统一、交叉链接、来源复核和重复内容消除。

每批交付时报告：

- 完成和未完成文章 ID；
- 新增来源及其支持的主张；
- 与软件实现不一致或不确定的地方；
- 重复、冲突或建议合并的词条；
- 需要 Codex 做代码事实复核的问题。

## 8. 验收清单

交回前逐项检查：

- [ ] 10 篇手册全部存在并使用统一章节模板。
- [ ] 85 个专业词条全部出现在目录中。
- [ ] 每篇文章都有稳定 ID、别名、分类、状态和关联模块。
- [ ] 每篇计算文章都有可手算例子和边界情况。
- [ ] 所有 `implemented` 声明都有本地代码依据。
- [ ] 所有未实现能力均标记 `theory_only`。
- [ ] A 股、港股、币种、复权和时间口径没有混写。
- [ ] 模拟数据没有被称为真实行情。
- [ ] 没有投资建议、收益承诺或实盘执行暗示。
- [ ] 会变化的规则和 API 有官方来源与核验日期。
- [ ] 引用没有裸链接、搜索结果链接或大段原文复制。
- [ ] 交叉引用 ID 全部存在，无循环式“参见本条”。
- [ ] 没有修改允许目录之外的文件。

## 9. 最终交回格式

最终回复只需给出：

1. 完成批次和文章数量；
2. `docs/knowledge-drafts/` 中的文件清单；
3. `needs_code_review` 与 `NEEDS_REVIEW` 项目列表；
4. 来源数量和类型统计；
5. 建议 Codex 优先复核的最多 10 个问题；
6. 明确声明未修改程序代码、数据库和发行文件。

不要在最终回复中宣称内容已经进入软件；这些草稿必须由 Codex 复核、转换、测试并通过实际 WebView 验收后，才能成为正式功能。
