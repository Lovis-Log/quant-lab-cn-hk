# 来源映射与用途

日期：2026-10-22；批次 2 修订来源状态更新：2026-10-23；批次 3 文章映射：2026-10-23

## 映射原则

1. **软件行为**以本地代码和 `P` 项目文档为准；外部 `S` 来源用于接口、交易规则和软件 API 的背景，不替代代码事实。
2. **定义、公式和统计假设**优先引用 `A` 学术来源或 `S` 官方文档；文章必须独立归纳，不复制原文。
3. 会变化的交易规则、费用、数据接口和模型 API 在正式发布前重新核验；未核验的页面在 `official.md` 中标 `NEEDS_REVIEW`。
4. `CATALOG.md` 为每个专业词条列出主要来源编号；本文件补充批次 1 手册的具体主张和代码依据。

## 批次 1 手册来源映射

| 手册 ID | 主要来源 | 支持的具体主张 |
| --- | --- | --- |
| `quick_start` | P001, P002, P003, P004, S001, S002, S003, A006 | 资料库创建与迁移；代码规范化；历史日线加载与来源；收盘信号与下一开盘成交；费用/滑点/整手/涨跌停假设；实验保存、复算与过拟合边界 |
| `workspace` | P001, P002, P005, S012, S022 | 顶栏、左侧导航、三个停靠面板、设置标签、资料库路径、WebView2、Windows 凭据管理器；面板布局只存本机 WebView |
| `market_data` | S001, S013, P002, P003, P004 | A 股/港股接口与回退；字段和币种；复权口径；15 分钟历史缓存、5 分钟快照缓存；名称 24 小时缓存/5 分钟冷却；候选目录；自选股 10 只上限 |
| `strategy` | P003, P002, A008 | 三种均线规则的条件；`min_periods=N` 预热；信号变化标记；收盘信号最早下一开盘成交；只做多、不加杠杆 |
| `backtest` | P003, P002, S002, S003, S004, A006, A007 | 下一开盘成交；买卖滑点公式；费用公式；A 股 T+1 与简化涨跌停；港股交易单位用户输入且未模拟 VCM；同成本基准；样本内外切分；参数敏感性仅样本内；过拟合和数据窥探 |
| `risk_portfolio` | P003, P002, A001, A013, A009 | 样本方差/标准差；年化 `√252`；最大回撤；2–4 只同市场同币种；共同交易日内连接；等权/逆波动率；固定权重每日再平衡且未计调仓成本；不处理汇率 |
| `statistics_ml` | P003, S015, S016, A003, A004, A005, A010 | 单样本 t 检验零假设；p 值解释；五个特征和次日标签；训练/测试按时间排序并留一行间隔；训练集内 3 折 `TimeSeriesSplit(gap=1)`；标准化只在训练集；MAE/零收益基线/R²/方向一致率 |
| `academy` | P003, P005, A002, A009 | 八节固定教学样本；参数范围和默认值；方差分母 `n−1`；最大回撤路径；夏普年化；相关系数；过拟合模拟；教学样本不是行情 |
| `deepseek` | S005, S006, S007, S022, P002, P003 | 官方模型列表；JSON 输出；Key 只进会话或 Windows 凭据管理器；付费请求仅显式触发；上下文白名单；模型不能执行代码/下单/改文件 |
| `research_notes` | P002, P004, S011, S018 | 分类最多 8 层；草稿自动保存；附件 200MB/20 个/1GB 限制；SHA-256 校验；回收站；实验两份 CSV 快照与指纹；复算只读归档；ZIP 内容 |

## 批次 1 代码依据

以下代码位置用于核对 `implemented` 声明；行号以 2026-10-22 的 `codex/learning-center-v2` 工作树为准。

