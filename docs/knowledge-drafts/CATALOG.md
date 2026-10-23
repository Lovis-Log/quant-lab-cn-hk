# 使用手册与专业知识库总目录

状态：批次 1 手册已修订；批次 2–4 的 65 篇专业文章已完成；批次 5 的 Python 与工程 20 篇已起草；85 个专业词条全部有草稿
日期：2026-10-23
目标版本：Quant Lab CN/HK `2.2.0-rc.1` 的内容输入
当前代码基线：`codex/learning-center-v2`，提交 `c10728b`（批次 5 起点；本批次未修改程序代码）
文档基线：`c10728b`（批次 4 文档收尾）
写作范围：仅 `docs/knowledge-drafts/`，未修改程序、测试、数据库、VERSION 或发行文件

## 状态与口径

### 功能状态

| 值 | 含义 |
| --- | --- |
| `implemented` | 当前代码中存在对应计算或界面，用户可以使用。 |
| `academy_demo` | 只在 Quant Academy 的固定教学样本中演示。 |
| `theory_only` | 专业扩展；当前软件没有对应计算或按钮，文章必须明确写“当前软件未实现”。 |
| `needs_code_review` | 事实或分层需要 Codex 复核；不得把不确定内容写成已实现。 |

### 文章状态

| 值 | 含义 |
| --- | --- |
| `todo` | 尚未撰写。 |
| `drafted` | 已有草稿，未完成来源核对。 |
| `source_checked` | 已按本地代码和项目文档核对；外部页面可能仍需联网复核。 |
| `review_needed` | 内容或软件口径存在待 Codex 判断的差异。 |

### 批次 1 口径说明

- 10 篇手册按 2.2.0 已锁定的“使用手册”三入口结构撰写：快速开始、功能说明、专业知识库。当前 2.1.0-rc.1 仍显示“新手使用指引”及旧学习中心分区；Codex 接入时应逐项核对实际 DOM 和控件。
- 手册不使用复选框、任务状态、测验、打卡、完成度或“完成本章”措辞。Academy 手册只描述固定教学样本和参数实验，不描述测验或进度。
- 手册中的“显示详细解释提示”对应产品决定中的新标签；当前 `ui_settings.py` 仍显示“新手模式（关闭为专业模式）”。
- 所有 `implemented` 声明都以本地代码为依据；代码位置见 `references/source-map.md`。S001–S007 的官方入口已由 Codex 于 2026-10-22 确认可访问；S023、S024 的官方入口已由 Codex 于 2026-10-23 确认可访问；具体接口字段、条款和生效口径仍待逐项核验，S008–S022 仍待核验。
- 85 个专业词条中，批次 2–5 已起草 85 篇（`market_data` 10、`return_risk` 10、`strategy_execution` 10、`backtest_research` 10、`portfolio` 8、`statistics` 9、`machine_learning` 8、`programming_engineering` 20），`todo` 为 0；本目录同时记录文章状态、来源和关联文章。

### Codex 批次 1 复核调整（2026-10-22）

- 以下 12 个复合或部分实现词条统一改为 `needs_code_review`，不拆分 ID，专业词条总数保持 85：`trading_calendar`、`timezone_and_session`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean`、`lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`、`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`。
- `manual/research_notes.md` 已修正草稿丢失说明：SQLite 草稿不会因清除 WebView 本地存储而删除；只有尚未同步的输入可能丢失；只有“放弃草稿”会删除数据库草稿和草稿附件。
- `manual/deepseek.md` 的目标版本“学习笔记”已统一改为“研究笔记”；程序按钮“保存选定回答到学习笔记”仍需同步重命名，记录在 `REVIEW_NOTES.md`。
- `references/official.md` 的 S001–S007 已改为“官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验”。

### 批次 2 修订（2026-10-23）

- `annualized_return` 已修正 126 个间隔的表述：年化是累计增长因子的平方再减一，即 `(1+R_cum)^2−1`，不再写成“平方根”。
- `maximum_drawdown` 已删除全部英文内部编辑批注，保留 `d=−25%` 恢复涨幅 33.33%、`d=−20%` 恢复涨幅 25% 的示例。
- `corporate_actions`、`price_adjustment` 中的“2 拆 1”统一改为“1 股拆成 2 股（2-for-1 stock split）”。
- `A033` 的 ISBN 已修正为 ISBN-10 `0135161088`、ISBN-13 `9780135161081`；`A035` 按 Cambridge 官方页面改为 2017 年（第 3 版），ISBN `978-1107111820` 不变。
- `currency_and_fx` 从 `implemented` 改为 `needs_code_review`：CNY/HKD 标注与同币种限制已实现；汇率数据、汇率换算、对冲和跨币种组合未实现。
- 专业词条统计更新为 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13；批次 2 为 `implemented` 13、`needs_code_review` 5、`theory_only` 2。
- 来源状态：S023、S024 官方入口已由 Codex 于 2026-10-23 确认可访问，具体规则仍按文章需要核验；A032、A034 书目/DOI 已核验；A033 修正 ISBN 后书目已核验；A035 第三版、ISBN 和 2017 出版日期已核验。
- 该次修订只改 `docs/knowledge-drafts/`，当时未进入批次 3；20 篇文章保持 `drafted`；批次 3 随后单独完成。

### 批次 2 进展（2026-10-22，2026-10-23 修订）

- 20 篇专业文章已写入 `articles/market_data/` 与 `articles/return_risk/`，全部文章状态为 `drafted`。
- `trading_calendar`、`timezone_and_session`、`currency_and_fx`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean` 为 `needs_code_review`，并在正文分三层说明“已计算/显示、只间接使用、未提供/未建模”。
- `corporate_actions`、`log_return` 保持 `theory_only`，正文明确写“当前软件未实现”。
- 不新增或删除 ID，专业词条总数仍为 85。
- 外部来源未逐条读取内容；S001–S007 入口已由 Codex 于 2026-10-22 确认可访问；S023、S024 入口已由 Codex 于 2026-10-23 确认可访问，具体规则仍按文章需要核验；S008–S022 待核验；A032–A035 书目/DOI/ISBN 已核验，A001–A031 待核验。所有文章状态只能是 `drafted`，不标 `source_checked`。
- 每篇计算文章含可手算样本；价格/收益率、百分数/小数、样本/总体分母在相关文章中区分；交易规则、接口、字段和复权行为标记 NEEDS_REVIEW（核验日期：2026-10-22）。
- 文章 frontmatter 的 `last_verified: 2026-10-22` 仅表示本地代码/项目文档核对日期，不表示外部来源内容已核验；外部来源仍需逐条读取。

### 批次 3 进展（2026-10-23）

- 20 篇专业文章已写入 `articles/strategy_execution/`（10 篇）与 `articles/backtest_research/`（10 篇），全部文章状态为 `drafted`。
- 13 篇 `implemented`：`signal_position_order_trade`、`moving_average`、`moving_average_crossover`、`trend_following`、`lookahead_bias`、`next_open_execution`、`trading_costs`、`benchmark`、`equity_curve`、`in_sample_out_of_sample`、`temporal_split`、`parameter_sensitivity`、`reproducibility_and_audit`。
- 3 篇 `needs_code_review`：`lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`；正文均分三层写“已实现/已显示、未显示/未提供、未实现”。
- 3 篇 `theory_only`：`mean_reversion`、`walk_forward_analysis`、`data_snooping_and_multiple_testing`；正文明确写“当前软件未实现”。
- 1 篇 `academy_demo`：`overfitting`；只描述 Quant Academy 第 8 课固定模拟，不写自动检测器。
- 三种策略与本地代码一致：`single_ma` 为收盘价 > 长均线；`dual_ma` 为短均线 > 长均线；`trend` 为收盘价 > 长均线且长均线较前一日上升。
- 回测口径：信号 t 最早 t+1 开盘成交；复权价格只生成信号，成交/估值使用同日不复权价格；只做多、不加杠杆、不做空，卖出全部持股。
- 当前日线引擎每天最多一笔订单；A 股 `i <= last_buy_index` 的 T+1 检查是防御性代码，正常流程不会同日买卖，文章不把 T+1 与零成交量、涨跌停并列为当前可观察的 `blocked` 原因。
- 基准在第二个交易日开盘尝试买入，使用同一成本与成交规则，不强制末日平仓。
- 样本内外：`split=int(N×train_fraction)`，样本外统计从 `split−1` 净值开始，`split_date=raw_history["date"].iloc[split]`；参数敏感性仅样本内并跳过无效窗口。
- 可复现性：`audit_id` 覆盖原始 CSV、信号 CSV、策略、成本配置和训练比例；来源、接收时间、市场、代码、名称、复权保存在实验档案，但不全部进入 `audit_id`；当前实验未保存源码提交或输入契约版本。
- 不新增或删除 ID，专业词条总数仍为 85；未新增来源编号，沿用现有 S/P/A。外部交易规则、费用和制度仍未逐项核验，相关文章保持 NEEDS_REVIEW。
- 专业词条统计保持 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13；批次 3 为 `implemented` 13、`needs_code_review` 3、`theory_only` 3、`academy_demo` 1。
- 批次 3 文章 frontmatter 的 `last_verified: 2026-10-23` 表示本地代码/项目文档核对日期，不表示外部来源内容已核验。

