# 批次 1 复核、批次 2 修订与批次 3 记录

日期：2026-10-22；批次 2 修订：2026-10-23；批次 3：2026-10-23
批次：使用手册 10 篇；专业文章批次 2 共 20 篇；批次 3 共 20 篇
代码基线：`codex/learning-center-v2`，提交 `d50cfd1`
恢复分支：`codex/recovery-before-manual-batch1-20261022`（指向 `d50cfd1`）；批次 2 修订恢复分支：`codex/recovery-before-batch2-revision-20261023`（指向 `0ada6fd`）；批次 3 恢复分支：`codex/recovery-before-batch3-20261023`（指向 `3498f98`）
写作范围：仅 `docs/knowledge-drafts/`；未修改 `quant_lab/`、`tests/`、`app.py`、`desktop_launcher.py`、`VERSION`、构建脚本、数据库或发行文件。
批次 1 草稿提交：`09b003f`；批次 1 修订提交：`99c70aa`；批次 2 草稿提交：`0ada6fd`；批次 2 修订提交：`3498f98`；批次 3 基于 `3498f98`。

## 0. 批次 2 修订摘要（2026-10-23）

1. `annualized_return`：修正 126 个间隔的表述，改为“年化是累计增长因子的平方再减一，即 `(1+R_cum)^2−1`”，不再写成平方根。
2. `maximum_drawdown`：删除全部英文内部编辑批注；保留 `d=−25%` 对应恢复涨幅 33.33%、`d=−20%` 对应恢复涨幅 25%。
3. `corporate_actions`、`price_adjustment`：全部“2 拆 1”统一改为“1 股拆成 2 股（2-for-1 stock split）”。
4. `A033`：ISBN 修正为 ISBN-10 `0135161088`、ISBN-13 `9780135161081`，书目已核验。
5. `A035`：按 Cambridge 官方页面改为 2017 年（第 3 版），ISBN `978-1107111820` 不变，书目已核验。
6. `currency_and_fx`：功能状态从 `implemented` 改为 `needs_code_review`；正文明确 CNY/HKD 标注与同币种限制已实现，汇率数据、换算、对冲和跨币种组合未实现。
7. 统计更新：专业词条 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13；批次 2 为 `implemented` 13、`needs_code_review` 5、`theory_only` 2。
8. 来源状态：S023、S024 官方入口已由 Codex 于 2026-10-23 确认可访问，具体规则仍按文章需要核验；A032、A034 书目/DOI 已核验；A033 修正 ISBN 后书目已核验；A035 第三版、ISBN 和 2017 出版日期已核验。
9. 全目录扫描确认除合法状态词 `todo` 外，不存在英文内部编辑批注、未完成标记或其他内部自我校对文字。
10. 手册仍为 10 篇，专业词条仍为 85 个，批次 2 仍为 20 篇且全部 `drafted`；当时不进入批次 3，批次 3 随后单独完成。

## 1. 本轮完成内容

- 10 篇使用手册草稿：`quick_start`、`workspace`、`market_data`、`strategy`、`backtest`、`risk_portfolio`、`statistics_ml`、`academy`、`deepseek`、`research_notes`。
- `CATALOG.md`：10 篇手册 + 85 个专业词条的稳定 ID、标题、分类、状态、模块、关联词条、文章状态和主要来源。
- `references/official.md`：S001–S024 外部官方来源；P001–P006 项目内依据。
- `references/academic.md`：A001–A035 论文、教材和大学课程。
- `references/source-map.md`：手册 ID 到来源与代码位置的映射。
- `README.md`：目录使用说明和批次边界。

### 1.1 Codex 批次 1 复核结论与修订（2026-10-22）

Codex 对批次 1 的复核结论已落实为以下修改：

