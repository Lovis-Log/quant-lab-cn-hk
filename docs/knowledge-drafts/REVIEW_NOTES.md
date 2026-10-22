# 批次 1 复核记录

日期：2026-10-22
批次：使用手册 10 篇
代码基线：`codex/learning-center-v2`，提交 `d50cfd1`
恢复分支：`codex/recovery-before-manual-batch1-20261022`（指向 `d50cfd1`）
写作范围：仅新增 `docs/knowledge-drafts/`；未修改 `quant_lab/`、`tests/`、`app.py`、`desktop_launcher.py`、`VERSION`、构建脚本、数据库或发行文件。

## 1. 本轮完成内容

- 10 篇使用手册草稿：`quick_start`、`workspace`、`market_data`、`strategy`、`backtest`、`risk_portfolio`、`statistics_ml`、`academy`、`deepseek`、`research_notes`。
- `CATALOG.md`：10 篇手册 + 85 个专业词条的稳定 ID、标题、分类、状态、模块、关联词条、文章状态和主要来源。
- `references/official.md`：S001–S022 外部官方来源；P001–P006 项目内依据。
- `references/academic.md`：A001–A031 论文、教材和大学课程。
- `references/source-map.md`：手册 ID 到来源与代码位置的映射。
- `README.md`（如已创建）：目录使用说明和批次边界。

## 2. 只读核对范围

### 交接文档列出的项目事实文件

- `README.md`
- `ARCHITECTURE.md`
- `LEARNING.md`
- `docs/METHODOLOGY.md`
- `docs/DATA.md`
- `quant_lab/knowledge.py`
- `quant_lab/guidance.py`
- `quant_lab/learning.py`
- `quant_lab/backtest.py`
- `quant_lab/statistics.py`
- `quant_lab/portfolio.py`

### 为核对控件和口径额外只读的文件

- `quant_lab/ui.py`, `ui_strategy.py`, `ui_research.py`, `ui_analysis.py`, `ui_terminal.py`, `ui_learning.py`, `ui_deepseek.py`, `ui_settings.py`, `ui_updates.py`, `ui_knowledge.py`, `ui_ai.py`
- `quant_lab/strategy.py`, `research.py`, `metrics.py`, `notes.py`, `storage.py`, `paths.py`, `ai_context.py`, `deepseek.py`, `ai_research.py`, `credentials.py`, `names.py`, `refresh.py`, `market_data.py`, `processing.py`, `data.py`

这些文件只读，没有修改。

## 3. 事实核对结果

### 已确认

- A 股历史主链路是 AKShare 腾讯接口；港股主链路是 AKShare 东方财富接口，失败时回退新浪并显示来源。
- 历史缓存 15 分钟、最多 64 条；快照缓存 5 分钟；自选股上游请求至少间隔 1 秒；手动更新绕过缓存，连续点击 5 秒防抖。
- 名称缓存 24 小时、失败冷却 5 分钟；手动“重新获取证券名称”绕过缓存和冷却。
- 证券目录内置快照接收于 2026-10-14：A 股 6,181 条、港股 3,033 条；联网更新写入用户目录。
- 策略只有单均线、双均线、趋势过滤；窗口约束 `2 ≤ 短周期 < 长周期 ≤ 250`；`min_periods=N`；信号最早下一交易日开盘成交。
- 回测只做多；A 股模拟 T+1、用户设定的整手和简化涨跌停；港股交易单位用户输入，未模拟 VCM。
- 成交价与费用公式与 `docs/METHODOLOGY.md` 和 `backtest.py` 一致；复权价格只生成信号，成交/估值使用不复权价格。
- 样本内比例 0.50–0.85；测试统计以分割日前一交易日净值为起点；参数敏感性只计算样本内。
- 组合要求 2–4 只同市场同币种，共同交易日内连接；等权/训练期逆波动率；固定权重每日再平衡，未计调仓成本、股息或汇率。
- t 检验至少 3 个有效日收益；线性回归至少 60 行有效特征，训练至少 30 行、测试至少 10 行；训练/测试按时间排序并留一行间隔；训练内 3 折 `TimeSeriesSplit(gap=1)`；标准化只在训练集拟合；MAE/零收益基线/R²/方向一致率。
- DeepSeek Key 只进会话或 Windows 凭据管理器；模型列表来自官方接口；付费请求只在“生成 AI 假设”“让 AI 审阅实验”“发送到 DeepSeek”时发生；上下文默认排除私人笔记、完整行情和数据库；模型不能执行代码、下单或修改文件。
- 研究笔记支持分类、草稿、附件、回收站、实验复算和 ZIP 导出；附件 200MB/20 个/1GB；实验两份 CSV 快照和 SHA-256；复算核对指纹。
- 资料库首次创建会复制并校验现有数据，原目录保留，按提示重启；默认 Windows 目录 `%LOCALAPPDATA%\QuantLabCNHK`。