### 批次 4 进展（2026-10-23）

- 25 篇专业文章已写入 `articles/portfolio/`（8 篇）、`articles/statistics/`（9 篇）与 `articles/machine_learning/`（8 篇），全部文章状态为 `drafted`。
- 15 篇 `implemented`：`covariance`、`correlation`、`portfolio_weights_and_constraints`、`equal_weight`、`inverse_volatility`、`null_and_alternative_hypothesis`、`t_test`、`p_value`、`features_and_targets`、`time_ordered_split`、`data_leakage`、`feature_scaling`、`prediction_baseline`、`r_squared`、`time_series_cross_validation`。
- 5 篇 `needs_code_review`：`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`；正文均按“已计算/已显示、只间接使用、未提供/未建模”三层说明。
- 5 篇 `theory_only`：`diversification`、`multi_currency_portfolio`、`sampling_distribution`、`confidence_interval`、`autocorrelation_and_stationarity`；正文明确写“当前软件未实现”，没有暗示不存在的按钮、指标或图表。
- 组合口径与 `portfolio.py`/`ui_analysis.py`/`docs/METHODOLOGY.md` 一致：界面接受 2–4 只不重复的当前市场代码；收盘价按日期内连接，至少 8 个共同收盘日；`returns=closes.pct_change().dropna()`；协方差/相关系数使用全部共同日期收益，样本口径 `ddof=1`；`split=int(len(returns)×train_fraction)`，训练比例 0.50–0.85；权重只用训练收益估计；样本外曲线在第一笔测试收益之前的共同收盘日期归一化为 1。
- 组合权重只有等权与训练期逆波动率；权重为正且合计 100%，没有做空、杠杆、权重上下限或优化器。样本外收益矩阵乘固定权重（`test @ equal`、`test @ inverse`）是每日固定权重的数学曲线，不生成持仓、订单、成交、换手率或调仓成本。核心函数只接收历史表，不掌握币种；同市场/同币种限制由界面上下文保证。
- 统计口径与 `statistics.py`/`ui_analysis.py` 一致：日收益率至少 3 个；均值、样本方差/标准差使用 `n−1`；年化波动率为样本标准差 × `√252`；t 检验零假设为平均日收益率为 0，调用 `ttest_1samp(..., popmean=0.0)` 的默认双侧检验；标准差为 0 时 t 值和 p 值返回 `None`。页面显示 p 值，不单独显示 t 值、自由度、标准误或置信区间。
- 机器学习口径与 `statistics.py` 一致：五个特征 `return_1`、`return_5`、`ma_gap_5_20`、`volume_change`、`volatility_10`；标签 `next_return=close(t+1)/close(t)−1`；零成交量先替换为 NaN，无限值和缺失值最终删除；至少 60 行有效样本；训练比例 0.55–0.85；`split=int(M×train_fraction)`；`train=samples[:split−1]`、索引 `split−1` 为一行间隔、`test=samples[split:]`；训练至少 30 行、测试至少 10 行；`Pipeline(StandardScaler(), LinearRegression())`；训练内 `TimeSeriesSplit(n_splits=3, gap=1)`；MAE、零收益基线 MAE、样本外 R²、方向一致率；RMSE 未计算或显示。
- 不新增、删除或拆分 ID，专业词条总数仍为 85；未新增来源编号，沿用现有 S/P/A。外部来源未逐条读取，25 篇均保持 `drafted`，不标 `source_checked`。
- 全目录功能状态保持 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13；批次 4 为 `implemented` 15、`needs_code_review` 5、`theory_only` 5。
- 批次 4 文章 frontmatter 的 `last_verified: 2026-10-23` 仅表示本地代码/项目文档核对日期，不表示外部来源内容已核验。

### 批次 5 进展（2026-10-23）

- 20 篇专业文章已写入 `articles/programming_engineering/`，全部文章状态为 `drafted`。
- 20 篇全部保持 `implemented`：技术确实被项目代码使用，但不表示软件为用户提供独立的 Python、Git、数据库管理或编程教学工具。
- `python_values_and_types`：区分 `int`、`float`、`str`、`bool`、`None`、日期时间和 pandas/NumPy 类型；说明 `bool` 是 `int` 子类、浮点舍入和 `1% = 0.01`。
- `python_control_flow`：以 `build_signals` 的 `if/elif`、`run_backtest` 的逐日循环与 `while lots > 0`、`RefreshCache` 早返回和 `migrate` 版本分支为例。
- `python_functions`：区分纯计算函数与带网络/文件/数据库副作用的函数；说明默认参数、`None` 返回和异常。
- `python_collections`：`list`、`dict`、`tuple`、`set` 的顺序、可变性和唯一性；明确 `set` 不保留业务排序。
- `python_exceptions`：`DataValidationError`、`DataUnavailableError`、`ValueError`；缓存和名称查询捕获较宽异常以保留旧值；名称失败不代表证券不存在。
- `python_modules_and_packages`：`quant_lab` 模块化单体、核心模块不导入 Streamlit、未来 FastAPI 仅为计划。
- `type_hints_and_dataclasses`：类型注解不自动运行时校验；`frozen=True` 不保证深度不可变；`MarketDataProvider` 为 Protocol。
- `numpy_arrays`：`np.isfinite` 检查 NaN 和正负无穷；数组不是主要持久化格式；`np.sin`/`np.cos` 只用于 Academy 固定模拟。
- `pandas_series_and_dataframe`：列、索引、dtype、复制、筛选和向量化；历史缓存返回深拷贝。
- `datetime_and_index`：行情 `date` 为无时区交易日；`received_at`/`created_at` 为 UTC；界面显示北京时间 UTC+08:00；接收时间不是交易所报价时间。
- `missing_data`：必需字段缺失显式报错；组合共同日期内连接并 `dropna`；机器学习零成交量转 NaN 后删除含缺失行；无通用插值。
- `returns_and_pct_change`：简单收益率 `r_t=P_t/P_{t−1}−1`；首行 NaN；只有机器学习 `volume_change` 明确 `fill_method=None`。
- `rolling_window`：`rolling(window=N,min_periods=N).mean()`、5/20 日均线和 10 日收益标准差；窗口按交易日行数。
- `alignment_join_and_merge`：组合按日期 inner join；回测要求 raw/signal 日期完全一致；排序并拒绝重复日期。
- `csv_and_json`：实验 CSV 为 UTF-8 字节、zlib 压缩 BLOB、读取核对 SHA-256 后 `parse_dates` 与 `float_precision="round_trip"`；JSON 不是加密或自动 schema 验证；部分界面下载使用 UTF-8 BOM。
- `sqlite_and_transactions`：`timeout=15`、`row_factory=sqlite3.Row`、`PRAGMA foreign_keys=ON`；上下文 commit/rollback/close；无远程数据库、账户隔离、加密或防篡改保证。
- `schema_migration`：`SCHEMA_VERSION=4`、`PRAGMA user_version`、高版本拒绝打开、升级前 backup API 备份、`BEGIN IMMEDIATE` 事务与失败回滚；`stage_library` 与迁移分开。
- `hash_and_fingerprint`：完整 SHA-256 用于 raw/signal CSV 和附件；`audit_id` 为前 16 个十六进制字符（64 位）；哈希不是加密、签名或第三方存证。
- `provider_api_cache_and_concurrency`：`MarketDataProvider` Protocol、AKShare 默认实现、历史缓存 15 分钟/64 条、快照 5 分钟/1 秒间隔、名称 24 小时/5 分钟冷却、single-flight 与等待超时；缓存和锁只在当前进程。
- `automated_testing_git_and_modular_monolith`：正文拆成自动化测试、Git、模块化单体三个独立部分；测试通过不等于真实 WebView、外部接口或安装包验收；Git 不是应用按钮；FastAPI 是未来计划。
- 不新增、删除或拆分 ID，专业词条总数仍为 85；未新增来源编号，沿用 S008–S011、S017–S020、P001–P004、A011、A012 等现有来源。
- 全目录功能状态保持 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13；批次 5 为 `implemented` 20。
- 批次 5 文章 frontmatter 的 `last_verified: 2026-10-23` 仅表示本地代码/项目文档核对日期，不表示外部来源内容已核验。

