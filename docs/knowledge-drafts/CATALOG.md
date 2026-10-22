# 使用手册与专业知识库总目录

状态：批次 1（10 篇使用手册）已完成草稿；85 个专业词条已建目录，正文待后续批次
日期：2026-10-22
目标版本：Quant Lab CN/HK `2.2.0-rc.1` 的内容输入
当前代码基线：`codex/learning-center-v2`，提交 `d50cfd1`
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
- 所有 `implemented` 声明都以本地代码为依据；代码位置见 `references/source-map.md`。S001–S007 的官方入口已由 Codex 于 2026-10-22 确认可访问，但具体接口字段、条款和生效口径仍待逐项核验；S008–S022 仍待核验。
- 85 个专业词条的正文均为 `todo`；本目录只锁定 ID、标题、分类、状态、模块、关联词条和主要来源，供后续批次续写。

### Codex 批次 1 复核调整（2026-10-22）

- 以下 12 个复合或部分实现词条统一改为 `needs_code_review`，不拆分 ID，专业词条总数保持 85：`trading_calendar`、`timezone_and_session`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean`、`lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`、`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`。
- `manual/research_notes.md` 已修正草稿丢失说明：SQLite 草稿不会因清除 WebView 本地存储而删除；只有尚未同步的输入可能丢失；只有“放弃草稿”会删除数据库草稿和草稿附件。
- `manual/deepseek.md` 的目标版本“学习笔记”已统一改为“研究笔记”；程序按钮“保存选定回答到学习笔记”仍需同步重命名，记录在 `REVIEW_NOTES.md`。
- `references/official.md` 的 S001–S007 已改为“官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验”。

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
| `instrument_identity` | 证券身份与代码规范化 / Instrument Identity and Symbol Normalization | `implemented` | `market_data.py`, `securities.py`, `names.py`, `ui.py` | `ohlcv`, `currency_and_fx`, `data_provenance` | `todo` | S001, S013, P004 | 规范化与名称/目录辅助；未用交易所名录验证上市身份。 |
| `ohlcv` | 开高低收与成交量 / OHLCV | `implemented` | `processing.py`, `data.py`, `ui.py` | `instrument_identity`, `trading_calendar`, `data_quality_and_bias` | `todo` | S001, P004 | 字段校验、表格和 CSV。 |
| `trading_calendar` | 交易日历 / Trading Calendar | `needs_code_review` | `data.py`, `processing.py`, `portfolio.py` | `timezone_and_session`, `alignment_join_and_merge`, `ohlcv` | `todo` | S001, P004 | 实际交易日用于对齐；不提供独立日历服务，文章需分层说明“已使用日期/未提供日历接口”。 |
| `timezone_and_session` | 时区与交易时段 / Time Zone and Trading Session | `needs_code_review` | `data.py`, `ui_updates.py` | `trading_calendar`, `data_provenance` | `todo` | S001, S002, S003 | 接收时间存 UTC、显示北京时间；不建模盘中交易时段，文章需分层说明。 |
| `currency_and_fx` | 币种与汇率 / Currency and FX | `implemented` | `data.py`, `portfolio.py`, `ui.py` | `multi_currency_portfolio`, `instrument_identity` | `todo` | S001, P004 | 标注 CNY/HKD；组合限制同币种；不做汇率换算。 |
| `price_adjustment` | 价格复权 / Price Adjustment | `implemented` | `data.py`, `ui.py`, `ui_strategy.py` | `corporate_actions`, `simple_return`, `next_open_execution` | `todo` | S001, P004 | 三口径；信号可用复权，成交/估值用不复权。 |
| `corporate_actions` | 公司行动 / Corporate Actions | `theory_only` | 仅通过复权价格间接体现 | `price_adjustment`, `simple_return`, `data_quality_and_bias` | `todo` | S001, P004 | 未单独建模分红、拆股现金流或公司行动表。 |
| `data_provenance` | 数据来源与时间戳 / Data Provenance | `implemented` | `data.py`, `refresh.py`, `ui_updates.py`, `storage.py` | `cache_and_freshness`, `timezone_and_session`, `reproducibility_and_audit` | `todo` | S001, P002, P004 | 来源、`received_at`、缓存和更新结果。 |
| `cache_and_freshness` | 缓存与新鲜度 / Cache and Freshness | `implemented` | `data.py`, `refresh.py`, `ui_updates.py` | `data_provenance`, `provider_api_cache_and_concurrency` | `todo` | S001, P002, P004 | 历史 15 分钟/64 条，快照 5 分钟；手动绕过。 |
| `data_quality_and_bias` | 数据质量与偏差 / Data Quality and Bias | `needs_code_review` | `processing.py`, `data.py`, `docs/METHODOLOGY.md` | `missing_data`, `data_provenance`, `lookahead_bias`, `overfitting` | `todo` | S001, P003, P004, A006 | 字段校验、重复/非正/异常值已实现；幸存者偏差、前视偏差等未完全消除，文章需逐项分层。 |

## 收益与风险（10）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `simple_return` | 简单收益率 / Simple Return | `implemented` | `metrics.py`, `knowledge.py`, `ui.py` | `log_return`, `compound_return`, `returns_and_pct_change` | `todo` | P003, A009 | 首尾收盘价；不含分红/费用。 |
| `log_return` | 对数收益率 / Log Return | `theory_only` | 无 | `simple_return`, `compound_return` | `todo` | A009, A020 | 当前不使用对数收益。 |
| `compound_return` | 复合收益 / Compound Return | `implemented` | `metrics.py`, `learning.py`, `knowledge.py` | `simple_return`, `annualized_return`, `arithmetic_vs_geometric_mean` | `todo` | P005, A009 | 多期乘法；学院和净值。 |
| `annualized_return` | 年化收益 / Annualized Return | `implemented` | `metrics.py`, `knowledge.py` | `compound_return`, `arithmetic_vs_geometric_mean`, `volatility` | `todo` | P003, A009 | 252 日换算，不是预测。 |
| `arithmetic_vs_geometric_mean` | 算术平均与几何平均 / Arithmetic vs Geometric Mean | `needs_code_review` | `metrics.py`, `statistics.py` | `compound_return`, `annualized_return`, `sharpe_ratio` | `todo` | A009, A013 | 算术均值用于夏普分子、几何年化用于收益换算；无并列比较 UI，文章需说明。 |
| `variance` | 方差 / Variance | `implemented` | `metrics.py`, `statistics.py`, `knowledge.py`, `ui_analysis.py` | `standard_deviation`, `covariance`, `sample_and_population` | `todo` | P003, A009 | 样本分母 `n−1`。 |
| `standard_deviation` | 标准差 / Standard Deviation | `implemented` | `metrics.py`, `knowledge.py` | `variance`, `volatility`, `standard_error` | `todo` | P003, A009 | 样本标准差。 |
| `volatility` | 波动率 / Volatility | `implemented` | `metrics.py`, `knowledge.py`, `ui_analysis.py` | `standard_deviation`, `sharpe_ratio`, `autocorrelation_and_stationarity` | `todo` | P003, A009 | 日标准差 × `√252`。 |
| `maximum_drawdown` | 最大回撤 / Maximum Drawdown | `implemented` | `metrics.py`, `knowledge.py`, `ui_analysis.py` | `equity_curve`, `volatility`, `rebalancing_and_turnover` | `todo` | P003, A014 | 历史路径指标，非未来损失上限。 |
| `sharpe_ratio` | 夏普比率 / Sharpe Ratio | `implemented` | `metrics.py`, `knowledge.py`, `ui_strategy.py` | `volatility`, `annualized_return`, `benchmark` | `todo` | P003, A002 | 默认无风险利率 0；零波动不显示。 |

## 策略与执行（10）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `signal_position_order_trade` | 信号、持仓、订单与成交 / Signal, Position, Order, Trade | `implemented` | `strategy.py`, `backtest.py`, `ui_strategy.py` | `moving_average_crossover`, `next_open_execution`, `cash_position_and_pnl` | `todo` | P003, P004 | 信号/订单/成交分离。 |
| `moving_average` | 移动平均线 / Moving Average | `implemented` | `strategy.py`, `knowledge.py`, `learning.py` | `moving_average_crossover`, `trend_following`, `rolling_window` | `todo` | P003, A008 | `min_periods=N`。 |
| `moving_average_crossover` | 均线交叉 / Moving Average Crossover | `implemented` | `strategy.py`, `ui_strategy.py` | `moving_average`, `trend_following`, `signal_position_order_trade` | `todo` | P003, A008 | 双均线趋势。 |
| `trend_following` | 趋势跟随 / Trend Following | `implemented` | `strategy.py` | `moving_average`, `moving_average_crossover`, `mean_reversion` | `todo` | P003, A008 | 价格 > 长均线且长均线上升。 |
| `mean_reversion` | 均值回归 / Mean Reversion | `theory_only` | 无 | `trend_following`, `moving_average`, `autocorrelation_and_stationarity` | `todo` | A008, A020 | 当前未实现。 |
| `lookahead_bias` | 前视偏差 / Lookahead Bias | `implemented` | `research.py`, `backtest.py`, `statistics.py` | `next_open_execution`, `data_leakage`, `data_quality_and_bias` | `todo` | P003, A016 | 引擎强制次日开盘；无自动检测器。 |
| `next_open_execution` | 下一交易日开盘成交 / Next-Open Execution | `implemented` | `backtest.py`, `research.py` | `signal_position_order_trade`, `lookahead_bias`, `trading_costs` | `todo` | P003 | 信号 t−1，成交 t。 |
| `lot_size_and_fractional_shares` | 整手与碎股 / Lot Size and Fractional Shares | `needs_code_review` | `backtest.py`, `ui_strategy.py` | `trading_costs`, `slippage_liquidity_market_impact`, `next_open_execution` | `todo` | S002, S003, P003 | 整手已实现；碎股未实现；复合词条需 Codex 决定文章分层，不拆分 ID。 |
| `trading_costs` | 交易成本 / Trading Costs | `implemented` | `backtest.py`, `knowledge.py`, `ui_strategy.py` | `slippage_liquidity_market_impact`, `lot_size_and_fractional_shares`, `benchmark` | `todo` | S002, S003, P003 | 佣金+最低+附加费；参数可改。 |
| `slippage_liquidity_market_impact` | 滑点、流动性与市场冲击 / Slippage, Liquidity, Market Impact | `needs_code_review` | `backtest.py`, `knowledge.py` | `trading_costs`, `lot_size_and_fractional_shares`, `next_open_execution` | `todo` | S002, S003, P003, A016 | 固定基点滑点已实现；流动性与市场冲击未实现；复合词条需 Codex 决定分层，不拆分 ID。 |

## 回测与研究（10）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `benchmark` | 基准 / Benchmark | `implemented` | `backtest.py`, `research.py`, `ui_strategy.py` | `equity_curve`, `trading_costs`, `in_sample_out_of_sample` | `todo` | P003 | 同成本买入持有。 |
| `equity_curve` | 净值曲线 / Equity Curve | `implemented` | `backtest.py`, `metrics.py`, `ui_strategy.py` | `cash_position_and_pnl`, `maximum_drawdown`, `benchmark` | `todo` | P003 | 现金+持股×收盘。 |
| `cash_position_and_pnl` | 现金、持仓与盈亏 / Cash, Position, and PnL | `needs_code_review` | `backtest.py`, `storage.py` | `equity_curve`, `signal_position_order_trade`, `trading_costs` | `todo` | P003 | 现金/股数逐日记录；PnL 可推导但无单独列，文章需分层说明。 |
| `in_sample_out_of_sample` | 样本内与样本外 / In-Sample and Out-of-Sample | `implemented` | `research.py`, `ui_strategy.py` | `temporal_split`, `overfitting`, `walk_forward_analysis` | `todo` | P003, A006 | 训练/测试切分。 |
| `temporal_split` | 时间顺序切分 / Temporal Split | `implemented` | `research.py`, `statistics.py`, `portfolio.py` | `in_sample_out_of_sample`, `time_ordered_split`, `data_leakage` | `todo` | P003, A005 | 按日期，不随机。 |
| `walk_forward_analysis` | 滚动前向分析 / Walk-Forward Analysis | `theory_only` | 无 | `temporal_split`, `parameter_sensitivity`, `overfitting` | `todo` | A006, A016 | 当前只有训练期 3 折 CV，不是完整 walk-forward。 |
| `parameter_sensitivity` | 参数敏感性 / Parameter Sensitivity | `implemented` | `research.py`, `ui_strategy.py` | `overfitting`, `data_snooping_and_multiple_testing`, `in_sample_out_of_sample` | `todo` | P003, A006 | 仅样本内。 |
| `overfitting` | 过拟合 / Overfitting | `academy_demo` | `learning.py`, `guidance.py`, `research.py` | `in_sample_out_of_sample`, `parameter_sensitivity`, `data_snooping_and_multiple_testing` | `todo` | A006, A018 | 学院固定模拟演示；无自动检测。 |
| `data_snooping_and_multiple_testing` | 数据窥探与多重检验 / Data Snooping and Multiple Testing | `theory_only` | 无 | `overfitting`, `parameter_sensitivity`, `p_value` | `todo` | A007, A015 | 当前未做多重检验校正。 |
| `reproducibility_and_audit` | 可复现性与审计 / Reproducibility and Audit | `implemented` | `research.py`, `storage.py`, `ui_research.py` | `hash_and_fingerprint`, `data_provenance`, `schema_migration` | `todo` | P002, P004, S011 | 指纹、快照、复算、ZIP。 |

## 组合分析（8）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `covariance` | 协方差 / Covariance | `implemented` | `portfolio.py`, `knowledge.py`, `ui_analysis.py` | `correlation`, `variance`, `portfolio_weights_and_constraints` | `todo` | P003, A001 | 同日收益率、样本分母 `n−1`。 |
| `correlation` | 相关系数 / Correlation | `implemented` | `portfolio.py`, `knowledge.py`, `ui_analysis.py` | `covariance`, `diversification`, `multi_currency_portfolio` | `todo` | P003, A001 | 全部共同日期；不证明因果。 |
| `diversification` | 分散化 / Diversification | `theory_only` | `portfolio.py`, `ui_analysis.py`（仅相关/曲线支持讨论） | `correlation`, `equal_weight`, `inverse_volatility` | `todo` | A001, A013 | 无单独分散化指标。 |
| `portfolio_weights_and_constraints` | 组合权重与约束 / Portfolio Weights and Constraints | `implemented` | `portfolio.py`, `ui_analysis.py` | `equal_weight`, `inverse_volatility`, `rebalancing_and_turnover` | `todo` | P003, A001 | 2–4 只同市场同币种；权重和 100%。 |
| `equal_weight` | 等权 / Equal Weight | `implemented` | `portfolio.py`, `ui_analysis.py` | `inverse_volatility`, `portfolio_weights_and_constraints`, `diversification` | `todo` | P003, A001 | `1/n`。 |
| `inverse_volatility` | 逆波动率 / Inverse Volatility | `implemented` | `portfolio.py`, `ui_analysis.py` | `volatility`, `equal_weight`, `portfolio_weights_and_constraints` | `todo` | P003, A013 | 训练期标准差；零波动报错。 |
| `rebalancing_and_turnover` | 再平衡与换手 / Rebalancing and Turnover | `needs_code_review` | `portfolio.py`, `ui_analysis.py` | `portfolio_weights_and_constraints`, `trading_costs`, `equal_weight` | `todo` | P003, A013 | 曲线假设每日固定权重再平衡；换手/成本未建模；Codex 复核保留 `needs_code_review`，文章需明确分层。 |
| `multi_currency_portfolio` | 多币种组合 / Multi-Currency Portfolio | `theory_only` | `portfolio.py`, `ui_analysis.py`（限制同币种） | `currency_and_fx`, `correlation`, `portfolio_weights_and_constraints` | `todo` | S001, P004 | 当前不支持；不同币种不能直接加总。 |

## 统计推断（9）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `sample_and_population` | 样本与总体 / Sample and Population | `needs_code_review` | `metrics.py`, `statistics.py` | `variance`, `standard_error`, `sampling_distribution` | `todo` | A009 | 样本分母 `n−1` 已使用；总体公式未提供，文章需分层说明。 |
| `mean_and_median` | 均值与中位数 / Mean and Median | `needs_code_review` | `metrics.py`, `statistics.py` | `sample_and_population`, `standard_error`, `autocorrelation_and_stationarity` | `todo` | A009 | 均值已显示；中位数未显示，文章需分层说明。 |
| `sampling_distribution` | 抽样分布 / Sampling Distribution | `theory_only` | 无 | `standard_error`, `confidence_interval`, `t_test` | `todo` | A009, A003 | 未做重采样/模拟。 |
| `standard_error` | 标准误 / Standard Error | `needs_code_review` | `statistics.py` | `standard_deviation`, `sampling_distribution`, `t_test` | `todo` | A009 | 在 t 检验内部计算；不单独显示，文章需说明。 |
| `null_and_alternative_hypothesis` | 原假设与备择假设 / Null and Alternative Hypothesis | `implemented` | `statistics.py`, `ui_analysis.py` | `t_test`, `p_value`, `confidence_interval` | `todo` | A009 | 零假设均值=0；无备择假设 UI。 |
| `t_test` | t 检验 / t-Test | `implemented` | `statistics.py`, `ui_analysis.py` | `null_and_alternative_hypothesis`, `p_value`, `standard_error` | `todo` | P003, A003, S016 | 单样本双侧。 |
| `p_value` | p 值 / p-Value | `implemented` | `statistics.py`, `knowledge.py`, `ui_analysis.py` | `t_test`, `null_and_alternative_hypothesis`, `data_snooping_and_multiple_testing` | `todo` | P003, A009 | 不是 H0 为真概率/盈利概率。 |
| `confidence_interval` | 置信区间 / Confidence Interval | `theory_only` | 无 | `standard_error`, `p_value`, `sampling_distribution` | `todo` | A009 | 未计算/显示。 |
| `autocorrelation_and_stationarity` | 自相关与平稳性 / Autocorrelation and Stationarity | `theory_only` | 无 | `volatility`, `t_test`, `time_series_cross_validation` | `todo` | A004, A020 | 仅在局限中提及，无检验。 |

## 机器学习（8）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `features_and_targets` | 特征与标签 / Features and Targets | `implemented` | `statistics.py`, `ui_analysis.py` | `data_leakage`, `time_ordered_split`, `prediction_baseline` | `todo` | P003, A010 | 5 个特征；次日收盘收益标签。 |
| `time_ordered_split` | 时间顺序切分 / Time-Ordered Split | `implemented` | `statistics.py` | `temporal_split`, `data_leakage`, `time_series_cross_validation` | `todo` | P003, A005 | 训练/测试 + 一行间隔。 |
| `data_leakage` | 数据泄漏 / Data Leakage | `implemented` | `statistics.py`, `ai_context.py` | `lookahead_bias`, `features_and_targets`, `feature_scaling` | `todo` | P003, A016 | Pipeline 强制时间切分/训练集标准化；无自动泄漏检测。 |
| `feature_scaling` | 特征标准化 / Feature Scaling | `implemented` | `statistics.py` | `data_leakage`, `features_and_targets`, `time_ordered_split` | `todo` | A010 | `StandardScaler` 仅训练集拟合。 |
| `prediction_baseline` | 预测基线 / Prediction Baseline | `implemented` | `statistics.py`, `ui_analysis.py` | `mae_and_rmse`, `r_squared`, `features_and_targets` | `todo` | P003, A010 | 零收益基线 MAE。 |
| `mae_and_rmse` | 平均绝对误差与均方根误差 / MAE and RMSE | `needs_code_review` | `statistics.py`, `ui_analysis.py` | `prediction_baseline`, `r_squared` | `todo` | P003, A010 | MAE 已显示；RMSE 未显示；文章需分层说明，不拆分 ID。 |
| `r_squared` | 决定系数 R² / R-squared | `implemented` | `statistics.py`, `knowledge.py`, `ui_analysis.py` | `mae_and_rmse`, `prediction_baseline`, `overfitting` | `todo` | P003, A010 | 样本外可负。 |
| `time_series_cross_validation` | 时间序列交叉验证 / Time Series Cross-Validation | `implemented` | `statistics.py` | `time_ordered_split`, `temporal_split`, `data_leakage` | `todo` | P003, S015, A005 | 3 折，`gap=1`。 |

## Python、数据处理与工程（20）

| ID | 中文标题 / English | 功能状态 | 关联模块 | 关联词条 | 文章状态 | 主要来源 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python_values_and_types` | Python 值与类型 / Python Values and Types | `implemented` | `quant_lab/*.py` | `python_control_flow`, `python_functions`, `type_hints_and_dataclasses` | `todo` | S008 | 代码库基础。 |
| `python_control_flow` | Python 控制流 / Python Control Flow | `implemented` | `quant_lab/*.py` | `python_values_and_types`, `python_functions`, `python_exceptions` | `todo` | S008 | 条件、循环。 |
| `python_functions` | Python 函数 / Python Functions | `implemented` | `quant_lab/*.py` | `python_modules_and_packages`, `python_control_flow`, `type_hints_and_dataclasses` | `todo` | S008 | 计算函数。 |
| `python_collections` | Python 容器 / Python Collections | `implemented` | `quant_lab/*.py` | `python_values_and_types`, `pandas_series_and_dataframe`, `csv_and_json` | `todo` | S008 | dict/list/tuple/set。 |
| `python_exceptions` | Python 异常 / Python Exceptions | `implemented` | `data.py`, `processing.py`, `storage.py`, `notes.py` | `python_control_flow`, `python_functions`, `automated_testing_git_and_modular_monolith` | `todo` | S008 | 显式错误，不静默替换。 |
| `python_modules_and_packages` | Python 模块与包 / Python Modules and Packages | `implemented` | `quant_lab/`, `tests/` | `python_functions`, `automated_testing_git_and_modular_monolith`, `type_hints_and_dataclasses` | `todo` | S008 | 模块化单体。 |
| `type_hints_and_dataclasses` | 类型注解与数据类 / Type Hints and Dataclasses | `implemented` | `backtest.py`, `statistics.py`, `portfolio.py`, `market_data.py` | `python_functions`, `python_modules_and_packages`, `python_values_and_types` | `todo` | S008, S017 | 不可变配置/结果对象。 |
| `numpy_arrays` | NumPy 数组 / NumPy Arrays | `implemented` | `backtest.py`, `statistics.py`, `learning.py` | `pandas_series_and_dataframe`, `returns_and_pct_change`, `rolling_window` | `todo` | S010, A012 | 向量化/有限值。 |
| `pandas_series_and_dataframe` | pandas Series 与 DataFrame / pandas Series and DataFrame | `implemented` | `data.py`, `processing.py`, `metrics.py`, `statistics.py`, `portfolio.py` | `numpy_arrays`, `datetime_and_index`, `missing_data`, `rolling_window` | `todo` | S009, A011 | 核心数据表。 |
| `datetime_and_index` | 日期时间与索引 / Datetime and Index | `implemented` | `data.py`, `storage.py`, `ui_updates.py`, `portfolio.py` | `pandas_series_and_dataframe`, `trading_calendar`, `timezone_and_session` | `todo` | S009, S008 | 日期解析/时区/索引。 |
| `missing_data` | 缺失数据 / Missing Data | `implemented` | `processing.py`, `statistics.py`, `portfolio.py`, `notes.py` | `data_quality_and_bias`, `pandas_series_and_dataframe`, `alignment_join_and_merge` | `todo` | S009, P004 | `dropna`/校验/不静默。 |
| `returns_and_pct_change` | 收益率与 pct_change / Returns and pct_change | `implemented` | `metrics.py`, `statistics.py`, `portfolio.py` | `simple_return`, `log_return`, `rolling_window` | `todo` | S009, P003 | 百分比变化。 |
| `rolling_window` | 滚动窗口 / Rolling Window | `implemented` | `strategy.py`, `statistics.py`, `learning.py` | `moving_average`, `pandas_series_and_dataframe`, `returns_and_pct_change` | `todo` | S009, P003 | `rolling`/`min_periods`。 |
| `alignment_join_and_merge` | 对齐、连接与合并 / Alignment, Join, and Merge | `implemented` | `portfolio.py`, `research.py`, `data.py` | `datetime_and_index`, `missing_data`, `trading_calendar` | `todo` | S009, P003 | 内连接共同日期。 |
| `csv_and_json` | CSV 与 JSON / CSV and JSON | `implemented` | `storage.py`, `ui.py`, `ui_research.py`, `ai_context.py` | `pandas_series_and_dataframe`, `reproducibility_and_audit`, `sqlite_and_transactions` | `todo` | S008, S009 | CSV 快照/JSON 假设。 |
| `sqlite_and_transactions` | SQLite 与事务 / SQLite and Transactions | `implemented` | `storage.py`, `notes.py`, `migrations.py` | `schema_migration`, `hash_and_fingerprint`, `automated_testing_git_and_modular_monolith` | `todo` | S011, S018 | 事务/回滚/备份。 |
| `schema_migration` | Schema 迁移 / Schema Migration | `implemented` | `migrations.py`, `storage.py` | `sqlite_and_transactions`, `reproducibility_and_audit`, `hash_and_fingerprint` | `todo` | P002, S011 | `PRAGMA user_version`。 |
| `hash_and_fingerprint` | 哈希与指纹 / Hash and Fingerprint | `implemented` | `research.py`, `storage.py`, `notes.py`, `ai_context.py` | `reproducibility_and_audit`, `schema_migration`, `data_provenance` | `todo` | S008, P002 | SHA-256/审计指纹。 |
| `provider_api_cache_and_concurrency` | Provider、API、缓存与并发 / Provider, API, Cache, and Concurrency | `implemented` | `market_data.py`, `data.py`, `refresh.py`, `names.py`, `securities.py` | `cache_and_freshness`, `data_provenance`, `automated_testing_git_and_modular_monolith` | `todo` | P002, P004, S001 | 单飞、TTL、并发合并。 |
| `automated_testing_git_and_modular_monolith` | 自动化测试、Git 与模块化单体 / Automated Testing, Git, and Modular Monolith | `implemented` | `tests/`, `ARCHITECTURE.md` | `python_modules_and_packages`, `schema_migration`, `provider_api_cache_and_concurrency` | `todo` | P001, P002, S019, S020 | 复合词条，正文必须分节；未来可考虑拆分。 |