### 与当前代码的差异（需要 Codex 处理）

1. **顶栏入口名称与手册结构**
   - 当前 `quant_lab/ui.py` 顶栏按钮是“新手使用指引”；目标 2.2.0 为“使用手册”。
   - 当前 `ui_guidance.py` 仍有“界面指南/入门任务/学习路径/课程与练习/学习进度”等旧分区；目标为“快速开始/功能说明/专业知识库”的纯阅读与检索。
   - 手册 `workspace` 已按目标结构写，功能状态标 `needs_code_review`，文章状态 `review_needed`。

2. **设置标签**
   - 当前 `quant_lab/ui_settings.py` 显示“新手模式（关闭为专业模式）”；目标为“显示详细解释提示”，只影响提示密度。
   - 手册已使用目标标签；Codex 接入时需同步 UI、帮助文本和测试。

3. **Academy 旧按钮**
   - 当前 `quant_lab/ui_learning.py` 仍有“到学习中心保存实验与测验”按钮；目标版本不再承担进度/测验。
   - 手册 `academy` 未描述该按钮，文章状态标 `review_needed`。接入时需移除或替换，并检查现有测试。

4. **DeepSeek 面板文案**
   - `quant_lab/ui_ai.py` 提示“请在本页上方‘DeepSeek 连接设置’配置密钥并选择模型”，但 `render_deepseek_panel` 没有连接控件；实际 Key/模型设置在 `⚙` → “DeepSeek”。
   - 手册按实际位置写；建议 Codex 修正文案或把连接入口放到面板内。

5. **Academy 过拟合课程的知识解释**
   - 第 8 课（`bias`）没有 `readings`，`render_knowledge("bias", None)` 会显示“当前没有足够的有效计算值”。
   - 手册说明以表格/结论为准；是否传入模拟结果或改写解释，待 Codex 判断。

6. **港股代码位数提示**
   - `normalize_symbol` 对港股接受 1–5 位数字并补足五位；侧栏提示写“港股请输入 5 位”。
   - 手册同时说明“1–5 位会补足为五位”；是否统一提示，待 Codex 判断。

7. **部分实现词条的分层**
   - `lot_size_and_fractional_shares`：整手已实现，碎股未实现，按交接文档标 `theory_only`。
   - `slippage_liquidity_market_impact`：固定基点滑点已实现，流动性和市场冲击未实现，按交接文档标 `theory_only`。
   - `rebalancing_and_turnover`：曲线假设每日固定权重再平衡，换手/成本未建模；标 `needs_code_review`，文章需决定拆分或只写假设。
   - `mae_and_rmse`：MAE 已显示，RMSE 未显示。
   - `mean_and_median`：均值已显示，中位数未显示。
   - `sample_and_population`：样本分母 `n−1` 已使用，总体公式未提供。
   - `standard_error`：t 检验内部使用，未单独显示。
   - `cash_position_and_pnl`：现金/股数逐日记录，PnL 可推导但无单独列。
   - `trading_calendar`、`timezone_and_session`：使用实际交易日和北京时间，但不提供独立交易日历/交易时段模型。

## 4. `needs_code_review` 清单

| 对象 | 问题 | 建议 |
| --- | --- | --- |
| `workspace`（手册） | 三入口、顶栏改名、设置标签尚未在当前代码实现 | Codex 接入手册内容时按目标结构改造，并做 WebView DOM 验收 |
| `rebalancing_and_turnover` | 每日固定权重再平衡已假设，换手/成本未建模 | 决定文章是否拆分“再平衡假设”和“换手成本”；不要写成完整成本模型 |
| `academy`（文章状态 `review_needed`） | 当前仍有测验/学习中心入口，目标移除 | 移除旧入口后复核测试和帮助文本 |
| `deepseek`（文案差异） | 面板提示与实际设置位置不一致 | 修正文案或调整入口；手册已按实际位置写 |
| `academy` 第 8 课 | 过拟合课程知识解释无当前值 | 决定是否传模拟结果或改写为“本课无单一指标” |
| `mae_and_rmse`、`mean_and_median`、`sample_and_population`、`standard_error`、`cash_position_and_pnl`、`trading_calendar`、`timezone_and_session` | 部分实现/部分显示 | 后续文章统一采用“已实现/未显示/未建模”分层，必要时拆 ID |
| 港股代码提示 | 1–5 位补足 vs 界面提示 5 位 | 统一文案或输入校验；不要改变 `normalize_symbol` 行为前先加测试 |

## 5. `NEEDS_REVIEW` 清单