## 使用手册（10 篇）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `quick_start` | 快速开始：从资料库到第一份可复现实验 / Quick Start | `implemented` | UI、存储、回测、研究笔记 | `instrument_identity`, `data_provenance`, `next_open_execution`, `reproducibility_and_audit` | `source_checked` | P001–P004, S001–S003, A006 | 完整流程；不承诺收益或上游可用性。 |
| `workspace` | 工作台与使用手册面板 / Workspace and Panels | `needs_code_review` | UI、设置、桌面 | `data_provenance`, `cache_and_freshness`, `provider_api_cache_and_concurrency`, `reproducibility_and_audit` | `review_needed` | P001, P002, P005, S012, S022 | `needs_code_review` 仅指三入口/改名/设置标签尚未接入；研究页控件已实现。 |
| `market_data` | 市场数据：代码、名称、区间、复权、来源与缓存 / Market Data | `implemented` | 市场数据、名称、证券目录、UI | `instrument_identity`, `ohlcv`, `trading_calendar`, `timezone_and_session`, `currency_and_fx`, `price_adjustment`, `corporate_actions`, `data_provenance`, `cache_and_freshness`, `data_quality_and_bias` | `source_checked` | S001, S013, P002–P004 | 港股接受 1–5 位数字并补足五位；界面提示五位。 |
| `strategy` | 策略实验室：均线、收盘信号与预热 / Strategy Lab | `implemented` | 策略、UI | `signal_position_order_trade`, `moving_average`, `moving_average_crossover`, `trend_following`, `lookahead_bias`, `next_open_execution` | `source_checked` | P002, P003, A008 | 单均线/趋势过滤只用长均线；双均线用短/长均线。 |
| `backtest` | 历史回测：下一开盘成交、费用、基准与样本外 / Backtest | `implemented` | 回测、研究、存储、UI | `benchmark`, `equity_curve`, `cash_position_and_pnl`, `in_sample_out_of_sample`, `temporal_split`, `parameter_sensitivity`, `overfitting`, `reproducibility_and_audit`, `next_open_execution`, `trading_costs`, `slippage_liquidity_market_impact`, `lot_size_and_fractional_shares`, `lookahead_bias` | `source_checked` | P002, P003, S002–S004, A006, A007 | 费用/滑点/整手/涨跌停均为可修改研究假设。 |
| `risk_portfolio` | 风险与组合：单资产波动、共同日期与权重 / Risk and Portfolio | `implemented` | 指标、组合、UI | `covariance`, `correlation`, `diversification`, `portfolio_weights_and_constraints`, `equal_weight`, `inverse_volatility`, `rebalancing_and_turnover`, `multi_currency_portfolio`, `variance`, `standard_deviation`, `volatility`, `maximum_drawdown` | `source_checked` | P002, P003, A001, A009, A013 | 同市场同币种；固定权重每日再平衡，未计调仓成本。 |
| `statistics_ml` | 统计与机器学习：t 检验、时间切分与样本外误差 / Statistics and ML | `implemented` | 统计、UI | `sample_and_population`, `standard_error`, `null_and_alternative_hypothesis`, `t_test`, `p_value`, `features_and_targets`, `time_ordered_split`, `data_leakage`, `feature_scaling`, `prediction_baseline`, `mae_and_rmse`, `r_squared`, `time_series_cross_validation` | `source_checked` | P003, S015, S016, A003–A005, A009, A010 | 线性回归，不是分类器/因子框架/自动交易。 |
| `academy` | Quant Academy：固定教学样本与参数实验 / Quant Academy | `implemented` | 学习、知识、UI | `simple_return`, `compound_return`, `moving_average`, `variance`, `standard_deviation`, `volatility`, `maximum_drawdown`, `sharpe_ratio`, `correlation`, `overfitting` | `review_needed` | P003, P005, A002, A009 | 当前代码仍有“到学习中心保存实验与测验”按钮；目标版本移除，文章不写测验。 |
| `deepseek` | DeepSeek 助手：密钥、模型与显式请求 / DeepSeek Assistant | `implemented` | AI、设置、UI | `reproducibility_and_audit`, `data_provenance`, `overfitting`, `lookahead_bias`, `data_leakage`, `p_value`, `mae_and_rmse`, `r_squared` | `source_checked` | S005–S007, S022, P002, P003 | 连接设置实际在 `⚙` → DeepSeek；面板旧文案“本页上方”待修。 |
| `research_notes` | 研究笔记：分类、草稿、附件、回收站与实验复算 / Research Notes | `implemented` | 存储、笔记、UI | `reproducibility_and_audit`, `hash_and_fingerprint`, `sqlite_and_transactions`, `schema_migration`, `data_provenance`, `data_quality_and_bias`, `overfitting` | `source_checked` | P002, P004, S011, S018 | 附件 200MB/20 个/1GB；复算只读归档。 |

## 市场与数据（10）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `instrument_identity` | 证券身份与代码规范化 / Instrument Identity and Symbol Normalization | `implemented` | `market_data.py`, `securities.py`, `names.py`, `ui.py` | `ohlcv`, `currency_and_fx`, `data_provenance`, `corporate_actions` | `drafted` | S001, S013, P004 | 批次 2 已起草；规范化与名称/目录辅助；未用交易所名录验证上市身份。 |
| `ohlcv` | 开高低收与成交量 / OHLCV | `implemented` | `processing.py`, `data.py`, `ui.py` | `trading_calendar`, `data_quality_and_bias`, `simple_return`, `price_adjustment` | `drafted` | S001, P004, A032 | 批次 2 已起草；字段校验、表格和 CSV；价格/收益率单位区分。 |
| `trading_calendar` | 交易日历 / Trading Calendar | `needs_code_review` | `data.py`, `processing.py`, `portfolio.py` | `timezone_and_session`, `alignment_join_and_merge`, `data_quality_and_bias`, `annualized_return` | `drafted` | S001, S002, S003, P004 | 批次 2 已起草；实际交易日对齐；无独立日历服务；已分三层说明。 |
| `timezone_and_session` | 时区与交易时段 / Time Zone and Trading Session | `needs_code_review` | `data.py`, `ui_updates.py` | `data_provenance`, `cache_and_freshness`, `trading_calendar`, `reproducibility_and_audit` | `drafted` | S023, S001, S002, S003, P002 | 批次 2 已起草；UTC 存储/北京时间显示；无交易时段模型；已分三层说明。 |
| `currency_and_fx` | 币种与汇率 / Currency and FX | `needs_code_review` | `data.py`, `portfolio.py`, `ui.py` | `multi_currency_portfolio`, `price_adjustment`, `data_provenance`, `portfolio_weights_and_constraints` | `drafted` | S024, S001, P004, A035 | 批次 2 已修订；CNY/HKD 标注与同币种限制已实现；汇率数据、换算、对冲和跨币种组合未实现。 |
| `price_adjustment` | 价格复权 / Price Adjustment | `implemented` | `data.py`, `ui.py`, `ui_strategy.py` | `corporate_actions`, `simple_return`, `next_open_execution`, `data_provenance` | `drafted` | S001, P003, P004, A033 | 批次 2 已起草；三口径；信号可用复权，成交/估值用不复权；复权非总回报。 |
| `corporate_actions` | 公司行动 / Corporate Actions | `theory_only` | 仅通过复权价格间接体现 | `price_adjustment`, `simple_return`, `compound_return`, `data_quality_and_bias` | `drafted` | S001, P004, A033, A032 | 批次 2 已起草；`theory_only`；未单独建模分红、拆股现金流或公司行动表。 |
| `data_provenance` | 数据来源与时间戳 / Data Provenance | `implemented` | `data.py`, `refresh.py`, `ui_updates.py`, `storage.py` | `cache_and_freshness`, `timezone_and_session`, `reproducibility_and_audit`, `data_quality_and_bias` | `drafted` | S001, P002, P004, A034 | 批次 2 已起草；来源、`received_at`、缓存和更新结果；FAIR 边界。 |
| `cache_and_freshness` | 缓存与新鲜度 / Cache and Freshness | `implemented` | `data.py`, `refresh.py`, `ui_updates.py` | `data_provenance`, `provider_api_cache_and_concurrency`, `data_quality_and_bias`, `reproducibility_and_audit` | `drafted` | S001, P002, P004, S008 | 批次 2 已起草；历史 15 分钟/64 条，快照 5 分钟；手动绕过；缓存非实时。 |
| `data_quality_and_bias` | 数据质量与偏差 / Data Quality and Bias | `needs_code_review` | `processing.py`, `data.py`, `docs/METHODOLOGY.md` | `missing_data`, `lookahead_bias`, `data_provenance`, `overfitting`, `cache_and_freshness` | `drafted` | S001, P003, P004, A006, A016, A022, A034 | 批次 2 已起草；字段校验已实现；缺失/停牌/重复/异常/幸存者/前视偏差逐项分层；已分三层说明。 |