1. `CATALOG.md` 中 12 个复合或部分实现词条统一改为 `needs_code_review`：`trading_calendar`、`timezone_and_session`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean`、`lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`、`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`。不拆分 ID，专业词条总数保持 85。
2. `manual/research_notes.md` 已修正草稿丢失说明：SQLite 已保存草稿不会因清除 WebView 本地存储而删除；只有尚未同步的输入可能丢失；只有“放弃草稿”会删除数据库草稿和草稿附件。
3. `manual/deepseek.md` 中目标版本的“学习笔记”已统一改为“研究笔记”。当前程序按钮“保存选定回答到学习笔记”仍需同步重命名，见第 4.2 节。
4. `CATALOG.md` 与 `REVIEW_NOTES.md` 的状态统计已按逐行状态更新：`implemented` 62、`theory_only` 10、`academy_demo` 1、`needs_code_review` 12 个专业词条，另有 1 个手册章节 `workspace` 为 `needs_code_review`。批次 2 修订后（2026-10-23）为 `implemented` 61、`needs_code_review` 13。
5. `references/official.md` 中 S001–S007 已改为“官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验”；没有把入口可访问写成全部内容已经核验。
6. 已重新核对：手册 10 篇、专业词条 85 个、手册相关术语 ID 均存在、修改范围仅限 `docs/knowledge-drafts/`。

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

批次 3 额外只读核对 `strategy.py`、`backtest.py`、`research.py`、`metrics.py`、`storage.py`、`ui_strategy.py`、`learning.py`、`ui_learning.py`、`statistics.py`，用于核对策略条件、成交时序、费用、样本切分、参数敏感性和实验指纹；这些文件只读，没有修改。

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

7. **复合或部分实现词条统一复核**
   - 按 Codex 复核结论，以下 12 个词条统一标 `needs_code_review`，不拆分 ID：`trading_calendar`、`timezone_and_session`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean`、`lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`、`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`。
   - 其中已实现或已显示的部分包括：实际交易日对齐、北京时间显示、字段校验、算术均值、整手数量、固定基点滑点、现金/股数记录、每日固定权重再平衡假设、样本分母 `n−1`、均值、t 检验内部标准误、MAE。
   - 未实现、未显示或未建模的部分包括：独立交易日历服务、盘中交易时段、幸存者/前视偏差控制、算术/几何均值并列比较、碎股、流动性与市场冲击、单独 PnL 列、换手/调仓成本、总体公式、中位数、单独标准误显示、RMSE。
   - 后续文章必须分段说明这些差异，不得把已实现部分误写成 `theory_only`，也不得把未实现部分写成按钮或指标。

## 4. `needs_code_review` 清单

### 4.1 专业词条（13）

> 批次 1 复核时列出 12 个；批次 2 修订（2026-10-23）新增 `currency_and_fx`，当前共 13 个。

| ID | 部分实现/待复核内容 | 建议 |
| --- | --- | --- |
| `trading_calendar` | 实际交易日用于对齐；无独立日历服务 | 文章分层：已使用日期 vs 未提供日历接口 |
| `timezone_and_session` | 接收时间存 UTC、显示北京时间；不建模盘中交易时段 | 文章分层：时间戳 vs 交易时段 |
| `currency_and_fx` | CNY/HKD 标注与同币种限制已实现；汇率数据、换算、对冲和跨币种组合未实现 | 文章分三层说明；不把汇率换算或跨币种组合写成按钮或指标 |
| `data_quality_and_bias` | 字段校验已实现；幸存者/前视偏差未完全控制 | 逐项区分缺失、停牌、重复、异常值和偏差 |
| `arithmetic_vs_geometric_mean` | 算术均值用于夏普分子、几何年化用于收益换算；无并列比较 UI | 文章并列解释，不虚构比较指标 |
| `lot_size_and_fractional_shares` | 整手已实现；碎股未实现 | 不拆 ID；文章分节说明 |
| `slippage_liquidity_market_impact` | 固定基点滑点已实现；流动性与市场冲击未实现 | 不拆 ID；文章分节说明 |
| `cash_position_and_pnl` | 现金/股数逐日记录；PnL 可推导但无单独列 | 说明推导方式，不写“PnL 指标” |
| `rebalancing_and_turnover` | 每日固定权重再平衡假设；换手/成本未建模 | 说明假设，不写完整成本模型 |
| `sample_and_population` | 样本分母 `n−1` 已使用；总体公式未提供 | 文章并列，标注软件口径 |
| `mean_and_median` | 均值已显示；中位数未显示 | 文章分层说明 |
| `standard_error` | t 检验内部计算；不单独显示 | 说明内部使用，不写独立指标 |
| `mae_and_rmse` | MAE 已显示；RMSE 未显示 | 文章分层说明，不拆 ID |

### 4.2 手册与程序事项