以下项目不是软件代码问题，而是外部页面/书目未能在本轮联网核验：

1. `S001` AKShare 股票数据文档：接口名、字段、复权参数、上游来源。
2. `S002` 上海证券交易所交易规则：链接是否为当前有效版本、生效日期、申报单位和涨跌幅条款。
3. `S003` 香港交易所交易运作常见问题：交易单位/每手股数的具体表述。
4. `S004` 香港交易所 VCM 常见问题：机制细节和适用证券范围。
5. `S005`–`S007` DeepSeek 模型列表、Chat Completions、JSON Output：模型 ID、字段、错误码和 JSON 要求。
6. `S008`–`S011` Python、pandas、NumPy、SQLite 文档：版本和 API 行为。
7. `S012` Microsoft Edge WebView2 Runtime：安装要求和版本。
8. `S013` 巨潮资讯 A 股基础目录：端点、字段、公开访问状态。
9. `S014`–`S020` scikit-learn、SciPy、dataclasses、sqlite3、Git、pytest 文档：版本和示例行为。
10. `S021`–`S022` Windows 凭据管理器：API 行为和权限要求。
11. `A001`–`A031` 论文、教材和课程：DOI、ISBN、页码、版次、作者列表和课程页面版本。
12. 所有交易费用、税率、结算、申报单位和涨跌幅数字：不能从本软件默认值推断现行规则；正式内容发布前必须以交易所、监管机构或券商官方资料重新核验。

## 6. 来源统计

| 类型 | 数量 | 说明 |
| --- | --- | --- |
| 外部官方 `S` | 22 | S001–S022；页面内容未联网核验，标记 `NEEDS_REVIEW` |
| 项目内 `P` | 6 | P001–P006；2026-10-22 已读 |
| 学术 `A` | 31 | A001–A031；书目信息待复核 |
| 手册引用 | 10 篇 | 每篇至少引用 P 文档；关键页面引用 S/A |
| 专业词条来源映射 | 85 条 | 见 `CATALOG.md` 各行“主要来源” |

## 7. 建议 Codex 优先复核（最多 10 项）

1. 顶栏“新手使用指引” → “使用手册”，以及“快速开始/功能说明/专业知识库”三入口的实际接入。
2. 设置“新手模式（关闭为专业模式）” → “显示详细解释提示”，确认只影响提示密度。
3. Academy 移除“保存实验与测验”入口，保留固定教学样本和参数实验。
4. DeepSeek 面板“本页上方配置”文案与 `⚙` → DeepSeek 实际位置不一致。
5. Academy 第 8 课知识解释无当前值，确认是否需要传入模拟结果。
6. `rebalancing_and_turnover` 的“每日再平衡假设/换手成本未建模”如何分层。
7. 部分实现词条的 `theory_only`/`implemented` 标注：`mae_and_rmse`、`mean_and_median`、`sample_and_population`、`standard_error`、`cash_position_and_pnl`、`trading_calendar`、`timezone_and_session`。
8. 港股 1–5 位补足与界面“5 位”提示是否统一。
9. 外部来源 `S001`–`S022`、`A001`–`A031` 的页面/书目复核和核验日期更新。
10. 接入手册后按 AGENTS.md 做真实 WebView DOM/控件验收；本批次未启动 GUI，不能把文档完成当成验收通过。

## 8. 未执行事项

- 未启动 Streamlit 或桌面 WebView；未核对实际 DOM。手册中的控件名称来自代码 `st.button`/`st.selectbox`/`st.text_input` 等定义，但实际渲染仍需 GUI 验收。
- 未联网核验外部页面；2026-10-22 的 WebFetch 尝试被网络策略阻止。
- 未运行付费 DeepSeek 请求；手册中的请求边界来自代码和现有文档。
- 未修改或迁移 SQLite 数据库；未写入任何 Key；未创建安装包、标签或 Release。

## 9. 声明

本轮只新增/更新 `docs/knowledge-drafts/` 下的 Markdown 文件。未修改程序代码、测试、数据库、`VERSION`、构建脚本或发行文件；未执行打包、标签或 Release。手册草稿尚未进入软件，必须由 Codex 复核、转换、测试并通过实际 WebView 验收后，才能成为正式功能。

## 10. 下一批次建议

批次 2：市场与数据、收益与风险共 20 篇专业文章。建议先写 `instrument_identity`、`ohlcv`、`price_adjustment`、`data_provenance`、`simple_return`、`volatility`、`maximum_drawdown`、`sharpe_ratio`，把手册中的口径延伸到公式和手算例子；继续使用 `theory_only` 标注未实现能力，并在写完后把 `CATALOG.md` 中对应文章状态从 `todo` 更新为 `drafted` 或 `source_checked`。