## 收益与风险（10）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `simple_return` | 简单收益率 / Simple Return | `implemented` | `metrics.py`, `knowledge.py`, `ui.py` | `log_return`, `compound_return`, `returns_and_pct_change`, `annualized_return` | `drafted` | P003, A009, A032 | 批次 2 已起草；首尾收盘价；不含分红/费用；百分数/小数区分。 |
| `log_return` | 对数收益率 / Log Return | `theory_only` | 无 | `simple_return`, `compound_return`, `annualized_return`, `volatility` | `drafted` | A032, A020, A009 | 批次 2 已起草；`theory_only`；当前不使用对数收益；与简单收益率区分。 |
| `compound_return` | 复合收益 / Compound Return | `implemented` | `metrics.py`, `learning.py`, `knowledge.py` | `annualized_return`, `arithmetic_vs_geometric_mean`, `maximum_drawdown`, `equity_curve` | `drafted` | P003, P005, A009, A032 | 批次 2 已起草；多期乘法；学院和净值；先涨后跌/回本例子。 |
| `annualized_return` | 年化收益 / Annualized Return | `implemented` | `metrics.py`, `knowledge.py` | `compound_return`, `arithmetic_vs_geometric_mean`, `volatility`, `maximum_drawdown` | `drafted` | P003, A009, A032 | 批次 2 已起草；252/n 几何换算；不是预测；短样本放大。 |
| `arithmetic_vs_geometric_mean` | 算术平均与几何平均 / Arithmetic vs Geometric Mean | `needs_code_review` | `metrics.py`, `statistics.py` | `compound_return`, `annualized_return`, `sharpe_ratio`, `volatility` | `drafted` | P003, A009, A032, A013 | 批次 2 已起草；算术/几何均值分层；无并列 UI；已分三层说明。 |
| `variance` | 方差 / Variance | `implemented` | `metrics.py`, `statistics.py`, `knowledge.py`, `ui_analysis.py` | `standard_deviation`, `covariance`, `sample_and_population`, `volatility` | `drafted` | P003, A009 | 批次 2 已起草；样本分母 `n−1` vs 总体 `n`；小数/百分数单位。 |
| `standard_deviation` | 标准差 / Standard Deviation | `implemented` | `metrics.py`, `knowledge.py` | `variance`, `volatility`, `standard_error`, `sharpe_ratio` | `drafted` | P003, A009 | 批次 2 已起草；样本标准差；样本/总体分母；年化基础。 |
| `volatility` | 波动率 / Volatility | `implemented` | `metrics.py`, `knowledge.py`, `ui_analysis.py` | `standard_deviation`, `sharpe_ratio`, `autocorrelation_and_stationarity`, `maximum_drawdown` | `drafted` | P003, A009, A020, A022 | 批次 2 已起草；日标准差 × `√252`；历史波动非未来预测。 |
| `maximum_drawdown` | 最大回撤 / Maximum Drawdown | `implemented` | `metrics.py`, `knowledge.py`, `ui_analysis.py` | `equity_curve`, `volatility`, `sharpe_ratio`, `rebalancing_and_turnover` | `drafted` | P003, A014, A026 | 批次 2 已起草；路径指标；恢复涨幅；非未来损失上限。 |
| `sharpe_ratio` | 夏普比率 / Sharpe Ratio | `implemented` | `metrics.py`, `knowledge.py`, `ui_strategy.py` | `volatility`, `annualized_return`, `benchmark`, `standard_deviation`, `maximum_drawdown` | `drafted` | P003, A002, A009, A026 | 批次 2 已起草；默认无风险利率 0；零波动不显示；不是盈利概率。 |

## 策略与执行（10）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `signal_position_order_trade` | 信号、持仓、订单与成交 / Signal, Position, Order, Trade | `implemented` | `strategy.py`, `backtest.py`, `ui_strategy.py` | `moving_average_crossover`, `next_open_execution`, `cash_position_and_pnl` | `drafted` | P002, P003, P004 | 批次 3 已起草；信号、目标持仓、订单、成交和每日估值分层。 |
| `moving_average` | 移动平均线 / Moving Average | `implemented` | `strategy.py`, `knowledge.py`, `learning.py` | `moving_average_crossover`, `trend_following`, `rolling_window` | `drafted` | P003, P005, A008 | 批次 3 已起草；SMA、`min_periods=N`、窗口 2–250。 |
| `moving_average_crossover` | 均线交叉 / Moving Average Crossover | `implemented` | `strategy.py`, `ui_strategy.py` | `moving_average`, `trend_following`, `signal_position_order_trade` | `drafted` | P003, P005, A008 | 批次 3 已起草；`dual_ma` 短均线 > 长均线，严格大于。 |
| `trend_following` | 趋势跟随 / Trend Following | `implemented` | `strategy.py` | `moving_average`, `moving_average_crossover`, `mean_reversion` | `drafted` | P003, P005, A008 | 批次 3 已起草；收盘价 > 长均线且长均线较前一日上升；短周期不参与条件。 |
| `mean_reversion` | 均值回归 / Mean Reversion | `theory_only` | 无 | `trend_following`, `moving_average`, `autocorrelation_and_stationarity` | `drafted` | A008, A020 | 批次 3 已起草；`theory_only`；当前软件未实现均值回归。 |
| `lookahead_bias` | 前视偏差 / Lookahead Bias | `implemented` | `research.py`, `backtest.py`, `statistics.py` | `next_open_execution`, `data_leakage`, `data_quality_and_bias` | `drafted` | P003, P004, A016 | 批次 3 已起草；引擎强制收盘信号/下一开盘；无自动检测器。 |
| `next_open_execution` | 下一交易日开盘成交 / Next-Open Execution | `implemented` | `backtest.py`, `research.py` | `signal_position_order_trade`, `lookahead_bias`, `trading_costs` | `drafted` | P003, P004, S002, S003 | 批次 3 已起草；信号 t−1，成交 t；不强制末日平仓。 |
| `lot_size_and_fractional_shares` | 整手与碎股 / Lot Size and Fractional Shares | `needs_code_review` | `backtest.py`, `ui_strategy.py` | `trading_costs`, `slippage_liquidity_market_impact`, `next_open_execution` | `drafted` | S002, S003, P003, P004 | 批次 3 已起草；整手已实现；碎股未实现；港股每手数量由用户输入，软件不自动验证。 |
| `trading_costs` | 交易成本 / Trading Costs | `implemented` | `backtest.py`, `knowledge.py`, `ui_strategy.py` | `slippage_liquidity_market_impact`, `lot_size_and_fractional_shares`, `benchmark` | `drafted` | S002, S003, P003 | 批次 3 已起草；佣金+最低+附加费；默认值为可修改研究假设。 |
| `slippage_liquidity_market_impact` | 滑点、流动性与市场冲击 / Slippage, Liquidity, Market Impact | `needs_code_review` | `backtest.py`, `knowledge.py` | `trading_costs`, `lot_size_and_fractional_shares`, `next_open_execution` | `drafted` | S002, S003, P003, A016 | 批次 3 已起草；固定基点滑点已实现；订单簿、容量和市场冲击未实现。 |