| 手册 ID | 代码位置 | 核对内容 |
| --- | --- | --- |
| `quick_start` | `quant_lab/ui.py:256-366`, `quant_lab/ui.py:745-842`, `quant_lab/ui_settings.py:55-92`, `quant_lab/ui_strategy.py:142-264`, `quant_lab/ui_research.py:213-308` | 左侧研究参数、资料库设置、回测运行与保存、研究笔记复算/导出 |
| `workspace` | `quant_lab/ui.py:48-243`, `quant_lab/ui.py:413-484`, `quant_lab/ui_settings.py:67-92` | 顶栏按钮、面板拖宽/排序/最大化、左侧导航开关、设置标签 |
| `market_data` | `quant_lab/ui.py:256-366`, `quant_lab/ui.py:510-695`, `quant_lab/ui_updates.py:61-93`, `quant_lab/data.py:61-198`, `quant_lab/names.py:42-121`, `quant_lab/ui_terminal.py:16-84` | 加载与校验、来源/缓存状态、复权、自选股、名称缓存 |
| `strategy` | `quant_lab/strategy.py:8-52`, `quant_lab/ui_strategy.py:21-91` | 三种策略条件、窗口校验、预热、信号变化标记、最近 30 行表格 |
| `backtest` | `quant_lab/backtest.py:14-169`, `quant_lab/research.py:26-90`, `quant_lab/ui_strategy.py:94-264`, `quant_lab/storage.py:80-124` | 成交、费用、滑点、T+1、涨跌停、基准、样本切分、敏感性、保存实验 |
| `risk_portfolio` | `quant_lab/portfolio.py:19-78`, `quant_lab/ui_analysis.py:19-115`, `quant_lab/metrics.py:58-79` | 共同日期、权重、相关/协方差、样本外曲线、单资产风险 |
| `statistics_ml` | `quant_lab/statistics.py:44-128`, `quant_lab/ui_analysis.py:118-207` | t 检验、特征/标签、切分/间隔、交叉验证、标准化、MAE/R²/方向一致率 |
| `academy` | `quant_lab/learning.py:25-109`, `quant_lab/ui_learning.py:11-54` | 八节课程、参数范围、固定教学数据、知识解释 |
| `deepseek` | `quant_lab/ui_settings.py:79-80`, `quant_lab/ui_deepseek.py:103-278`, `quant_lab/deepseek.py:21-235`, `quant_lab/ai_research.py:38-159`, `quant_lab/credentials.py:50-88` | 设置控件、付费请求、模型列表、JSON 验证、上下文白名单、凭据存储 |
| `research_notes` | `quant_lab/ui_research.py:60-308`, `quant_lab/notes.py:22-415`, `quant_lab/storage.py:138-216` | 分类、草稿、附件、回收站、实验复算、ZIP、快照校验 |

## 批次 2 文章来源映射

| 文章 ID | 主要来源 | 支持的具体主张 |
| --- | --- | --- |
| `instrument_identity` | S001, S013, P004 | 代码规范化规则；名称/目录只作身份辅助；不验证上市状态；目录快照时间和限制 |
| `ohlcv` | S001, P004, A032 | 开高低收/成交量/成交额字段、单位、验证关系；日线不是实时行情；价格与收益率区别 |
| `trading_calendar` | S001, S002, S003, P004 | 实际交易日来自上游；区间过滤/排序/去重；组合共同日期；252 是近似；无独立日历服务 |
| `timezone_and_session` | S023, S001, S002, S003, P002 | UTC 存储、北京时间显示；`received_at` 不是报价时间；无交易时段模型 |
| `currency_and_fx` | S024, S001, P004, A035 | CNY/HKD 标注；同币种组合限制；不做汇率换算；本地收益与汇率收益分解 |
| `price_adjustment` | S001, P003, P004, A033 | 不复权/前复权/后复权；复权信号与不复权成交分离；复权非总回报 |
| `corporate_actions` | S001, P004, A033, A032 | 分红/拆股/送股/配股概念；软件未实现公司行动台账和现金流 |
| `data_provenance` | S001, P002, P004, A034 | 来源、接收时间、缓存、复权、币种；FAIR 和可复现边界 |
| `cache_and_freshness` | S001, P002, P004, S008 | 15 分钟历史缓存/64 条；5 分钟快照；名称 24 小时/5 分钟冷却；失败保留旧值 |
| `data_quality_and_bias` | S001, P003, P004, A006, A016, A022, A034 | 字段校验；缺失自然日/交易日/停牌/重复/异常值/幸存者/前视偏差的区分 |
| `simple_return` | P003, A009, A032 | 价格收益率公式；百分数/小数；不含分红/费用；区间首尾收益率 |
| `log_return` | A032, A020, A009 | 对数收益率定义、可加性、与简单收益率差异；软件未实现 |
| `compound_return` | P003, P005, A009, A032 | 多期乘法、复利、先涨后跌、回本不对称 |
| `annualized_return` | P003, A009, A032 | 252/n 几何年化；收益间隔数；短样本放大；不是未来预测 |
| `arithmetic_vs_geometric_mean` | P003, A009, A032, A013 | 算术/几何均值差异；夏普分子与年化收益的不同口径；无并列 UI |
| `variance` | P003, A009 | 样本方差 `n−1`、总体方差 `n`；小数/百分数单位；方差不是百分比 |
| `standard_deviation` | P003, A009 | 标准差是方差平方根；样本/总体分母；年化波动率基础 |
| `volatility` | P003, A009, A020, A022 | 日标准差 × `√252`；历史波动不是方向/未来预测；厚尾和波动聚集 |
| `maximum_drawdown` | P003, A014, A026 | 运行峰值、回撤、最大回撤、恢复涨幅；路径依赖 |
| `sharpe_ratio` | P003, A002, A009, A026 | 日超额均值/样本标准差 × `√252`；默认无风险利率 0；零波动不显示 |