| 对象 | 问题 | 建议 |
| --- | --- | --- |
| `workspace`（手册） | 三入口、顶栏改名、设置标签尚未在当前代码实现 | Codex 接入手册内容时按目标结构改造，并做 WebView DOM 验收 |
| `academy`（文章状态 `review_needed`） | 当前仍有测验/学习中心入口，目标移除 | 移除旧入口后复核测试和帮助文本 |
| `deepseek`（文案差异） | 面板提示与实际设置位置不一致 | 修正文案或调整入口；手册已按实际位置写 |
| `deepseek` 按钮重命名 | 当前程序按钮为“保存选定回答到学习笔记” | 目标版本改为“保存选定回答到研究笔记”，同步成功/错误提示和测试 |
| `academy` 第 8 课 | 过拟合课程知识解释无当前值 | 决定是否传模拟结果或改写为“本课无单一指标” |
| 港股代码提示 | 1–5 位补足 vs 界面提示 5 位 | 统一文案或输入校验；不要改变 `normalize_symbol` 行为前先加测试 |
| GUI 验收 | 本批次未启动 WebView，未核对实际 DOM | 按 AGENTS.md 做真实 WebView DOM/控件验收 |

## 5. `NEEDS_REVIEW` 清单

以下项目仍需逐项核验。S001–S007 的官方入口已由 Codex 于 2026-10-22 确认可访问，S023、S024 的官方入口已由 Codex 于 2026-10-23 确认可访问，但入口可访问不等于全部内容已经核验；S008–S022 未联网核验：

1. `S001`–`S007` 的官方入口已由 Codex 于 2026-10-22 确认可访问，`S023`、`S024` 的官方入口已由 Codex 于 2026-10-23 确认可访问，但接口字段、条款、版本号、生效日期和生效口径仍需逐项核验；`S008`–`S022` 的页面内容未在 2026-10-23 前联网核验。发布前必须重新访问原始页面。
2. `S001` AKShare 股票数据文档：入口可访问；接口名、字段、复权参数、上游来源待逐项核验。
3. `S002` 上海证券交易所交易规则：入口可访问；具体条款、生效日期、申报单位和涨跌幅口径待逐项核验。
4. `S003` 香港交易所交易运作常见问题：入口可访问；交易单位/每手股数的具体表述待核验。
5. `S004` 香港交易所 VCM 常见问题：入口可访问；机制细节和适用证券范围待核验。
6. `S005`–`S007` DeepSeek 模型列表、Chat Completions、JSON Output：入口可访问；模型 ID、字段、错误码和 JSON 要求待逐项核验。
7. `S008`–`S011` Python、pandas、NumPy、SQLite 文档：版本和 API 行为。
8. `S012` Microsoft Edge WebView2 Runtime：安装要求和版本。
9. `S013` 巨潮资讯 A 股基础目录：端点、字段、公开访问状态。
10. `S014`–`S020` scikit-learn、SciPy、dataclasses、sqlite3、Git、pytest 文档：版本和示例行为。
11. `S021`–`S022` Windows 凭据管理器：API 行为和权限要求。
12. `S023` IANA Time Zone Database：官方入口已由 Codex 于 2026-10-23 确认可访问；时区标识、偏移和夏令时规则仍按文章需要核验。
13. `S024` ISO 4217 Currency Codes：官方入口已由 Codex 于 2026-10-23 确认可访问；货币代码标准和适用范围仍按文章需要核验。
14. `A001`–`A031` 论文、教材和课程：DOI、ISBN、页码、版次、作者列表和课程页面版本仍待复核。`A032`、`A034` 的书目/DOI 和 `A033`、`A035` 的书目/ISBN 已于 2026-10-23 核验；书目核验不等于已读取全文。
15. 所有交易费用、税率、结算、申报单位和涨跌幅数字：不能从本软件默认值推断现行规则；正式内容发布前必须以交易所、监管机构或券商官方资料重新核验。
16. 批次 3 使用的 `S002`、`S003`、`S004` 交易规则、费用、整手、涨跌停和 VCM 条款仍未逐项核验；文章只把它们作为研究假设，不能写成现行法定规则。

## 6. 来源统计

| 类型 | 数量 | 说明 |
| --- | --- | --- |
| 外部官方 `S` | 24 | S001–S007 入口已由 Codex 于 2026-10-22 确认可访问；S023、S024 入口已由 Codex 于 2026-10-23 确认可访问；S008–S022 待核验；字段/条款按文章需要核验 |
| 项目内 `P` | 6 | P001–P006；2026-10-22 已读 |
| 学术 `A` | 35 | A032–A035 书目/DOI/ISBN 已核验；A001–A031 书目信息待复核 |
| 手册引用 | 10 篇 | 每篇至少引用 P 文档；关键页面引用 S/A |
| 专业词条来源映射 | 85 条 | 见 `CATALOG.md` 各行“主要来源” |
| 批次 3 新增来源 | 0 | 沿用现有 S/P/A；未新增来源编号 |