## 回测与研究（10）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `benchmark` | 基准 / Benchmark | `implemented` | `backtest.py`, `research.py`, `ui_strategy.py` | `equity_curve`, `trading_costs`, `in_sample_out_of_sample` | `drafted` | P003, A006 | 批次 3 已起草；同成本买入持有；第二个交易日开盘尝试买入；不强制末日平仓。 |
| `equity_curve` | 净值曲线 / Equity Curve | `implemented` | `backtest.py`, `metrics.py`, `ui_strategy.py` | `cash_position_and_pnl`, `maximum_drawdown`, `benchmark` | `drafted` | P003, A026 | 批次 3 已起草；`equity=cash+shares×不复权收盘`；每日估值。 |
| `cash_position_and_pnl` | 现金、持仓与盈亏 / Cash, Position, and PnL | `needs_code_review` | `backtest.py`, `storage.py` | `equity_curve`, `signal_position_order_trade`, `trading_costs` | `drafted` | P003, P004, A026 | 批次 3 已起草；每日 cash/shares/equity 已记录；独立 PnL/已实现/未实现盈亏列未提供。 |
| `in_sample_out_of_sample` | 样本内与样本外 / In-Sample and Out-of-Sample | `implemented` | `research.py`, `ui_strategy.py` | `temporal_split`, `overfitting`, `walk_forward_analysis` | `drafted` | P003, A006, A016 | 批次 3 已起草；`split=int(N×train_fraction)`；测试从 `split−1` 净值起；`split_date=date[split]`。 |
| `temporal_split` | 时间顺序切分 / Temporal Split | `implemented` | `research.py`, `statistics.py`, `portfolio.py` | `in_sample_out_of_sample`, `time_ordered_split`, `data_leakage` | `drafted` | P003, A005, A016 | 批次 3 已起草；按日期不随机；机器学习训练/测试留一行间隔。 |
| `walk_forward_analysis` | 滚动前向分析 / Walk-Forward Analysis | `theory_only` | 无 | `temporal_split`, `parameter_sensitivity`, `overfitting` | `drafted` | P003, A005, A006, A016 | 批次 3 已起草；`theory_only`；当前只有单次切分和训练期 3 折 CV，不是完整 walk-forward。 |
| `parameter_sensitivity` | 参数敏感性 / Parameter Sensitivity | `implemented` | `research.py`, `ui_strategy.py` | `overfitting`, `data_snooping_and_multiple_testing`, `in_sample_out_of_sample` | `drafted` | P003, A006, A016 | 批次 3 已起草；仅样本内 3×3 网格；跳过无效窗口。 |
| `overfitting` | 过拟合 / Overfitting | `academy_demo` | `learning.py`, `guidance.py`, `research.py` | `in_sample_out_of_sample`, `parameter_sensitivity`, `data_snooping_and_multiple_testing` | `drafted` | P003, P005, A006, A018 | 批次 3 已起草；Academy 固定模拟；无自动过拟合检测器。 |
| `data_snooping_and_multiple_testing` | 数据窥探与多重检验 / Data Snooping and Multiple Testing | `theory_only` | 无 | `overfitting`, `parameter_sensitivity`, `p_value` | `drafted` | P003, A007, A015, A016 | 批次 3 已起草；`theory_only`；当前未做多重检验校正。 |
| `reproducibility_and_audit` | 可复现性与审计 / Reproducibility and Audit | `implemented` | `research.py`, `storage.py`, `ui_research.py` | `hash_and_fingerprint`, `data_provenance`, `schema_migration` | `drafted` | P002, P004, S011, A034 | 批次 3 已起草；`audit_id` 覆盖 raw/signal CSV、策略、成本、训练比例；未保存源码提交/输入契约版本。 |

## 组合分析（8）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `covariance` | 协方差 / Covariance | `implemented` | `portfolio.py`, `knowledge.py`, `ui_analysis.py` | `correlation`, `variance`, `portfolio_weights_and_constraints` | `drafted` | P003, A001, A009 | 批次 4 已起草；全部共同日期同日收益率；样本分母 `n−1`；不是价格协方差。 |
| `correlation` | 相关系数 / Correlation | `implemented` | `portfolio.py`, `knowledge.py`, `ui_analysis.py` | `covariance`, `diversification`, `multi_currency_portfolio` | `drafted` | P003, A001, A009 | 批次 4 已起草；Pearson 同日收益率相关；不证明因果或未来分散。 |
| `diversification` | 分散化 / Diversification | `theory_only` | `portfolio.py`, `ui_analysis.py`（仅相关/曲线支持讨论） | `correlation`, `equal_weight`, `inverse_volatility` | `drafted` | A001, A013, A027 | 批次 4 已起草；`theory_only`；已显示组合样本外收益/波动/回撤；无独立分散化指标或优化器。 |
| `portfolio_weights_and_constraints` | 组合权重与约束 / Portfolio Weights and Constraints | `implemented` | `portfolio.py`, `ui_analysis.py` | `equal_weight`, `inverse_volatility`, `rebalancing_and_turnover` | `drafted` | P003, A001, A013 | 批次 4 已起草；2–4 只同市场；界面限制币种；权重为正、合计 100%。 |
| `equal_weight` | 等权 / Equal Weight | `implemented` | `portfolio.py`, `ui_analysis.py` | `inverse_volatility`, `portfolio_weights_and_constraints`, `diversification` | `drafted` | P003, A001, A013 | 批次 4 已起草；`1/n`；不估计收益或波动。 |
| `inverse_volatility` | 逆波动率 / Inverse Volatility | `implemented` | `portfolio.py`, `ui_analysis.py` | `volatility`, `equal_weight`, `portfolio_weights_and_constraints` | `drafted` | P003, A013, A027 | 批次 4 已起草；训练期日标准差倒数归一化；零/负/NaN 波动率报错。 |
| `rebalancing_and_turnover` | 再平衡与换手 / Rebalancing and Turnover | `needs_code_review` | `portfolio.py`, `ui_analysis.py` | `portfolio_weights_and_constraints`, `trading_costs`, `equal_weight` | `drafted` | P003, A013, A026 | 批次 4 已起草；已分三层：固定权重数学曲线、隐含每日恢复、真实换手/成本未实现。 |
| `multi_currency_portfolio` | 多币种组合 / Multi-Currency Portfolio | `theory_only` | `portfolio.py`, `ui_analysis.py`（限制同币种） | `currency_and_fx`, `correlation`, `portfolio_weights_and_constraints` | `drafted` | S001, P004, A035, S024 | 批次 4 已起草；`theory_only`；当前同市场同币种，无汇率/换算/对冲。 |