## 重复、合并、缺口与待 Codex 判断

### 重复与合并建议

1. `simple_return` 与 `returns_and_pct_change`：前者是金融概念，后者是 pandas 实现；保留两篇，互相交叉引用，避免重复公式推导。
2. `temporal_split` 与 `time_ordered_split`：前者用于回测/研究切分，后者用于机器学习；保留两篇，明确“回测样本内外”与“训练/测试/交叉验证”的区别。
3. `variance`、`standard_deviation`、`volatility`：保留三篇；方差/标准差讲统计口径，波动率讲年化近似和金融解释。
4. `moving_average`、`moving_average_crossover`、`trend_following`：保留三篇；信号条件只在 `strategy.md` 和 `moving_average_crossover` 中集中说明，其他文章引用而不重复。
5. `correlation` 与 `covariance`：保留两篇；相关矩阵、协方差矩阵和组合权重的单位/解释分别说明。
6. `overfitting` 与 `data_snooping_and_multiple_testing`：保留两篇；前者讲样本内拟合噪声，后者讲反复检验/多重比较。
7. `lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`：两个 ID 都混合了“已实现的一部分”和“未实现的一部分”；建议正文分节，并明确标注整手/固定滑点 `implemented`、碎股/流动性/市场冲击 `theory_only`。是否在 2.3 拆分 ID，待 Codex 判断。
8. `automated_testing_git_and_modular_monolith`：复合 ID，正文必须分成“自动化测试”“Git”“模块化单体”三节；首版保留 ID 以控制文章数量，未来可拆分。
9. `mae_and_rmse`、`mean_and_median`、`sample_and_population`、`standard_error`、`cash_position_and_pnl`、`trading_calendar`、`timezone_and_session`：这些 ID 包含部分未显示或未建模的内容；文章必须明确“软件当前显示/计算什么”，不要把未显示的部分写成按钮或指标。