## 批次 2 代码依据

| 文章 ID | 代码位置 | 核对内容 |
| --- | --- | --- |
| `instrument_identity` | `market_data.py:20-36`, `securities.py`, `names.py:42-121` | 代码规范化、候选目录、名称缓存和身份边界 |
| `ohlcv` | `processing.py:17-58`, `ui.py:510-520`, `ui.py:671-695` | 字段验证、表格/CSV、单位和图表 |
| `trading_calendar` | `processing.py:42-58`, `data.py:148-165`, `portfolio.py:19-35`, `research.py:26-64` | 日期过滤/排序/去重、缓存键、共同日期、样本切分 |
| `timezone_and_session` | `ui_updates.py:51-79`, `data.py:105-125`, `ui.py:289-299` | UTC 存储、北京时间显示、日期默认值和快照窗口 |
| `currency_and_fx` | `data.py:79-101`, `portfolio.py:19-35`, `ui.py:528-530` | CNY/HKD 标签、同币种组合约束、价格/金额单位 |
| `price_adjustment` | `data.py:71-111`, `ui.py:300`, `ui_strategy.py:131-139` | 三种复权口径、复权信号、不复权成交 |
| `corporate_actions` | 无独立实现；`data.py` 复权参数、`docs/DATA.md` | 当前软件未实现公司行动台账；仅复权价格间接体现 |
| `data_provenance` | `data.py:25-44`, `refresh.py:9-67`, `ui_updates.py:61-93`, `storage.py:80-124` | 来源、接收时间、缓存、更新结果和实验快照 |
| `cache_and_freshness` | `data.py:138-198`, `refresh.py:19-67`, `names.py:42-99` | TTL、单飞、失败保留、名称缓存和快照节流 |
| `data_quality_and_bias` | `processing.py:17-58`, `statistics.py:44-128`, `portfolio.py:19-35` | 字段校验、缺失处理、时间切分和共同日期 |
| `simple_return` | `metrics.py:30-55`, `knowledge.py:21-27`, `ui.py:555-586` | 首尾收盘价收益率、知识解释和页面指标 |
| `log_return` | 无独立实现 | 当前软件未实现对数收益率 |
| `compound_return` | `metrics.py:58-79`, `learning.py:69-82`, `knowledge.py:28-33` | 净值累计收益、复利课程和知识解释 |
| `annualized_return` | `metrics.py:58-79`, `knowledge.py:95-100` | `(V_end/V_start)^(252/n)−1`、252 假设 |
| `arithmetic_vs_geometric_mean` | `statistics.py:44-60`, `metrics.py:58-79`, `knowledge.py` | 日均收益、几何年化、夏普分子 |
| `variance` | `metrics.py:58-79`, `statistics.py:44-60`, `ui_analysis.py:26-39`, `knowledge.py:40-45` | 样本方差 `ddof=1`、风险页显示和知识解释 |
| `standard_deviation` | `metrics.py:58-79`, `knowledge.py:46-51`, `ui_analysis.py:26-39` | 样本标准差、年化波动率和风险页 |
| `volatility` | `metrics.py:73-79`, `knowledge.py:52-57`, `ui_analysis.py:26-34` | 日标准差 × `√252`、年化波动率 |
| `maximum_drawdown` | `metrics.py:70`, `knowledge.py:58-63`, `ui_analysis.py:33` | 运行峰值、回撤、最大回撤 |
| `sharpe_ratio` | `metrics.py:73-79`, `knowledge.py:64-69`, `ui_strategy.py:186-190` | 日超额均值/样本标准差 × `√252`；默认无风险利率 0 |

## 批次 3 文章来源映射