## 统计推断（9）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `sample_and_population` | 样本与总体 / Sample and Population | `needs_code_review` | `metrics.py`, `statistics.py` | `variance`, `standard_error`, `sampling_distribution` | `drafted` | A009, P003 | 批次 4 已起草；样本分母 `n−1` 已实现；总体公式未计算/显示；已分三层。 |
| `mean_and_median` | 均值与中位数 / Mean and Median | `needs_code_review` | `metrics.py`, `statistics.py` | `sample_and_population`, `standard_error`, `autocorrelation_and_stationarity` | `drafted` | A009, P003 | 批次 4 已起草；日均收益已显示；中位数未显示；已分三层。 |
| `sampling_distribution` | 抽样分布 / Sampling Distribution | `theory_only` | 无 | `standard_error`, `confidence_interval`, `t_test` | `drafted` | A009, A029, A024 | 批次 4 已起草；`theory_only`；未做重采样、模拟或分布图。 |
| `standard_error` | 标准误 / Standard Error | `needs_code_review` | `statistics.py` | `standard_deviation`, `sampling_distribution`, `t_test` | `drafted` | A009, A019, A021 | 批次 4 已起草；t 检验内部使用 `s/√n`；页面不单独显示；已分三层。 |
| `null_and_alternative_hypothesis` | 原假设与备择假设 / Null and Alternative Hypothesis | `implemented` | `statistics.py`, `ui_analysis.py` | `t_test`, `p_value`, `confidence_interval` | `drafted` | A009, A029, P003 | 批次 4 已起草；H0 均值=0；双侧；无方向选择器。 |
| `t_test` | t 检验 / t-Test | `implemented` | `statistics.py`, `ui_analysis.py` | `null_and_alternative_hypothesis`, `p_value`, `standard_error` | `drafted` | P003, A003, S016, A009 | 批次 4 已起草；单样本双侧；页面显示 p 值，不显示 t 值/自由度。 |
| `p_value` | p 值 / p-Value | `implemented` | `statistics.py`, `knowledge.py`, `ui_analysis.py` | `t_test`, `null_and_alternative_hypothesis`, `data_snooping_and_multiple_testing` | `drafted` | P003, A009, A029 | 批次 4 已起草；不是 H0 为真概率、上涨概率或盈利概率。 |
| `confidence_interval` | 置信区间 / Confidence Interval | `theory_only` | 无 | `standard_error`, `p_value`, `sampling_distribution` | `drafted` | A009, A029, A030 | 批次 4 已起草；`theory_only`；未计算/显示。 |
| `autocorrelation_and_stationarity` | 自相关与平稳性 / Autocorrelation and Stationarity | `theory_only` | 无 | `volatility`, `t_test`, `time_series_cross_validation` | `drafted` | A004, A020, A028, A019 | 批次 4 已起草；`theory_only`；无 ACF、Ljung–Box、ADF、KPSS 或单位根检验。 |

## 机器学习（8）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `features_and_targets` | 特征与标签 / Features and Targets | `implemented` | `statistics.py`, `ui_analysis.py` | `data_leakage`, `time_ordered_split`, `prediction_baseline` | `drafted` | P003, A010, A016 | 批次 4 已起草；5 个特征；次日收盘收益标签；预热和最后一行减少样本。 |
| `time_ordered_split` | 时间顺序切分 / Time-Ordered Split | `implemented` | `statistics.py` | `temporal_split`, `data_leakage`, `time_series_cross_validation` | `drafted` | P003, A005, A016 | 批次 4 已起草；`split=int(M×f)`；`train=[:split−1]`；一行间隔；测试从 `split` 起。 |
| `data_leakage` | 数据泄漏 / Data Leakage | `implemented` | `statistics.py`, `ai_context.py` | `lookahead_bias`, `features_and_targets`, `feature_scaling` | `drafted` | P003, A016, A005 | 批次 4 已起草；内置管线有防护；无通用泄漏检测器。 |
| `feature_scaling` | 特征标准化 / Feature Scaling | `implemented` | `statistics.py` | `data_leakage`, `features_and_targets`, `time_ordered_split` | `drafted` | A010, S014, P003 | 批次 4 已起草；`StandardScaler` 只在训练集拟合；折内 Pipeline。 |
| `prediction_baseline` | 预测基线 / Prediction Baseline | `implemented` | `statistics.py`, `ui_analysis.py` | `mae_and_rmse`, `r_squared`, `features_and_targets` | `drafted` | P003, A010 | 批次 4 已起草；只实现零收益基线；不是随机森林或交易策略基准。 |
| `mae_and_rmse` | 平均绝对误差与均方根误差 / MAE and RMSE | `needs_code_review` | `statistics.py`, `ui_analysis.py` | `prediction_baseline`, `r_squared` | `drafted` | P003, A010, A029 | 批次 4 已起草；MAE 已显示；RMSE 未计算/显示；已分三层，不拆分 ID。 |
| `r_squared` | 决定系数 R² / R-squared | `implemented` | `statistics.py`, `knowledge.py`, `ui_analysis.py` | `mae_and_rmse`, `prediction_baseline`, `overfitting` | `drafted` | P003, A010 | 批次 4 已起草；样本外 R² 可为负；分母是测试均值；常数目标按 `force_finite` 返回 0/1。 |
| `time_series_cross_validation` | 时间序列交叉验证 / Time Series Cross-Validation | `implemented` | `statistics.py` | `time_ordered_split`, `temporal_split`, `data_leakage` | `drafted` | P003, S015, A005, A016 | 批次 4 已起草；训练内 3 折、`gap=1`；每折新 Pipeline；不是完整 walk-forward。 |

## Python、数据处理与工程（20）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python_values_and_types` | Python 值与类型 / Python Values and Types | `implemented` | `quant_lab/*.py` | `python_control_flow`, `python_functions`, `type_hints_and_dataclasses` | `drafted` | S008, P003 | 批次 5 已起草；类型、单位、bool 子类、浮点舍入与百分数口径。 |
| `python_control_flow` | Python 控制流 / Python Control Flow | `implemented` | `quant_lab/*.py` | `python_values_and_types`, `python_functions`, `python_exceptions` | `drafted` | S008, P003 | 批次 5 已起草；`if/elif`、逐日 `for`、`while` 手数与早返回。 |
| `python_functions` | Python 函数 / Python Functions | `implemented` | `quant_lab/*.py` | `python_modules_and_packages`, `python_control_flow`, `type_hints_and_dataclasses` | `drafted` | S008, P003 | 批次 5 已起草；纯函数与网络/文件/数据库副作用分离。 |
| `python_collections` | Python 容器 / Python Collections | `implemented` | `quant_lab/*.py` | `python_values_and_types`, `pandas_series_and_dataframe`, `csv_and_json` | `drafted` | S008, P003 | 批次 5 已起草；list/dict/tuple/set 的顺序、可变性和唯一性。 |
| `python_exceptions` | Python 异常 / Python Exceptions | `implemented` | `data.py`, `processing.py`, `storage.py`, `notes.py` | `python_control_flow`, `python_functions`, `automated_testing_git_and_modular_monolith` | `drafted` | S008, P004 | 批次 5 已起草；显式错误、回滚、缓存保留旧值与名称失败边界。 |
| `python_modules_and_packages` | Python 模块与包 / Python Modules and Packages | `implemented` | `quant_lab/`, `tests/` | `python_functions`, `automated_testing_git_and_modular_monolith`, `type_hints_and_dataclasses` | `drafted` | S008, P002 | 批次 5 已起草；模块化单体、核心模块不导入 Streamlit、FastAPI 未实现。 |
| `type_hints_and_dataclasses` | 类型注解与数据类 / Type Hints and Dataclasses | `implemented` | `backtest.py`, `statistics.py`, `portfolio.py`, `market_data.py` | `python_functions`, `python_modules_and_packages`, `python_values_and_types` | `drafted` | S008, S017, P003 | 批次 5 已起草；注解不自动校验、frozen 非深度不可变、Provider Protocol。 |
| `numpy_arrays` | NumPy 数组 / NumPy Arrays | `implemented` | `backtest.py`, `statistics.py`, `learning.py` | `pandas_series_and_dataframe`, `returns_and_pct_change`, `rolling_window` | `drafted` | S010, A012, P003 | 批次 5 已起草；`isfinite`、年化因子、方向一致率和教学模拟。 |
| `pandas_series_and_dataframe` | pandas Series 与 DataFrame / pandas Series and DataFrame | `implemented` | `data.py`, `processing.py`, `metrics.py`, `statistics.py`, `portfolio.py` | `numpy_arrays`, `datetime_and_index`, `missing_data`, `rolling_window` | `drafted` | S009, A011, P003 | 批次 5 已起草；列/索引/dtype、深拷贝、筛选和向量化。 |
| `datetime_and_index` | 日期时间与索引 / Datetime and Index | `implemented` | `data.py`, `storage.py`, `ui_updates.py`, `portfolio.py` | `pandas_series_and_dataframe`, `trading_calendar`, `timezone_and_session` | `drafted` | S009, S008, P002 | 批次 5 已起草；交易日无时区、UTC 接收时间、北京时间显示。 |
| `missing_data` | 缺失数据 / Missing Data | `implemented` | `processing.py`, `statistics.py`, `portfolio.py`, `notes.py` | `data_quality_and_bias`, `pandas_series_and_dataframe`, `alignment_join_and_merge` | `drafted` | S009, P004, P003 | 批次 5 已起草；字段缺失报错、共同日期、零成交量与无插值。 |
| `returns_and_pct_change` | 收益率与 pct_change / Returns and pct_change | `implemented` | `metrics.py`, `statistics.py`, `portfolio.py` | `simple_return`, `log_return`, `rolling_window` | `drafted` | S009, P003 | 批次 5 已起草；简单收益率、首行 NaN 与 `fill_method` 边界。 |
| `rolling_window` | 滚动窗口 / Rolling Window | `implemented` | `strategy.py`, `statistics.py`, `learning.py` | `moving_average`, `pandas_series_and_dataframe`, `returns_and_pct_change` | `drafted` | S009, P003 | 批次 5 已起草；`min_periods=N`、5/20 日均线差、10 日波动率。 |
| `alignment_join_and_merge` | 对齐、连接与合并 / Alignment, Join, and Merge | `implemented` | `portfolio.py`, `research.py`, `data.py` | `datetime_and_index`, `missing_data`, `trading_calendar` | `drafted` | S009, P003 | 批次 5 已起草；组合 inner join、回测日期完全一致、拒绝重复日期。 |
| `csv_and_json` | CSV 与 JSON / CSV and JSON | `implemented` | `storage.py`, `ui.py`, `ui_research.py`, `ai_context.py` | `pandas_series_and_dataframe`, `reproducibility_and_audit`, `sqlite_and_transactions` | `drafted` | S008, S009, P004 | 批次 5 已起草；UTF-8 CSV、zlib BLOB、SHA-256、JSON 与 BOM 差异。 |
| `sqlite_and_transactions` | SQLite 与事务 / SQLite and Transactions | `implemented` | `storage.py`, `notes.py`, `migrations.py` | `schema_migration`, `hash_and_fingerprint`, `automated_testing_git_and_modular_monolith` | `drafted` | S011, S018, P004 | 批次 5 已起草；连接参数、commit/rollback/close 与本地数据库边界。 |
| `schema_migration` | Schema 迁移 / Schema Migration | `implemented` | `migrations.py`, `storage.py` | `sqlite_and_transactions`, `reproducibility_and_audit`, `hash_and_fingerprint` | `drafted` | P002, S011, S018 | 批次 5 已起草；`user_version=4`、备份、`BEGIN IMMEDIATE` 与 `stage_library` 区分。 |
| `hash_and_fingerprint` | 哈希与指纹 / Hash and Fingerprint | `implemented` | `research.py`, `storage.py`, `notes.py`, `ai_context.py` | `reproducibility_and_audit`, `schema_migration`, `data_provenance` | `drafted` | S008, P002 | 批次 5 已起草；完整 SHA-256、16 位 `audit_id` 与技术边界。 |
| `provider_api_cache_and_concurrency` | Provider、API、缓存与并发 / Provider, API, Cache, and Concurrency | `implemented` | `market_data.py`, `data.py`, `refresh.py`, `names.py`, `securities.py` | `cache_and_freshness`, `data_provenance`, `automated_testing_git_and_modular_monolith` | `drafted` | P002, P004, S001 | 批次 5 已起草；TTL、single-flight、深拷贝、等待超时与进程内边界。 |
| `automated_testing_git_and_modular_monolith` | 自动化测试、Git 与模块化单体 / Automated Testing, Git, and Modular Monolith | `implemented` | `tests/`, `ARCHITECTURE.md` | `python_modules_and_packages`, `schema_migration`, `provider_api_cache_and_concurrency` | `drafted` | P001, P002, S019, S020 | 批次 5 已起草；正文分三个独立部分；Git 非应用按钮，FastAPI 未实现。 |