## 7. 建议 Codex 优先复核（最多 10 项）

1. 顶栏“新手使用指引” → “使用手册”，以及“快速开始/功能说明/专业知识库”三入口的实际接入。
2. 设置“新手模式（关闭为专业模式）” → “显示详细解释提示”，确认只影响提示密度。
3. Academy 移除“保存实验与测验”入口，保留固定教学样本和参数实验。
4. DeepSeek 面板“本页上方配置”文案与 `⚙` → DeepSeek 实际位置不一致；同时把“保存选定回答到学习笔记”改为“保存选定回答到研究笔记”，同步成功/错误提示和测试。
5. Academy 第 8 课知识解释无当前值，确认是否需要传入模拟结果。
6. 13 个 `needs_code_review` 专业词条：`trading_calendar`、`timezone_and_session`、`currency_and_fx`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean`、`lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`、`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`；不拆分 ID。
7. 后续文章对上述复合词条分节写明“已实现/已显示”“未显示/未提供”“未实现”，不得把整手、固定滑点、MAE、均值等已实现部分误写成 `theory_only`；批次 3 已对整手、滑点、现金/PnL 三层写成。
8. 港股 1–5 位补足与界面“5 位”提示是否统一。
9. 外部来源：S001–S007 入口已由 Codex 于 2026-10-22 确认可访问，S023、S024 入口已由 Codex 于 2026-10-23 确认可访问，但字段/条款/生效口径待逐项核验；S008–S022 与 A001–A031 仍待核验；A032–A035 书目/DOI/ISBN 已核验。
10. 接入手册后按 AGENTS.md 做真实 WebView DOM/控件验收；本批次未启动 GUI，不能把文档完成当成验收通过。

批次 3 的代码事实复核问题见第 12.4 节；本节保持最多 10 项。

## 8. 未执行事项

- 未启动 Streamlit 或桌面 WebView；未核对实际 DOM。手册中的控件名称来自代码 `st.button`/`st.selectbox`/`st.text_input` 等定义，但实际渲染仍需 GUI 验收。
- 未逐项核验外部页面内容；S001–S007 的官方入口已由 Codex 于 2026-10-22 确认可访问，S023、S024 的官方入口已由 Codex 于 2026-10-23 确认可访问，但接口字段、条款和生效口径仍需逐项核验；S008–S022 未联网核验；A032–A035 仅核验书目/DOI/ISBN，未读取全文。
- 批次 2 的 20 篇文章状态均为 `drafted`，未标 `source_checked`；外部来源内容未逐条读取。
- 未运行付费 DeepSeek 请求；手册中的请求边界来自代码和现有文档。
- 未修改或迁移 SQLite 数据库；未写入任何 Key；未创建安装包、标签或 Release。
- 本次修订后使用独立 `--basetemp` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；本次只改文档。
- 批次 2 后再次使用独立 `--basetemp` 运行 `pytest -q`：115 passed，1 warning；未修改程序代码。
- 批次 2 修订后使用独立 `--basetemp` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；首次使用默认临时目录运行时，Windows 拒绝访问 `pytest-of-LENOVO` 目录，属于环境权限问题，不是测试断言失败。本次仅修改 `docs/knowledge-drafts/`。
- 批次 3 后使用独立 `--basetemp` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；本次仅新增/修改 `docs/knowledge-drafts/` 下的 Markdown 文件。

## 9. 声明

本轮（批次 1 修订、批次 2 起草与修订、批次 3 起草）只修改 `docs/knowledge-drafts/` 下的 Markdown 文件。未修改程序代码、测试、数据库、`VERSION`、构建脚本或发行文件；未执行打包、标签或 Release。手册和 40 篇专业文章仍是草稿，尚未进入软件，必须由 Codex 复核、转换、测试并通过实际 WebView 验收后，才能成为正式功能。

## 10. 下一批次建议

批次 2 已完成 20 篇（市场与数据、收益与风险）并于 2026-10-23 完成修订；批次 3 已完成 20 篇（策略与执行、回测与研究）草稿，文章状态均为 `drafted`。下一批次（未开始）为批次 4：组合分析、统计推断、机器学习，共 25 篇；本次提交不进入批次 4。批次 4 应继续使用 `theory_only` 标注未实现能力，并在外部来源未逐条读取时保持 `drafted`，不标 `source_checked`。

## 11. 批次 2：市场与数据、收益与风险（20 篇）

### 11.1 完成状态

- 20 篇文章已写入 `articles/market_data/`（10 篇）和 `articles/return_risk/`（10 篇）。
- 文章状态全部为 `drafted`；外部来源内容未逐条读取，未标 `source_checked`。
- 软件状态：`implemented` 13 篇、`needs_code_review` 5 篇、`theory_only` 2 篇。
- 五个 `needs_code_review`：`trading_calendar`、`timezone_and_session`、`currency_and_fx`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean`；正文均分三层写“已计算/显示、只间接使用、未提供/未建模”。
- 两个 `theory_only`：`corporate_actions`、`log_return`；正文明确写“当前软件未实现”。
- 未新增或删除内容 ID，专业词条总数仍为 85；新增来源编号 S023、S024、A032–A035。