| 文章 ID | 主要来源 | 支持的具体主张 |
| --- | --- | --- |
| `signal_position_order_trade` | P002, P003, P004 | 信号、目标持仓、订单、成交、持仓和每日估值的分层；下一开盘成交 |
| `moving_average` | P003, P005, A008 | 简单移动平均公式、`min_periods=N`、预热和窗口约束 |
| `moving_average_crossover` | P003, P005, A008 | `dual_ma` 的短均线 > 长均线条件和严格大于边界 |
| `trend_following` | P003, P005, A008 | 收盘价 > 长均线且长均线较前一日上升 |
| `mean_reversion` | A008, A020 | 均值回归假说、z 分数和自相关/非平稳性背景；当前未实现 |
| `lookahead_bias` | P003, P004, A016 | 收盘信号、下一开盘成交、复权信号与原始成交、时间切分 |
| `next_open_execution` | P003, P004, S002, S003 | 信号 t、成交 t+1 开盘；交易规则和交易日背景 |
| `lot_size_and_fractional_shares` | S002, S003, P003, P004 | 整数交易单位、碎股未实现、港股每手数量用户输入 |
| `trading_costs` | S002, S003, P003 | 佣金、最低佣金、附加费和滑点公式；默认值为研究假设 |
| `slippage_liquidity_market_impact` | S002, S003, P003, A016 | 固定基点滑点；订单簿、容量和市场冲击未实现 |
| `benchmark` | P003, A006 | 同成本买入持有；第二个交易日开盘尝试买入；不强制末日平仓 |
| `equity_curve` | P003, A026 | `equity=cash+shares×不复权收盘`；每日估值和回撤基础 |
| `cash_position_and_pnl` | P003, P004, A026 | 每日 cash/shares/equity；独立 PnL 列未提供 |
| `in_sample_out_of_sample` | P003, A006, A016 | `split=int(N×train_fraction)`；测试从 `split−1` 净值起；`split_date=date[split]` |
| `temporal_split` | P003, A005, A016 | 按时间切分；机器学习训练/测试一行间隔 |
| `walk_forward_analysis` | P003, A005, A006, A016 | 滚动训练/测试概念；当前只有单次切分和训练期 3 折 CV |
| `parameter_sensitivity` | P003, A006, A016 | 仅样本内 3×3 网格；跳过无效窗口 |
| `overfitting` | P003, P005, A006, A018 | Academy 固定模拟；无自动过拟合检测器 |
| `data_snooping_and_multiple_testing` | P003, A007, A015, A016 | 数据窥探、多重检验和显著性阈值；当前未校正 |
| `reproducibility_and_audit` | P002, P004, S011, A034 | 快照、指纹、复算、ZIP 和实验档案字段；未保存源码提交/输入契约版本 |

## 批次 3 代码依据

行号以 2026-10-23 的 `codex/learning-center-v2` 工作树为准；复核时以符号名和测试为准。