## 重复、合并、缺口与待 Codex 判断

### 重复与合并建议

1. `simple_return` 与 `returns_and_pct_change`：前者是金融概念，后者是 pandas 实现；保留两篇，互相交叉引用，避免重复公式推导。
2. `temporal_split` 与 `time_ordered_split`：前者用于回测/研究切分，后者用于机器学习；保留两篇，明确“回测样本内外”与“训练/测试/交叉验证”的区别。
3. `variance`、`standard_deviation`、`volatility`：保留三篇；方差/标准差讲统计口径，波动率讲年化近似和金融解释。
4. `moving_average`、`moving_average_crossover`、`trend_following`：保留三篇；批次 3 已分别成文，`moving_average_crossover` 集中说明双均线条件，其他文章引用而不重复。
5. `correlation` 与 `covariance`：保留两篇；相关矩阵、协方差矩阵和组合权重的单位/解释分别说明。
6. `overfitting` 与 `data_snooping_and_multiple_testing`：保留两篇；前者讲样本内拟合噪声，后者讲反复检验/多重比较。
7. `lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`：两个 ID 都混合了“已实现的一部分”和“未实现的一部分”；批次 3 已按三层写成，并明确整手/固定滑点已实现、碎股/订单簿/容量/市场冲击未实现。是否在后续版本拆分 ID，待 Codex 判断。
8. `automated_testing_git_and_modular_monolith`：复合 ID；批次 5 正文已分成“自动化测试”“Git”“模块化单体”三个独立部分，并明确测试、版本控制和架构是三个不同概念。首版保留 ID 以控制文章数量，未来仍可拆分。
9. `mae_and_rmse`、`mean_and_median`、`sample_and_population`、`standard_error`、`cash_position_and_pnl`、`trading_calendar`、`timezone_and_session`：这些 ID 包含部分未显示或未建模的内容；批次 3–4 已对其中多数分层说明，其余文章在后续修订中必须明确“软件当前显示/计算什么”，不要把未显示的部分写成按钮或指标。
10. `returns_and_pct_change` 与 `simple_return`：前者讲 pandas 实现和首行 NaN，后者讲金融概念和首尾价格；两篇交叉引用，不重复整篇公式推导。
11. `provider_api_cache_and_concurrency` 与 `cache_and_freshness`：前者讲 Provider、single-flight 和并发边界，后者讲 TTL、来源与新鲜度；两篇都提缓存，但前者侧重实现机制，后者侧重数据状态解释。

### 内容缺口

- 方向一致率、超参数、模型过拟合不单独设 ID；按交接文档放入最相关文章的相关知识与常见误解部分。
- 市场微观结构目前只有 `slippage_liquidity_market_impact` 一个入口；订单簿、队列、盘中停牌和 VCM 细节在回测边界中说明，未来可扩展。
- 组合优化目前只有 `portfolio_weights_and_constraints`、`equal_weight`、`inverse_volatility`；均值-方差优化、风险平价和因子模型暂不设 ID。
- 公司行动现金流目前归入 `corporate_actions` 和 `price_adjustment`；分红、拆股、供股等细分未来可扩展。
- 数据库迁移目前只有 `schema_migration` 和 `sqlite_and_transactions`；备份/恢复流程在 `research_notes` 和工程文章中说明。
- Python、数据处理与工程 20 篇已在批次 5 完成；后续缺口主要是全局术语统一、交叉链接、来源逐条核验，以及是否把复合词条拆成更细 ID。

### 待 Codex 复核（优先级从高到低）