### 11.2 公式与口径清单

| 文章 ID | 核心公式/口径 | 软件状态 | 主要来源 | 待复核/说明 |
| --- | --- | --- | --- | --- |
| `instrument_identity` | `normalize(market, raw) -> code`；A 股 `\d{6}`，港股 `\d{1,5}` 补足五位 | `implemented` | S001, S013, P004 | 代码规范化不等于上市身份验证 |
| `ohlcv` | `r_t=close_t/close_{t-1}−1`；`range=high−low`；`amount/volume≈平均价` | `implemented` | S001, P004, A032 | 字段/单位/复权接口 NEEDS_REVIEW |
| `trading_calendar` | `D_common=∩D_i`；`R_ann=(P_n/P_1)^(252/(n−1))−1` | `needs_code_review` | S001, S002, S003, P004 | 实际交易日 vs 独立日历服务分层 |
| `timezone_and_session` | `t_Beijing=t_UTC+8h`；`age=now−received_at` | `needs_code_review` | S023, S001, S002, S003, P002 | 接收时间不是交易所报价时间 |
| `currency_and_fx` | `r_investor=(1+r_local)(1+r_fx)−1` | `needs_code_review` | S024, S001, P004, A035 | CNY/HKD 标注与同币种限制已实现；汇率数据、换算、对冲和跨币种组合未实现 |
| `price_adjustment` | `P_adj=P×f`；`r_total≈(P_ex+D)/P_cum−1` | `implemented` | S001, P003, P004, A033 | 复权价非成交价；上游复权行为待核验 |
| `corporate_actions` | `r_total=(P_ex+D)/P_cum−1`；拆股价值不变 | `theory_only` | S001, P004, A033, A032 | 软件未实现分红现金流/公司行动表 |
| `data_provenance` | `prov=(source,...,received_at,...)`；`fingerprint=H(...)` | `implemented` | S001, P002, P004, A034 | 本地溯源非不可篡改审计 |
| `cache_and_freshness` | `age=now−t_success`；`fresh=(age<TTL)` | `implemented` | S001, P002, P004, S008 | 缓存不是实时行情；失败保留旧值 |
| `data_quality_and_bias` | `missing_rate=missing/expected`；`duplicate_rate=dup/total` | `needs_code_review` | S001, P003, P004, A006, A016, A022, A034 | 校验不等于无偏；幸存者/前视偏差未控制 |
| `simple_return` | `R=P_1/P_0−1` | `implemented` | P003, A009, A032 | 价格收益率；不含分红/费用 |
| `log_return` | `r_log=ln(P_t/P_{t−1})` | `theory_only` | A032, A020, A009 | 当前软件未实现对应对数收益率 |
| `compound_return` | `V_n=V_0∏(1+r_i)` | `implemented` | P003, P005, A009, A032 | 多期乘法；不是收益率直接相加 |
| `annualized_return` | `R_ann=(V_n/V_0)^(252/n)−1` | `implemented` | P003, A009, A032 | n 是收益间隔数；不是未来预测 |
| `arithmetic_vs_geometric_mean` | `a=mean(r)`；`g=(∏(1+r))^(1/n)−1` | `needs_code_review` | P003, A009, A032, A013 | 软件分别使用但无并列 UI；需分层 |
| `variance` | `s²=Σ(x−x̄)²/(n−1)`；总体 `σ²=/n` | `implemented` | P003, A009 | 样本分母 n−1；方差不是百分比 |
| `standard_deviation` | `s=√s²`；`σ_ann≈s_daily×√252` | `implemented` | P003, A009 | 样本/总体分母不同；年化是近似 |
| `volatility` | `σ_ann≈s_daily×√252` | `implemented` | P003, A009, A020, A022 | 历史波动不是方向/未来预测 |
| `maximum_drawdown` | `D_t=V_t/max_{s≤t}V_s−1`；`MDD=min D_t` | `implemented` | P003, A014, A026 | 路径指标；不是未来损失上限 |
| `sharpe_ratio` | `S=(mean−r_f)/s×√252` | `implemented` | P003, A002, A009, A026 | 默认 rf=0；零波动不显示；不是盈利概率 |