### 内容缺口

- 方向一致率、超参数、模型过拟合不单独设 ID；按交接文档放入最相关文章的相关知识与常见误解部分。
- 市场微观结构目前只有 `slippage_liquidity_market_impact` 一个入口；订单簿、队列、盘中停牌和 VCM 细节在回测边界中说明，未来可扩展。
- 组合优化目前只有 `portfolio_weights_and_constraints`、`equal_weight`、`inverse_volatility`；均值-方差优化、风险平价和因子模型暂不设 ID。
- 公司行动现金流目前归入 `corporate_actions` 和 `price_adjustment`；分红、拆股、供股等细分未来可扩展。
- 数据库迁移目前只有 `schema_migration` 和 `sqlite_and_transactions`；备份/恢复流程在 `research_notes` 和后续工程文章中说明。

### 待 Codex 复核（优先级从高到低）

1. **使用手册外壳与改名**：`ui.py` 顶栏仍显示“新手使用指引”；产品决定改为“使用手册”，并采用“快速开始/功能说明/专业知识库”三入口。`ui_guidance.py` 仍是旧学习中心分区。手册 `workspace` 标记 `needs_code_review`。
2. **设置标签**：`ui_settings.py` 仍显示“新手模式（关闭为专业模式）”；目标为“显示详细解释提示”，只影响提示密度。手册已使用目标标签，需同步 UI 和测试。
3. **Academy 旧入口**：`ui_learning.py` 仍有“到学习中心保存实验与测验”按钮；目标版本不再承担进度/测验。手册未描述该按钮，接入时需移除或替换。
4. **DeepSeek 面板文案与按钮重命名**：`ui_ai.py` 提示“请在本页上方‘DeepSeek 连接设置’配置密钥”，但面板没有连接控件，实际在 `⚙` → DeepSeek；同时 `ui_deepseek.py` 的“保存选定回答到学习笔记”需按目标版本改为“保存选定回答到研究笔记”，并同步成功/错误提示。
5. **Academy 过拟合课程知识解释**：第 8 课没有 `readings`，`render_knowledge("bias", None)` 会显示“没有足够计算值”。手册已说明以表格/结论为准；是否需要传入模拟结果，待 Codex 判断。
6. **12 个 `needs_code_review` 专业词条**：`trading_calendar`、`timezone_and_session`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean`、`lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`、`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`。不拆分 ID，总数保持 85。
7. **复合词条文章分层规则**：后续文章必须分别写清“已实现/已显示”“未显示/未提供”“未实现”三部分；不得把整手、固定滑点、MAE、均值、样本方差等已实现部分误写成 theory_only，也不得把碎股、市场冲击、RMSE、中位数、总体公式等未实现部分写成按钮或指标。
8. **港股代码位数**：`normalize_symbol` 接受 1–5 位并补足五位，但侧栏提示写“港股请输入 5 位”。手册已同时说明；是否统一提示，待 Codex 判断。
9. **外部来源**：S001–S007 官方入口已由 Codex 于 2026-10-22 确认可访问，但接口字段、条款和生效口径仍待逐项核验；S008–S022 与 A001–A031 仍待核验。发布前更新 `official.md`、`academic.md` 和文章核验日期。
10. **GUI 验收**：本批次只写文档，未启动 WebView，也未核对实际 DOM。Codex 接入手册内容后，必须按 AGENTS.md 做真实 WebView DOM/控件验收，不能把编译、健康检查或窗口显示当作通过。

## 计数与验收

| 项目 | 数量 | 状态 |
| --- | --- | --- |
| 使用手册 | 10 | 全部有草稿；8 篇 `source_checked`，2 篇 `review_needed`（`workspace`, `academy`） |
| 专业词条 | 85 | 全部列入目录；正文均为 `todo` |
| 合计内容项 | 95 | 与交接文档一致 |
| `implemented` 专业词条 | 62 | 逐行统计；见各分类表 |
| `theory_only` 专业词条 | 10 | `corporate_actions`, `log_return`, `mean_reversion`, `walk_forward_analysis`, `data_snooping_and_multiple_testing`, `diversification`, `multi_currency_portfolio`, `sampling_distribution`, `confidence_interval`, `autocorrelation_and_stationarity` |
| `academy_demo` 专业词条 | 1 | `overfitting` |
| `needs_code_review` 专业词条 | 12 | `trading_calendar`, `timezone_and_session`, `data_quality_and_bias`, `arithmetic_vs_geometric_mean`, `lot_size_and_fractional_shares`, `slippage_liquidity_market_impact`, `cash_position_and_pnl`, `rebalancing_and_turnover`, `sample_and_population`, `mean_and_median`, `standard_error`, `mae_and_rmse` |
| `needs_code_review` 手册章节 | 1 | `workspace` |
| 外部来源 | S001–S022 | S001–S007 入口已由 Codex 确认可访问，字段/条款待核验；S008–S022 待核验 |
| 项目内来源 | P001–P006 | 已只读核对 |
| 学术来源 | A001–A031 | 书目信息待复核，标记 `NEEDS_REVIEW` |