1. **使用手册外壳与改名**：`ui.py` 顶栏仍显示“新手使用指引”；产品决定改为“使用手册”，并采用“快速开始/功能说明/专业知识库”三入口。`ui_guidance.py` 仍是旧学习中心分区。手册 `workspace` 标记 `needs_code_review`。
2. **设置标签**：`ui_settings.py` 仍显示“新手模式（关闭为专业模式）”；目标为“显示详细解释提示”，只影响提示密度。手册已使用目标标签，需同步 UI 和测试。
3. **Academy 旧入口**：`ui_learning.py` 仍有“到学习中心保存实验与测验”按钮；目标版本不再承担进度/测验。手册未描述该按钮，接入时需移除或替换。
4. **DeepSeek 面板文案与按钮重命名**：`ui_ai.py` 提示“请在本页上方‘DeepSeek 连接设置’配置密钥”，但面板没有连接控件，实际在 `⚙` → DeepSeek；同时 `ui_deepseek.py` 的“保存选定回答到学习笔记”需按目标版本改为“保存选定回答到研究笔记”，并同步成功/错误提示。
5. **Academy 过拟合课程知识解释**：第 8 课没有 `readings`，`render_knowledge("bias", None)` 会显示“没有足够计算值”。手册已说明以表格/结论为准；是否需要传入模拟结果，待 Codex 判断。
6. **13 个 `needs_code_review` 专业词条**：`trading_calendar`、`timezone_and_session`、`currency_and_fx`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean`、`lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`、`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`。不拆分 ID，总数保持 85。
7. **复合词条文章分层规则**：批次 2 已对五个 `needs_code_review` 词条分节；批次 3 已对 `lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl` 分三层说明；批次 4 已对 `rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse` 分三层说明。后续批次仍须分别写清“已实现/已显示”“只间接使用”“未实现/未建模”三部分；不得把整手、固定滑点、MAE、均值、样本方差、CNY/HKD 标注、固定权重数学曲线、t 检验内部标准误等已实现部分误写成 theory_only，也不得把碎股、市场冲击、RMSE、中位数、总体公式、汇率换算、跨币种组合、抽样分布图、置信区间、ACF/ADF 等未实现部分写成按钮或指标。
8. **港股代码位数**：`normalize_symbol` 接受 1–5 位并补足五位，但侧栏提示写“港股请输入 5 位”。手册已同时说明；是否统一提示，待 Codex 判断。
9. **外部来源**：S001–S007 官方入口已由 Codex 于 2026-10-22 确认可访问，S023、S024 官方入口已由 Codex 于 2026-10-23 确认可访问，但接口字段、条款和生效口径仍待逐项核验；S008–S022 仍待核验；A032–A035 书目/DOI/ISBN 已于 2026-10-23 核验，A001–A031 仍待核验。批次 2–5 的 85 篇文章状态为 `drafted`，外部来源未逐条读取，不能标 `source_checked`；批次 5 未新增来源编号；发布前更新 `official.md`、`academic.md` 和文章核验日期。
10. **GUI 验收**：本批次只写文档，未启动 WebView，也未核对实际 DOM。Codex 接入手册内容后，必须按 AGENTS.md 做真实 WebView DOM/控件验收，不能把编译、健康检查或窗口显示当作通过。
11. **批次 3 代码事实复核**：确认三种策略条件、`run_backtest` 的 `i` 与 `i-1` 信号索引、基准第二个交易日开盘买入、`split=int(N×train_fraction)`、样本外统计从 `split−1` 起、`split_date=date[split]`、参数敏感性跳过 `short>=long` 与 `long>=len(raw_train)`、`audit_id` 的五类输入，以及实验档案未保存源码提交/输入契约版本。另确认 A 股 `i <= last_buy_index` 的 T+1 检查是防御性代码：当前日线每天最多一笔订单，正常流程不会同日买卖，不应把 T+1 与零成交量、涨跌停并列为当前可观察的 `blocked` 原因。当前文章按 2026-10-23 本地代码写成，仍需 Codex 逐项复核。
12. **批次 4 代码事实复核**：确认组合页 `align_closes` 的 2–4 只、共同收盘日 ≥8 天、日期内连接；确认 `returns.cov()/corr()` 使用全部共同日期收益且样本口径 `ddof=1`；确认 `split=int(len(returns)×f)`、权重只用训练收益、`test @ equal`/`test @ inverse` 与样本外起点归一化；确认 `inverse_volatility_weights` 对零/负/NaN 波动率报错；确认 `analyze_portfolio` 不掌握币种、同币种限制只在界面。确认 `one_sample_return_test` 至少 3 个收益、`std(ddof=1)`、`ttest_1samp(popmean=0.0)` 默认双侧、零标准差返回 `None`、页面只显示 p 值。确认 `supervised_frame` 的五个特征、次日收盘标签、零成交量替换和 `dropna`；确认 `evaluate_linear_model` 的 60 行门槛、`split-1` 间隔、训练 30/测试 10 行门槛、`TimeSeriesSplit(3,gap=1)` 折内新 Pipeline、MAE/零收益基线/R²/方向一致率口径，以及 RMSE 未实现。当前文章按 2026-10-23 本地代码写成，仍需 Codex 逐项复核。
13. **批次 5 代码事实复核**：确认 `bool` 是 `int` 子类但金融参数校验不应把 `True` 当 `1`；确认 `HistoryCache` 15 分钟/64 条、`SnapshotCache` 5 分钟/1 秒间隔、名称 24 小时/5 分钟冷却、`RefreshCache` 60 秒等待和 `NameCache` 30 秒等待；确认 `force=True` 绕过 TTL 但仍合并同键并发；确认缓存读取和页面重绘不更新上游成功时间；确认 `SCHEMA_VERSION=4`、高版本拒绝、backup API 和 `BEGIN IMMEDIATE`；确认 `stage_library` 的 `integrity_check` 与临时 bootstrap 文件替换；确认 `audit_id` 只取 SHA-256 前 16 个十六进制字符，完整 SHA-256 另存 `raw_sha256`/`signal_sha256`；确认 `automated_testing_git_and_modular_monolith` 的三部分没有把 Git 写成应用功能、没有把 FastAPI 写成已实现。当前文章按 2026-10-23 本地代码写成，仍需 Codex 逐项复核。

## 计数与验收

| 项目 | 数量 | 状态 |
| --- | --- | --- |
| 使用手册 | 10 | 全部有草稿；8 篇 `source_checked`，2 篇 `review_needed`（`workspace`, `academy`） |
| 专业词条 | 85 | 全部列入目录；85 篇 `drafted`，0 篇 `todo` |
| 合计内容项 | 95 | 与交接文档一致 |
| `drafted` 专业文章 | 85 | `market_data` 10、`return_risk` 10、`strategy_execution` 10、`backtest_research` 10、`portfolio` 8、`statistics` 9、`machine_learning` 8、`programming_engineering` 20 |
| `todo` 专业文章 | 0 | 批次 5 已完成 Python 与工程 20 篇 |
| `source_checked` 专业文章 | 0 | 外部来源未逐条读取，不能标 `source_checked` |
| 批次 2 专业文章状态 | 20 | `implemented` 13、`needs_code_review` 5、`theory_only` 2；全部 `drafted` |
| 批次 3 专业文章状态 | 20 | `implemented` 13、`needs_code_review` 3、`theory_only` 3、`academy_demo` 1；全部 `drafted` |
| 批次 4 专业文章状态 | 25 | `implemented` 15、`needs_code_review` 5、`theory_only` 5；全部 `drafted` |
| 批次 5 专业文章状态 | 20 | `implemented` 20；全部 `drafted`；不表示软件提供独立 Python/Git/数据库教学工具 |
| 批次 4 新增来源 | 0 | 沿用现有 S/P/A；外部来源未逐条读取 |
| 批次 5 新增来源 | 0 | 沿用 S008–S011、S017–S020、P001–P004、A011、A012 等现有来源 |
| `implemented` 专业词条 | 61 | 逐行统计；见各分类表 |
| `theory_only` 专业词条 | 10 | `corporate_actions`, `log_return`, `mean_reversion`, `walk_forward_analysis`, `data_snooping_and_multiple_testing`, `diversification`, `multi_currency_portfolio`, `sampling_distribution`, `confidence_interval`, `autocorrelation_and_stationarity` |
| `academy_demo` 专业词条 | 1 | `overfitting` |
| `needs_code_review` 专业词条 | 13 | `trading_calendar`, `timezone_and_session`, `currency_and_fx`, `data_quality_and_bias`, `arithmetic_vs_geometric_mean`, `lot_size_and_fractional_shares`, `slippage_liquidity_market_impact`, `cash_position_and_pnl`, `rebalancing_and_turnover`, `sample_and_population`, `mean_and_median`, `standard_error`, `mae_and_rmse` |
| `needs_code_review` 手册章节 | 1 | `workspace` |
| 外部来源 | S001–S024 | S001–S007 入口已由 Codex 于 2026-10-22 确认可访问；S023、S024 入口已由 Codex 于 2026-10-23 确认可访问；S008–S022 待核验；具体字段/条款按文章需要核验 |
| 项目内来源 | P001–P006 | 已只读核对 |
| 学术来源 | A001–A035 | A032–A035 书目/DOI/ISBN 已核验；A001–A031 书目信息待复核，标记 `NEEDS_REVIEW` |