### 11.3 来源与核验

- 批次 2 新增来源：S023 IANA Time Zone Database、S024 ISO 4217 Currency Codes、A032 Campbell/Lo/MacKinlay（1997）、A033 Berk/DeMarzo（2020）、A034 Wilkinson 等（2016）、A035 Bekaert/Hodrick（2017）。
- S001–S007 入口已由 Codex 于 2026-10-22 确认可访问，S023、S024 入口已由 Codex 于 2026-10-23 确认可访问，但具体字段/条款/口径未逐条核验；S008–S022 未联网核验。
- A032、A034 书目/DOI 已核验；A033 修正 ISBN 后书目已核验（ISBN-10 `0135161088`、ISBN-13 `9780135161081`）；A035 第三版、ISBN `978-1107111820` 和 2017 出版日期已核验。A001–A031 的 DOI、ISBN、页码、版次和作者列表仍待复核；书目核验不等于全文已读。
- 交易规则、接口字段、复权行为、时区和货币代码均标记 NEEDS_REVIEW（核验日期：2026-10-22）。
- 文章状态全部 `drafted`；未把“入口可访问”写成“内容已核验”。
- frontmatter 的 `last_verified: 2026-10-22` 仅表示本地代码/项目文档核对日期，不表示外部来源内容已核验。

### 11.4 需要 Codex 复核的问题（批次 2）

1. 确认五个 `needs_code_review` 词条的三层写法准确：`trading_calendar`、`timezone_and_session`、`currency_and_fx`、`data_quality_and_bias`、`arithmetic_vs_geometric_mean`；不拆分 ID。
2. 确认 `corporate_actions`、`log_return` 保持 `theory_only`，正文“当前软件未实现”没有暗示按钮或指标。
3. 确认 252 个年交易日近似、`n` 为收益间隔数、年化公式与 `docs/METHODOLOGY.md` 和 `metrics.py` 一致。
4. 确认算术平均/几何平均文章只解释现有口径，不要求新增并列指标或 UI。
5. 确认样本方差/标准差使用 `n−1`、总体分母 `n` 仅作对照，不把总体公式写成软件功能。
6. 确认 `corporate_actions` 的“仅复权间接体现、无分红现金流”描述与当前回测/估值边界一致。
7. 确认数据质量文章对缺失自然日/缺失交易日/停牌/重复/异常值/幸存者偏差/前视偏差的区分没有过度声称控制。
8. 确认 `cache_and_freshness` 的 TTL、失败保留、手动绕过和 `received_at` 语义与 `data.py`/`refresh.py` 一致。
9. 确认新增来源 S023/S024 的官方入口状态、A032–A035 的书目/DOI/ISBN 核验结果和仍需逐项核验的文章规则；正式发布前重新核验。
10. 确认 20 篇文章状态保持 `drafted`；只有逐条读取外部资料后才能升级为 `source_checked`。

## 12. 批次 3：策略与执行、回测与研究（20 篇）

### 12.1 完成状态