| 文章 ID | 代码位置 | 核对内容 |
| --- | --- | --- |
| `signal_position_order_trade` | `strategy.py:34-52`, `backtest.py:96-162`, `ui_strategy.py:44-91` | 信号、决策、订单、成交、持仓和估值字段 |
| `moving_average` | `strategy.py:28-52`, `learning.py:31-35`, `ui_strategy.py:64-90` | SMA、`min_periods=N`、窗口约束和图表 |
| `moving_average_crossover` | `strategy.py:21-25`, `strategy.py:43-46`, `ui_strategy.py:21-41` | `dual_ma` 条件和短/长窗口校验 |
| `trend_following` | `strategy.py:47-50` | 收盘价 > 长均线且长均线 `diff()>0` |
| `mean_reversion` | 无独立实现；`strategy.py` 仅三种策略 | 当前软件未实现均值回归 |
| `lookahead_bias` | `strategy.py:34-52`, `research.py:42-63`, `backtest.py:96-99`, `statistics.py:63-80` | 信号时序、下一开盘决策、特征/标签时序 |
| `next_open_execution` | `backtest.py:96-99`, `backtest.py:146-149`, `research.py:42-44` | `i` 日使用 `i-1` 信号；`decision_date` 与 `date` |
| `lot_size_and_fractional_shares` | `backtest.py:118-141`, `ui_strategy.py:99-102` | 整数手数、资金递减、卖出全部持股和交易单位输入 |
| `trading_costs` | `backtest.py:14-65`, `backtest.py:118-141`, `ui_strategy.py:94-128` | 默认参数、费用公式和 UI 输入 |
| `slippage_liquidity_market_impact` | `backtest.py:14-38`, `backtest.py:118-141`, `ui_strategy.py:115-118` | 固定基点滑点、零成交量阻止和参数范围 |
| `benchmark` | `backtest.py:165-169`, `research.py:44` | 常数 1 信号；第二个交易日开盘尝试买入；不强制平仓 |
| `equity_curve` | `backtest.py:154-160`, `metrics.py:58-79`, `ui_strategy.py:200-222` | 每日 `cash+shares×close`、指标和净值图 |
| `cash_position_and_pnl` | `backtest.py:90-160`, `storage.py:80-124` | 每日现金/股数/净值；订单和指标保存；无独立 PnL 列 |
| `in_sample_out_of_sample` | `research.py:45-63`, `ui_strategy.py:149`, `ui_strategy.py:211-222` | `split`、`split_date`、训练/测试统计和图中切分线 |
| `temporal_split` | `research.py:45-62`, `statistics.py:83-128` | 回测切分；机器学习训练/测试和一行间隔 |
| `walk_forward_analysis` | `research.py:45-62`, `statistics.py:98-106` | 当前只有单次切分和训练期 `TimeSeriesSplit(3, gap=1)` |
| `parameter_sensitivity` | `research.py:67-90`, `ui_strategy.py:232-241` | 样本内网格、跳过条件和输出列 |
| `overfitting` | `learning.py:61-65`, `learning.py:103-109`, `ui_learning.py:11-31` | Academy 第 8 课固定模拟和结论 |
| `data_snooping_and_multiple_testing` | `statistics.py:44-60`, `research.py:67-90` | 单次 t 检验和参数网格；无多重检验校正 |
| `reproducibility_and_audit` | `research.py:50-63`, `storage.py:80-216`, `ui_research.py:266-282` | 指纹输入、快照、复算、报告和 ZIP |

## 专业词条来源分配

`CATALOG.md` 已为 85 个词条逐行列出主要来源。批次 2–3 已撰写市场与数据、收益与风险、策略与执行、回测与研究共 40 篇；其余 45 篇仍为 `todo`。后续批次可按以下优先级补充来源：

1. **市场与数据**：S001、S013、P004；公司行动和交易规则需补充交易所/监管机构官方页面。
2. **收益与风险**：A009、A014、A002、P003；年化交易日假设需在正文明确。
3. **策略与执行**：P003、A008、S002、S003、S004；批次 3 已完成文章映射，市场冲击和流动性仍只有概念说明。
4. **回测与研究**：A006、A007、A015、A016、P002、P003；批次 3 已完成文章映射。
5. **组合分析**：A001、A013、A025、A026、A027、P003。
6. **统计推断**：A003、A009、A019、A020、A021、A029、S016。
7. **机器学习**：A005、A010、A016、A023、S014、S015。
8. **Python 与工程**：S008、S009、S010、S011、S017、S018、S019、S020；代码架构以 P002 和 `tests/` 为依据。

## 待复核与缺口

- S001–S024 外部页面在 2026-10-23 前未逐条读取内容；S001–S007 的官方入口已由 Codex 于 2026-10-22 确认可访问，S023、S024 的官方入口已由 Codex 于 2026-10-23 确认可访问，但接口字段、条款和生效口径仍需逐项核验。批次 2–3 的 40 篇文章因此全部标 `drafted`，不标 `source_checked`。
- 新增来源 S023（IANA 时区数据库）、S024（ISO 4217 货币代码）的官方入口已确认可访问，具体规则仍按文章需要核验；A032（Campbell 等）、A034（FAIR）书目/DOI 已核验；A033（Berk 与 DeMarzo）修正 ISBN 后书目已核验；A035（Bekaert 与 Hodrick）第三版、ISBN 和 2017 出版日期已核验。批次 3 未新增来源编号。
- 批次 3 的交易费用、整手、涨跌停、T+1、零成交量和 VCM 仍按简化研究假设写作；S002、S003、S004 的具体条款未逐项核验。
- 交易费用、税率、结算、申报单位和涨跌幅规则不能只靠本项目默认值推断；当前手册只把它们写成可修改假设。
- 市场冲击、流动性、碎股、多币种组合和滚动前向分析当前没有实现；相关文章必须标记 `theory_only`，不得虚构按钮或指标。
- `S013` 候选目录只提供身份字段，不证明上市状态；文章不得把“目录中存在”写成“可交易”。
- 代码行号会随开发变化；Codex 复核时应以符号名和测试为准，行号仅作定位辅助。