- 20 篇文章已写入 `articles/strategy_execution/`（10 篇）和 `articles/backtest_research/`（10 篇）。
- 文章状态全部为 `drafted`；外部来源内容未逐条读取，未标 `source_checked`。
- 软件状态：`implemented` 13 篇、`needs_code_review` 3 篇、`theory_only` 3 篇、`academy_demo` 1 篇。
- 13 篇 `implemented`：`signal_position_order_trade`、`moving_average`、`moving_average_crossover`、`trend_following`、`lookahead_bias`、`next_open_execution`、`trading_costs`、`benchmark`、`equity_curve`、`in_sample_out_of_sample`、`temporal_split`、`parameter_sensitivity`、`reproducibility_and_audit`。
- 3 篇 `needs_code_review`：`lot_size_and_fractional_shares`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`；正文均分三层写“已实现/已显示、未显示/未提供、未实现”。
- 3 篇 `theory_only`：`mean_reversion`、`walk_forward_analysis`、`data_snooping_and_multiple_testing`；正文明确写“当前软件未实现”。
- 1 篇 `academy_demo`：`overfitting`；只描述 Quant Academy 第 8 课固定模拟，不写自动检测器。
- 未新增或删除内容 ID，专业词条总数仍为 85；未新增来源编号，沿用现有 S/P/A。
- 三种策略与 `strategy.py` 一致：`single_ma` 为 `close > MA_long`；`dual_ma` 为 `MA_short > MA_long`；`trend` 为 `close > MA_long` 且 `MA_long.diff() > 0`。
- 回测口径与 `backtest.py`/`research.py` 一致：信号 t 最早 t+1 开盘成交；复权价格只生成信号；成交和估值使用同日不复权价格；只做多、不加杠杆、不做空；卖出全部持股。
- 基准在第二个交易日开盘尝试买入，使用同一成本与规则，不强制末日平仓。
- 样本内外：`split=int(N×train_fraction)`；样本外统计从 `split−1` 净值开始；`split_date=raw_history["date"].iloc[split]`；参数敏感性仅样本内并跳过无效窗口。
- 可复现性：`audit_id` 覆盖原始 CSV、信号 CSV、策略、成本配置和训练比例；来源、接收时间、市场、代码、名称、复权保存在实验档案，但不全部进入 `audit_id`；当前实验未保存源码提交或输入契约版本。
- 批次 3 文章 frontmatter 的 `last_verified: 2026-10-23` 仅表示本地代码/项目文档核对日期，不表示外部来源内容已核验。

### 12.2 公式与口径清单

| 文章 ID | 核心公式/口径 | 软件状态 | 主要来源 | 待复核/说明 |
| --- | --- | --- | --- | --- |
| `signal_position_order_trade` | `decision_t=S_{t−1}`；`equity=cash+shares×close`；`filled/blocked` | `implemented` | P002, P003, P004 | 信号、目标持仓、订单、成交、持仓、估值分层 |
| `moving_average` | `MA_N(t)=1/N Σ_{i=0}^{N−1} close_{t−i}`；`min_periods=N` | `implemented` | P003, P005, A008 | 窗口 2–250；前 N−1 日为空 |
| `moving_average_crossover` | `S_t=1[MA_s(t)>MA_l(t)]` | `implemented` | P003, P005, A008 | 严格大于；相等为 0 |
| `trend_following` | `S_t=1[close_t>MA_l(t)]×1[MA_l(t)>MA_l(t−1)]` | `implemented` | P003, P005, A008 | 短周期不参与条件 |
| `mean_reversion` | `z_t=(P_t−μ_t)/σ_t`；`z≤−k` 入场，`z≥0` 退出 | `theory_only` | A008, A020 | 当前软件未实现 |
| `lookahead_bias` | `S_t=f(I_t)`；成交在 `t+1` 开盘 | `implemented` | P003, P004, A016 | 无通用自动检测器 |
| `next_open_execution` | `decision_{t+1}=S_t`；`fill=open×(1±s/10000)` | `implemented` | P003, P004, S002, S003 | 零成交量/涨跌停/T+1 可阻止成交 |
| `lot_size_and_fractional_shares` | `max_lots=floor(cash/(fill×lot))`；卖出全部 | `needs_code_review` | S002, S003, P003, P004 | 整手已实现；碎股未实现；港股每手用户输入 |
| `trading_costs` | `fee=max(min_comm,N×c_bps/10000)+N×t_bps/10000` | `implemented` | S002, S003, P003 | 默认值为可修改研究假设 |
| `slippage_liquidity_market_impact` | `fill_buy=open×(1+s/10000)`；`fill_sell=open×(1−s/10000)` | `needs_code_review` | S002, S003, P003, A016 | 固定滑点已实现；订单簿/容量/冲击未实现 |
| `benchmark` | `S_t=1`；第二个交易日开盘买入；不强制末日卖出 | `implemented` | P003, A006 | 同成本同规则；单资产买入持有 |
| `equity_curve` | `E_t=cash_t+shares_t×close_t`；`r_t=E_t/E_{t−1}−1` | `implemented` | P003, A026 | 每日收盘估值；不复权价格 |
| `cash_position_and_pnl` | 每日 `cash`、`shares`、`equity`；PnL 可推导 | `needs_code_review` | P003, P004, A026 | 独立 PnL/已实现/未实现列未提供 |
| `in_sample_out_of_sample` | `split=int(N×f)`；测试从 `split−1` 净值起；`split_date=date[split]` | `implemented` | P003, A006, A016 | 单次切分，不是 walk-forward |
| `temporal_split` | 回测同上；ML `train=[:split−1]`，`test=[split:]` | `implemented` | P003, A005, A016 | 机器学习一行间隔 |
| `walk_forward_analysis` | 滚动训练/测试窗口拼接 | `theory_only` | P003, A005, A006, A016 | 当前只有单次切分和训练期 3 折 CV |
| `parameter_sensitivity` | 3×3 网格；仅样本内；跳过 `short>=long` 或 `long>=len(raw_train)` | `implemented` | P003, A006, A016 | 不报告样本外、回撤或夏普 |
| `overfitting` | Academy 固定模拟 `training(x)`/`testing(x)` | `academy_demo` | P003, P005, A006, A018 | 无自动过拟合检测器 |
| `data_snooping_and_multiple_testing` | `FWER=1−(1−α)^m`；Bonferroni `α/m` | `theory_only` | P003, A007, A015, A016 | 当前未做多重检验校正 |
| `reproducibility_and_audit` | `audit_id=first16hex(SHA256(raw_csv ‖ signal_csv ‖ repr(spec) ‖ repr(config) ‖ str(train_fraction)))` | `implemented` | P002, P004, S011, A034 | 未保存源码提交/输入契约版本 |

### 12.3 来源与核验

- 批次 3 未新增来源编号；沿用现有 S/P/A。`S002`、`S003`、`S004` 的官方入口已由 Codex 确认可访问，但交易规则、费用、整手、涨跌停和 VCM 的具体条款未逐项核验。
- `A005`、`A006`、`A007`、`A008`、`A015`、`A016`、`A018`、`A020`、`A026` 的书目信息仍待复核；`A034` 的书目/DOI 已核验。书目核验不等于全文已读。
- 所有费用、滑点、整手和涨跌停数字都是可修改研究假设，不得写成当前法定费用、券商报价或完整交易所仿真。
- 文章状态全部 `drafted`；未把“入口可访问”写成“内容已核验”。
- frontmatter 的 `last_verified: 2026-10-23` 仅表示本地代码/项目文档核对日期，不表示外部来源内容已核验。

### 12.4 需要 Codex 复核的问题（批次 3）

1. 确认三种策略条件与 `strategy.py` 完全一致：`single_ma` 只用长均线；`dual_ma` 严格短 > 长；`trend` 要求价格 > 长均线且长均线 `diff()>0`。
2. 确认 `run_backtest` 使用 `close_signals.iloc[i-1]` 决策、t+1 开盘成交、卖出全部持股、只做多；确认基准在第二个交易日开盘尝试买入且不强制末日平仓。
3. 确认 `split=int(N×train_fraction)`、样本外统计 `equity[split-1:]`、`split_date=raw_history["date"].iloc[split]` 的 off-by-one 口径与 `research.py` 一致。
4. 确认参数敏感性仅使用 `raw_train`/`signal_train`，并跳过 `short>=long` 与 `long>=len(raw_train)`；确认“成交次数”只统计 `filled` 订单。
5. 确认交易成本默认值、UI 标签“佣金/最低佣金/买入附加费用/卖出附加费用/单边滑点”和“研究假设”声明与 `backtest.py`/`ui_strategy.py` 一致。
6. 确认 `lot_size_and_fractional_shares` 分层：整手已实现、碎股未实现、港股每手数量由用户输入且软件不自动验证。
7. 确认 `slippage_liquidity_market_impact` 分层：固定基点滑点已实现；订单簿、容量和市场冲击未实现。
8. 确认 `cash_position_and_pnl` 分层：每日 cash/shares/equity 已记录；独立 PnL/已实现/未实现盈亏列未提供。
9. 确认 `audit_id` 的五类输入和实验档案字段：来源、接收时间、市场、代码、名称、复权保存在档案，但不全部进入 `audit_id`；当前未保存源码提交或输入契约版本。
10. 确认 `mean_reversion`、`walk_forward_analysis`、`data_snooping_and_multiple_testing` 保持 `theory_only`，`overfitting` 保持 `academy_demo`；不要把 3 折训练期 CV 写成完整 walk-forward，也不要把 Academy 演示写成自动检测器。
