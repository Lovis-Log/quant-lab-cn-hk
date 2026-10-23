# 批次 1 复核、批次 2–4 修订与批次 5 记录

日期：2026-10-22；批次 2 修订：2026-10-23；批次 3：2026-10-23；批次 4：2026-10-23；批次 4 修订：2026-10-23；批次 5：2026-10-23；批次 5 修订：2026-10-23
批次：使用手册 10 篇；专业文章批次 2 共 20 篇；批次 3 共 20 篇；批次 4 共 25 篇；批次 5 共 20 篇
代码基线：`codex/learning-center-v2`，提交 `c10728b`（批次 5 起点；本批次未修改程序代码）
恢复分支：`codex/recovery-before-manual-batch1-20261022`（指向 `d50cfd1`）；批次 2 修订恢复分支：`codex/recovery-before-batch2-revision-20261023`（指向 `0ada6fd`）；批次 3 恢复分支：`codex/recovery-before-batch3-20261023`（指向 `3498f98`）；批次 4 恢复分支：`codex/recovery-before-batch4-20261023`（指向 `7275d71`）；批次 5 恢复分支：`codex/recovery-before-batch5-20261023`（指向 `c10728b`）；批次 5 修订恢复分支：`codex/recovery-before-batch5-revision-20261023`（指向 `78b9b74`）
写作范围：仅 `docs/knowledge-drafts/`；未修改 `quant_lab/`、`tests/`、`app.py`、`desktop_launcher.py`、`VERSION`、构建脚本、数据库或发行文件。
批次 1 草稿提交：`09b003f`；批次 1 修订提交：`99c70aa`；批次 2 草稿提交：`0ada6fd`；批次 2 修订提交：`3498f98`；批次 3 基于 `3498f98`；批次 4 基于 `7275d71`；批次 5 基于 `c10728b`；批次 5 草稿提交：`78b9b74`；批次 5 修订基于 `78b9b74`。

## 接入状态更新（2026-10-23）

- 文字手册分支阶段 3 已接入全部 10 篇手册和 85 篇专业文章，完成三入口、目录、离线搜索、面包屑、状态、前置/相关词条和下一篇跳转。
- 按用户确认，`codex/manual-reading-v1` 已删除旧新手指引的任务、路径、测验和进度代码；完整任务式产品保留在 `codex/learning-center-v2`。SQLite schema v4 和旧学习数据不删除、不迁移。
- Academy 旧学习中心按钮已替换为专业文章跳转；阶段 3 真实 WebView2 DOM 验收通过。下文“当前代码差异”保留内容起草时的历史记录，不再代表本分支当前状态。

## 0. 批次 5 摘要（2026-10-23）

1. 20 篇专业文章已写入 `articles/programming_engineering/`，全部文章状态为 `drafted`；外部来源未逐条读取，不标 `source_checked`。
2. 20 篇全部为 `implemented`；这里表示技术确实被项目代码使用，不表示软件为用户提供独立的 Python、Git、数据库管理或编程教学工具。
3. 不新增、删除或拆分 ID，专业词条总数仍为 85；全目录功能状态保持 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13。
4. 专业文章状态更新为 `drafted` 85、`todo` 0；使用手册仍为 10 篇。
5. Python 口径：`bool` 是 `int` 子类，但金融参数校验不能因此把 `True` 当数值 1；浮点不承诺精确十进制；`1% = 0.01`、`1 bp = 0.0001`。
6. 数据口径：`clean_stock_history` 对必需字段中的不可解析值、NaN、无穷值、负成交量和异常价格关系显式报错；组合按日期内连接并 `dropna`；机器学习把零成交量替换为 NaN，删除含缺失特征或标签的行；当前没有通用插值。
7. 收益率口径：当前使用简单收益率 `r_t=P_t/P_{t−1}−1`，不是对数收益率；第一个收益率通常是 NaN；只有机器学习 `volume_change` 明确使用 `fill_method=None`，价格序列依赖已验证的完整输入。
8. 滚动窗口：`moving_average` 使用 `rolling(window=N,min_periods=N).mean()`；5/20 日均线和 10 日收益标准差按观测行/交易日，不是自然日；前 N−1 行是预热。
9. 日期口径：行情 `date` 是无时区交易日；`received_at`、`created_at` 是 UTC；界面显示北京时间 UTC+08:00；`received_at` 是本机收到响应的时间，不是交易所报价时间。
10. 序列化与存储：实验 CSV 为 `to_csv(index=False)` 的 UTF-8 字节，SQLite 中为 zlib 压缩 BLOB；读取先解压、核对 SHA-256，再 `read_csv(parse_dates=["date"], float_precision="round_trip")`；JSON 不是加密、签名或自动 schema 验证；部分界面下载使用 UTF-8 BOM。
11. SQLite 口径：`_connect` 使用 `timeout=15`、`sqlite3.Row`、`PRAGMA foreign_keys=ON`；上下文正常提交、异常回滚、最后关闭；代码未显式执行 `PRAGMA journal_mode`，不能断言活动数据库固定使用 rollback journal 或 WAL；当前没有远程数据库、账户隔离、加密或防篡改保证。
12. 迁移口径：`SCHEMA_VERSION=4`、`PRAGMA user_version`；高版本拒绝打开；非空旧库升级前用 SQLite backup API 备份；`BEGIN IMMEDIATE` 事务，成功更新版本并提交，失败回滚；`stage_library` 是资料库复制流程，不与 schema 迁移混为一谈。
13. 哈希口径：`raw_sha256`、`signal_sha256` 和附件保存完整 SHA-256（64 个十六进制字符，对应 256 位）；`audit_id` 是前 16 个十六进制字符（对应 64 位）；哈希不是加密、数字签名、身份认证或第三方存证。
14. Provider/缓存：`MarketDataProvider` 是 Protocol，默认实现是 `AKShareProvider`；历史缓存 15 分钟/64 条，快照 5 分钟且请求至少间隔 1 秒；名称成功缓存 24 小时、失败冷却 5 分钟；single-flight 只合并相同 key，等待有超时；缓存和锁只在当前进程。
15. 复合词条 `automated_testing_git_and_modular_monolith` 已拆成三个独立部分：自动化测试、Git、模块化单体；模块化单体按应用/代码库/部署与业务边界定义，不以进程数量定义；桌面父进程、Streamlit 子进程和 WebView2 附加进程仍共同构成一个应用；测试通过不等于真实 WebView、外部接口或安装包验收；Git 不是应用按钮；FastAPI 是未来计划。
16. 本批次只修改 `docs/knowledge-drafts/` 下的 Markdown；未改程序、测试、数据库、`VERSION`、构建或发行文件。使用独立 `--basetemp` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）。

## 0.1 批次 4 摘要（2026-10-23）

1. 25 篇专业文章已写入 `articles/portfolio/`（8 篇）、`articles/statistics/`（9 篇）与 `articles/machine_learning/`（8 篇），全部文章状态为 `drafted`；外部来源未逐条读取，不标 `source_checked`。
2. 软件状态为 `implemented` 15、`needs_code_review` 5、`theory_only` 5；不因文章已撰写而改变任何 `software_status`。
3. `needs_code_review`：`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`；正文均分三层写“已计算/已显示、只间接使用、未提供/未建模”。
4. `theory_only`：`diversification`、`multi_currency_portfolio`、`sampling_distribution`、`confidence_interval`、`autocorrelation_and_stationarity`；正文明确写“当前软件未实现”，没有暗示不存在的按钮、指标或图表。
5. 组合口径与 `portfolio.py`/`ui_analysis.py`/`docs/METHODOLOGY.md` 一致：2–4 只不重复的当前市场代码；日期内连接；至少 8 个共同收盘日；协方差/相关使用全部共同日期收益且 `ddof=1`；训练比例 0.50–0.85；权重只用训练收益；样本外曲线在第一笔测试收益之前的共同收盘日期归一化为 1。
6. 组合权重只有等权和训练期逆波动率；权重为正、合计 100%；没有做空、杠杆、权重上下限或优化器；样本外收益矩阵乘固定权重（`test @ equal`、`test @ inverse`）是每日固定权重数学曲线，不生成持仓、订单、成交、换手率或调仓成本。核心函数不掌握币种；同市场/同币种限制由界面上下文保证。
7. 统计口径与 `statistics.py`/`ui_analysis.py` 一致：至少 3 个有效日收益；均值、样本方差/标准差使用 `n−1`；年化波动率为样本标准差 × `√252`；t 检验零假设为平均日收益率为 0，`ttest_1samp(popmean=0.0)` 默认双侧；零标准差时 t/p 返回 `None`；页面显示 p 值，不单独显示 t 值、自由度、标准误或置信区间。
8. 机器学习口径与 `statistics.py` 一致：五个特征；标签 `next_return=close(t+1)/close(t)−1`；零成交量先替换为 NaN；至少 60 行；训练比例 0.55–0.85；`split=int(M×f)`；`train=samples[:split−1]`、索引 `split−1` 为一行间隔、`test=samples[split:]`；训练至少 30 行、测试至少 10 行；`Pipeline(StandardScaler(), LinearRegression())`；训练内 `TimeSeriesSplit(3,gap=1)`；MAE、零收益基线、样本外 R²、方向一致率；RMSE 未实现。
9. 不新增、删除或拆分 ID，专业词条总数仍为 85；未新增来源编号。全目录功能状态保持 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13；批次 4 完成时专业文章状态为 `drafted` 65、`todo` 20，批次 5 完成后更新为 `drafted` 85、`todo` 0。
10. 本批次只修改 `docs/knowledge-drafts/` 下的 Markdown；未改程序、测试、数据库、`VERSION`、构建或发行文件。使用独立 `--basetemp` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）。

## 0.2 批次 2 修订摘要（2026-10-23）

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

批次 4 额外只读核对 `portfolio.py`、`statistics.py`、`ui_analysis.py`、`metrics.py`，用于核对组合共同日期、权重、样本外曲线、t 检验、特征/标签、时间切分、交叉验证和评价指标；这些文件只读，没有修改。

## 3. 事实核对结果

### 已确认

- A 股历史主链路是 AKShare 腾讯接口；港股主链路是 AKShare 东方财富接口，失败时回退新浪并显示来源。
- 历史缓存 15 分钟、最多 64 条；快照缓存 5 分钟；自选股上游请求至少间隔 1 秒；手动更新绕过缓存，连续点击 5 秒防抖。
- 名称缓存 24 小时、失败冷却 5 分钟；手动“重新获取证券名称”绕过缓存和冷却。
- 证券目录内置快照接收于 2026-10-14：A 股 6,181 条、港股 3,033 条；联网更新写入用户目录。
- 策略只有单均线、双均线、趋势过滤；窗口约束 `2 ≤ 短周期 < 长周期 ≤ 250`；`min_periods=N`；信号最早下一交易日开盘成交。
- 回测只做多；A 股有简化 T+1 防御性检查（当前日线每天最多一笔订单，正常流程不会同日买卖）；用户设定的整手和简化涨跌停；港股交易单位用户输入，未模拟 VCM。
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
17. 批次 5 使用 `S008`–`S011`、`S017`–`S020` 的 Python、pandas、NumPy、SQLite、dataclasses、sqlite3、Git 和 pytest 文档；页面内容未在 2026-10-23 前联网核验，文章只引用语言和库的通用行为，不引用具体版本条款。来源库当前把 `S019` 登记为 Git、`S020` 登记为 pytest；批次 5 按来源库编号引用，没有交换编号。
18. 批次 5 的 `A011`（pandas）和 `A012`（NumPy）书目信息仍待复核；文章用它们作概念背景，不用来证明策略有效。

## 6. 来源统计

| 类型 | 数量 | 说明 |
| --- | --- | --- |
| 外部官方 `S` | 24 | S001–S007 入口已由 Codex 于 2026-10-22 确认可访问；S023、S024 入口已由 Codex 于 2026-10-23 确认可访问；S008–S022 待核验；字段/条款按文章需要核验 |
| 项目内 `P` | 6 | P001–P006；2026-10-22 已读 |
| 学术 `A` | 35 | A032–A035 书目/DOI/ISBN 已核验；A001–A031 书目信息待复核 |
| 手册引用 | 10 篇 | 每篇至少引用 P 文档；关键页面引用 S/A |
| 专业词条来源映射 | 85 条 | 见 `CATALOG.md` 各行“主要来源” |
| 批次 3 新增来源 | 0 | 沿用现有 S/P/A；未新增来源编号 |
| 批次 5 新增来源 | 0 | 沿用 S008–S011、S017–S020、P001–P004、A011、A012；未新增来源编号 |

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

批次 3 的代码事实复核问题见第 12.4 节，批次 4 的见第 13.7 节，批次 5 的见第 14.6 节；本节保持最多 10 项。

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
- 批次 3 修订后使用独立 `--basetemp` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；本次只修改 `docs/knowledge-drafts/`。
- 批次 4 后使用独立 `--basetemp` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；本次只新增/修改 `docs/knowledge-drafts/` 下的 Markdown 文件。
- 批次 5 后使用独立 `--basetemp` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；本次只新增/修改 `docs/knowledge-drafts/` 下的 Markdown 文件。

## 9. 声明

本轮（批次 1 修订、批次 2 起草与修订、批次 3 起草、批次 4 起草、批次 5 起草）只修改 `docs/knowledge-drafts/` 下的 Markdown 文件。未修改程序代码、测试、数据库、`VERSION`、构建脚本或发行文件；未执行打包、标签或 Release。手册和 85 篇专业文章仍是草稿，尚未进入软件，必须由 Codex 复核、转换、测试并通过实际 WebView 验收后，才能成为正式功能。

## 10. 下一批次建议

批次 2 已完成 20 篇（市场与数据、收益与风险）并于 2026-10-23 完成修订；批次 3 已完成 20 篇（策略与执行、回测与研究）草稿；批次 4 已完成 25 篇（组合分析、统计推断、机器学习）草稿；批次 5 已完成 20 篇（Python、数据处理与工程）草稿；85 篇文章状态均为 `drafted`。下一批次（未开始）为批次 6：全局术语统一、交叉链接、来源复核和重复内容消除。批次 6 应继续使用 `theory_only` 标注未实现能力，并在外部来源未逐条读取时保持 `drafted`，不标 `source_checked`。

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
| `next_open_execution` | `decision_{t+1}=S_t`；`fill=open×(1±s/10000)` | `implemented` | P003, P004, S002, S003 | 零成交量/涨跌停可阻止；T+1 为防御性检查，当前日线正常流程不触发 |
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
2. 确认 `run_backtest` 使用 `close_signals.iloc[i-1]` 决策、t+1 开盘成交、卖出全部持股、只做多；确认基准在第二个交易日开盘尝试买入且不强制末日平仓。确认 A 股 `i <= last_buy_index` 的 T+1 检查是防御性代码：当前日线每天最多一笔订单，正常流程不会同日买卖，不应把 T+1 与零成交量、涨跌停并列为当前可观察的 `blocked` 原因。
3. 确认 `split=int(N×train_fraction)`、样本外统计 `equity[split-1:]`、`split_date=raw_history["date"].iloc[split]` 的 off-by-one 口径与 `research.py` 一致。
4. 确认参数敏感性仅使用 `raw_train`/`signal_train`，并跳过 `short>=long` 与 `long>=len(raw_train)`；确认“成交次数”只统计 `filled` 订单。
5. 确认交易成本默认值、UI 标签“佣金/最低佣金/买入附加费用/卖出附加费用/单边滑点”和“研究假设”声明与 `backtest.py`/`ui_strategy.py` 一致。
6. 确认 `lot_size_and_fractional_shares` 分层：整手已实现、碎股未实现、港股每手数量由用户输入且软件不自动验证。
7. 确认 `slippage_liquidity_market_impact` 分层：固定基点滑点已实现；订单簿、容量和市场冲击未实现。
8. 确认 `cash_position_and_pnl` 分层：每日 cash/shares/equity 已记录；独立 PnL/已实现/未实现盈亏列未提供。
9. 确认 `audit_id` 的五类输入和实验档案字段：来源、接收时间、市场、代码、名称、复权保存在档案，但不全部进入 `audit_id`；当前未保存源码提交或输入契约版本。
10. 确认 `mean_reversion`、`walk_forward_analysis`、`data_snooping_and_multiple_testing` 保持 `theory_only`，`overfitting` 保持 `academy_demo`；不要把 3 折训练期 CV 写成完整 walk-forward，也不要把 Academy 演示写成自动检测器。

### 12.5 批次 3 修订（2026-10-23）

1. `cash_after` 口径已修正：当前回测每天最多一笔订单，且没有其他盘中现金流，因此订单表的 `cash_after` 与该交易日净值记录中的 `cash` 相同；`cash_after`/`cash` 只是现金余额，不是账户净值，账户净值还要加上 `shares × close`。已同步修改 `signal_position_order_trade` 和 `cash_position_and_pnl`。
2. `reproducibility_and_audit` 的训练比例与指纹说明已修正：Python float 中 `0.7` 和 `0.70` 是同一个值，`str()` 都得到 `"0.7"`，不会仅因书写尾零产生不同指纹；真正不同的浮点值（如 `0.7` 与 `0.7000000000000001`）才会改变哈希输入。
3. `parameter_sensitivity` 的边界已统一为代码条件 `long >= len(raw_train)`，正文表述改为“长周期不小于训练样本数”；保留 `long=40`、`N_train=35` 的 6 行示例。
4. T+1 实现边界已修正：`backtest.py` 有 `i <= last_buy_index` 的简化 A 股 T+1 防御性检查，但当前日线引擎每天最多一笔订单，买入后下一交易日 `i` 已大于 `last_buy_index`，正常流程不会同日买卖；因此 T+1 通常不是当前可观察到的 `blocked` 原因，不能与零成交量、涨跌停并列写成当前可触发的拒单条件。软件没有完整模拟可用持仓、历史持仓、盘中多订单或交易所级 T+1 制度。涉及 `signal_position_order_trade`、`next_open_execution`、`slippage_liquidity_market_impact`、`cash_position_and_pnl`、`lot_size_and_fractional_shares`。
5. 文章 `software_status` 保持不变：`signal_position_order_trade`、`next_open_execution` 仍为 `implemented`；`slippage_liquidity_market_impact`、`cash_position_and_pnl` 仍为 `needs_code_review`；`lot_size_and_fractional_shares` 仍为 `needs_code_review`。T+1 是防御性实现边界，不改变文章主体功能状态。
6. 状态统计不变：专业词条 85；`drafted` 40、`todo` 45；全目录 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13；批次 3 为 `implemented` 13、`needs_code_review` 3、`theory_only` 3、`academy_demo` 1。
7. 本次只修改 `docs/knowledge-drafts/` 下的 Markdown；未修改程序、测试、数据库、`VERSION`、构建或发行文件。

## 13. 批次 4：组合分析、统计推断、机器学习（25 篇）

### 13.1 完成状态

- 8 篇组合文章：`covariance`、`correlation`、`diversification`、`portfolio_weights_and_constraints`、`equal_weight`、`inverse_volatility`、`rebalancing_and_turnover`、`multi_currency_portfolio`。
- 9 篇统计文章：`sample_and_population`、`mean_and_median`、`sampling_distribution`、`standard_error`、`null_and_alternative_hypothesis`、`t_test`、`p_value`、`confidence_interval`、`autocorrelation_and_stationarity`。
- 8 篇机器学习文章：`features_and_targets`、`time_ordered_split`、`data_leakage`、`feature_scaling`、`prediction_baseline`、`mae_and_rmse`、`r_squared`、`time_series_cross_validation`。
- 文章状态全部为 `drafted`；外部来源内容未逐条读取，未标 `source_checked`。
- 软件状态：`implemented` 15 篇、`needs_code_review` 5 篇、`theory_only` 5 篇。
- 15 篇 `implemented`：`covariance`、`correlation`、`portfolio_weights_and_constraints`、`equal_weight`、`inverse_volatility`、`null_and_alternative_hypothesis`、`t_test`、`p_value`、`features_and_targets`、`time_ordered_split`、`data_leakage`、`feature_scaling`、`prediction_baseline`、`r_squared`、`time_series_cross_validation`。
- 5 篇 `needs_code_review`：`rebalancing_and_turnover`、`sample_and_population`、`mean_and_median`、`standard_error`、`mae_and_rmse`；正文均分三层写“已计算/已显示、只间接使用、未提供/未建模”。
- 5 篇 `theory_only`：`diversification`、`multi_currency_portfolio`、`sampling_distribution`、`confidence_interval`、`autocorrelation_and_stationarity`；正文明确写“当前软件未实现”。
- 未新增或删除 ID，专业词条总数仍为 85；未新增来源编号；批次 4 完成时专业文章状态为 `drafted` 65、`todo` 20；全目录功能状态保持 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13。

### 13.2 公式与口径清单

| 文章 ID | 核心公式/口径 | 软件状态 | 主要代码依据 | 待复核/说明 |
| --- | --- | --- | --- | --- |
| `covariance` | `cov=Σ(x−x̄)(y−ȳ)/(n−1)`；矩阵对角线为方差 | `implemented` | `portfolio.py:53-76`, `ui_analysis.py:92-100` | 全部共同日期同日收益率；不是价格协方差 |
| `correlation` | `ρ=cov/(s_x s_y)`；`[−1,1]` | `implemented` | `portfolio.py:53-76`, `ui_analysis.py:92-100` | Pearson；不证明因果或未来分散 |
| `diversification` | `σ_p²=w₁²σ₁²+w₂²σ₂²+2w₁w₂ρσ₁σ₂` | `theory_only` | 无独立实现 | 页面已显示样本外收益/波动/回撤；无独立分散化指标 |
| `portfolio_weights_and_constraints` | `w_i≥0`，`Σw_i=1`；等权或逆波动率 | `implemented` | `portfolio.py:19-78`, `ui_analysis.py:44-100` | 核心不掌握币种；界面限制同市场 |
| `equal_weight` | `w_i=1/n`；`r_p=(1/n)Σr_i` | `implemented` | `portfolio.py:60-66` | 不等于风险平价 |
| `inverse_volatility` | `w_i=(1/s_i)/Σ(1/s_j)` | `implemented` | `portfolio.py:38-44`, `portfolio.py:60-66` | 训练期日标准差；零/负/NaN 报错 |
| `rebalancing_and_turnover` | `r_p=Σw_i r_i`；`turnover=0.5Σ\|w_target−w_drift\|` | `needs_code_review` | `portfolio.py:63-72`, `ui_analysis.py:101-115` | 数学曲线已实现；换手/成本未实现 |
| `multi_currency_portfolio` | `r_investor=(1+r_local)(1+r_fx)−1` | `theory_only` | 无独立实现；界面限制同币种 | 无汇率、换算、对冲或跨币种净值 |
| `sample_and_population` | 样本 `s²=Σ(x−x̄)²/(n−1)`；总体 `σ²=Σ(x−μ)²/n` | `needs_code_review` | `statistics.py:44-60`, `metrics.py:58-79` | 样本口径已实现；总体公式未显示 |
| `mean_and_median` | `x̄=(1/n)Σx`；`med` 为排序中间值 | `needs_code_review` | `statistics.py:44-60`, `ui_analysis.py:137-141` | 均值已显示；中位数未显示 |
| `sampling_distribution` | 统计量重复抽样分布；`SE=σ/√n` | `theory_only` | 无重采样/模拟 | t 检验只用理论 t 分布 |
| `standard_error` | `SE=s/√n`；`t=(x̄−μ₀)/SE` | `needs_code_review` | `statistics.py:49-52` | t 检验内部使用；不单独显示 |
| `null_and_alternative_hypothesis` | `H0: μ=0`；`H1: μ≠0`（双侧） | `implemented` | `statistics.py:44-52`, `ui_analysis.py:141-146` | 无方向选择器或 α 输入 |
| `t_test` | `t=(x̄−0)/(s/√n)`；`df=n−1` | `implemented` | `statistics.py:44-60`, `ui_analysis.py:137-146` | 页面显示 p 值，不显示 t 值/自由度 |
| `p_value` | `p=P(至少同样极端结果\|H0)` | `implemented` | `statistics.py:51-52`, `ui_analysis.py:141-146` | 不是 H0 为真概率或盈利概率 |
| `confidence_interval` | `x̄±t_{1−α/2,n−1}s/√n` | `theory_only` | 无独立实现 | 未计算/显示 |
| `autocorrelation_and_stationarity` | `ρ_k=γ_k/γ_0`；弱平稳三条件 | `theory_only` | 无独立实现 | 无 ACF/Ljung–Box/ADF/KPSS |
| `features_and_targets` | 五个特征；`next_return=close(t+1)/close(t)−1` | `implemented` | `statistics.py:63-80` | 标签不是下一开盘交易收益 |
| `time_ordered_split` | `split=int(M×f)`；`train=[:split−1]`；`test=[split:]` | `implemented` | `statistics.py:87-97` | 一行间隔；不随机；非 walk-forward |
| `data_leakage` | 特征 `X_t` 只能依赖 `I_t` | `implemented` | `statistics.py:63-108` | 固定管线防护；无通用检测器 |
| `feature_scaling` | `z=(x−μ_train)/σ_train` | `implemented` | `statistics.py:98-108` | 只用训练集；scikit-learn 默认总体口径 |
| `prediction_baseline` | `MAE_0=(1/n)Σ\|y_t\|` | `implemented` | `statistics.py:119-128`, `ui_analysis.py:178-186` | 只实现零收益基线 |
| `mae_and_rmse` | `MAE=(1/n)Σ\|y−ŷ\|`；`RMSE=√(1/nΣ(y−ŷ)²)` | `needs_code_review` | `statistics.py:123-125`, `ui_analysis.py:178-186` | MAE 已显示；RMSE 未显示 |
| `r_squared` | `R²=1−SS_res/SS_tot`；分母为测试均值 | `implemented` | `statistics.py:125`, `ui_analysis.py:181` | 样本外可为负；常数目标按 `force_finite` 返回 0/1；不是相关系数平方 |
| `time_series_cross_validation` | `TimeSeriesSplit(3,gap=1)`；`cv_mae=mean(MAE_k)` | `implemented` | `statistics.py:98-107`, `ui_analysis.py:191-195` | 训练内 3 折；不是完整 walk-forward |

### 13.3 来源与核验

- 批次 4 未新增来源编号；沿用现有 S/P/A。`S001`–`S024` 外部页面未逐条读取；`S001`–`S007` 入口已由 Codex 于 2026-10-22 确认可访问，`S023`、`S024` 入口已由 Codex 于 2026-10-23 确认可访问；`S008`–`S022` 仍待核验。
- `A001`–`A031` 书目信息仍待复核；`A032`–`A035` 书目/DOI/ISBN 已核验。批次 4 使用 `A001`、`A003`、`A004`、`A005`、`A009`、`A010`、`A013`、`A016`、`A019`、`A020`、`A021`、`A024`、`A026`、`A027`、`A028`、`A029`、`A030`；这些引用只用于概念、公式和背景，不用于证明策略有效。
- 文章状态全部 `drafted`；未把“入口可访问”写成“内容已核验”；frontmatter 的 `last_verified: 2026-10-23` 仅表示本地代码/项目文档核对日期。

### 13.4 `needs_code_review` 分层结果

| 文章 ID | 已计算/已显示 | 只间接使用 | 未提供/未建模 |
| --- | --- | --- | --- |
| `rebalancing_and_turnover` | 固定权重每日收益数学曲线；累计净值；页面“未计调仓成本”说明 | 每日按固定权重加权，数学上等价于每日恢复目标权重 | 持仓股数、订单、成交、换手率、佣金、滑点、税费、整手、市场冲击 |
| `sample_and_population` | 样本量、均值、样本方差/标准差、年化波动率 | `n−1` 通过 `ddof=1`、t 检验标准误间接体现 | 总体公式、有限总体校正、抽样设计、参数置信区间 |
| `mean_and_median` | 日均收益率；t 检验分子；方差围绕均值 | 均值通过方差和 t 检验间接影响其他指标 | 中位数、截尾/缩尾均值、几何平均收益、均值/中位数区间 |
| `standard_error` | t 检验内部 `s/√n`；页面 p 值 | t 统计量由均值除以标准误；标准误影响 p 值 | 独立标准误指标、置信区间、HAC/聚类/bootstrap 标准误 |
| `mae_and_rmse` | 样本外 MAE；零收益基线 MAE；训练期 3 折 MAE | 线性回归训练使用平方误差损失；交叉验证 MAE 用于训练期评估 | RMSE、MSE、MAPE、误差分布、置信区间、成本调整误差 |

以上文章保持原 `software_status`，没有因为文章已撰写而改变功能状态；也没有把已实现部分写成 `theory_only`，或把未实现部分写成按钮/指标。

### 13.5 `theory_only` 边界

| 文章 ID | 当前软件明确没有提供的功能 |
| --- | --- |
| `diversification` | 无独立分散化比率、风险贡献、有效前沿或优化器；页面已显示等权/逆波动率组合的样本外累计收益、年化波动率和最大回撤，可用相关矩阵和曲线辅助讨论 |
| `multi_currency_portfolio` | 无汇率数据、换算、对冲、跨币种加总或跨币种净值；界面限制同市场同币种 |
| `sampling_distribution` | 无重采样、bootstrap、Monte Carlo 或抽样分布图；t 检验只用理论 t 分布 |
| `confidence_interval` | 无均值、波动率、相关系数、权重、MAE、R² 的置信区间；无预测区间 |
| `autocorrelation_and_stationarity` | 无 ACF/PACF、Ljung–Box、ADF、KPSS、单位根或平稳性检验；只在方法局限文字中提及 |

以上文章没有暗示不存在的按钮、图表、指标或计算结果。

### 13.6 自检结果

- 85 个专业词条 ID 无缺失、无重复；手册仍为 10 篇；批次 4 完成时专业文章为 `drafted` 65、`todo` 20。
- 批次 4 共 25 篇，目录和文件名准确：`portfolio` 8、`statistics` 9、`machine_learning` 8。
- 所有 `prerequisites`、`related_articles`、`source_ids` 均指向现有 ID/来源；没有悬空引用。
- 每篇文章包含完整 frontmatter 和“快速理解/软件实践/专业原理/相关知识/参考资料”模板，含手算例子、软件边界和参考资料。
- 五个 `needs_code_review` 词条均完成三层说明；五个 `theory_only` 词条均明确“当前软件未实现”。
- 全目录扫描未发现英文内部编辑批注或未完成标记；合法状态值 `todo` 除外。
- 所有手算例子已用独立脚本复核；关键数值包括协方差 `0.0001`、相关系数 `0.6547`、逆波动率权重 `57.14%/28.57%/14.29%`、t 值 `1.7253`、p 值 `0.0482`、R² `0.7647`、RMSE `1.1180%`、TimeSeriesSplit 三折索引。
- 使用独立 `--basetemp=/tmp/qb4-pytest-20261023` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；未跳过失败测试。
- 修改范围仅为 `docs/knowledge-drafts/`；未修改程序、测试、数据库、`VERSION`、构建脚本或发行文件。

### 13.7 需要 Codex 复核的问题（批次 4）

1. 确认组合页 `align_closes`：2–4 只、日期唯一、有效收盘价、内连接、至少 8 个共同收盘日；确认 `analyze_portfolio` 只接收历史表、不掌握币种。
2. 确认协方差/相关系数使用全部共同日期日收益率，pandas 样本口径 `ddof=1`；确认文章没有把相关系数写成因果或未来分散保证。
3. 确认 `split=int(len(returns)×train_fraction)`、训练比例 0.50–0.85、权重只用训练收益、样本外曲线在第一笔测试收益之前的共同收盘日期归一化为 1。
4. 确认等权 `1/n`、逆波动率 `(1/std_i)/Σ`、权重为正且合计 100%、零/负/NaN 波动率报错、没有做空/杠杆/上下限/优化器。
5. 确认 `rebalancing_and_turnover` 三层：`test @ equal`/`test @ inverse` 是数学曲线；不生成持仓/订单/成交；换手率和调仓成本未实现；不得写成真实可执行组合回测。
6. 确认统计页至少 3 个有效日收益、`std(ddof=1)`、`ttest_1samp(popmean=0.0)` 默认双侧、零标准差返回 `None`、页面只显示 p 值；确认 `sample_and_population`、`mean_and_median`、`standard_error` 三层说明准确。
7. 确认机器学习五个特征和 `next_return=close(t+1)/close(t)−1` 标签；确认零成交量→NaN、无限值/缺失值删除、均线预热/波动率窗口/最后一行导致样本减少。
8. 确认 `evaluate_linear_model` 的 60 行门槛、`split=int(M×f)`、`train=[:split−1]`、一行间隔、`test=[split:]`、训练 30/测试 10 行门槛、不随机打乱。
9. 确认 `Pipeline(StandardScaler(), LinearRegression())` 只在训练集拟合、每折新 Pipeline、`TimeSeriesSplit(n_splits=3,gap=1)`、`cv_mae` 为三折平均、不是完整 walk-forward。
10. 确认 MAE/零收益基线/R²/方向一致率口径；确认 RMSE 未计算或显示；确认 `data_leakage` 只声称固定内置管线有防护，不是通用泄漏检测器；确认五个 `theory_only` 词条没有虚构按钮、指标或图表。

### 13.8 声明

批次 4 只新增/修改 `docs/knowledge-drafts/` 下的 Markdown。未修改程序代码、测试、数据库、`VERSION`、安装器、构建脚本或发行文件；未执行打包、标签或 Release；未进入批次 5。25 篇文章仍是草稿，必须由 Codex 复核、转换、测试并通过实际 WebView 验收后，才能成为正式功能。

### 13.9 批次 4 修订（2026-10-23）

1. `diversification`：明确记录组合页已显示等权/逆波动率组合的样本外累计收益率、年化波动率和最大回撤；未实现的是独立分散化比率、风险贡献、边际风险贡献、有效前沿、优化器和“风险降低百分比”。删除关于页面显示范围的过窄表述；组合曲线差异改为归因于权重、样本区间或资产波动结构不同，不再使用未投资现金权重的解释。文章保持 `theory_only`。
2. `rebalancing_and_turnover`：明确标准单边换手率 `0.5×Σ|w_target−w_drift|` 由权重变化决定；单边调仓金额 = 组合市值 × 单边换手率；市值只影响金额，买卖方向影响费用类型，费用参数决定调仓成本。明确等权/逆波动率曲线使用同一组样本外资产收益，差异来自权重不同。手算例子改为“每日再平衡的累计换手不一定高于一次换手”，累计换手取决于完整收益路径、相对价格变化和观察期间，当前软件未计算，不能判断高低。文章保持 `needs_code_review`。
3. `mean_and_median`：把均值/中位数接近条件改为“对称分布中通常接近；偏斜和极端值常使二者分离；非对称样本也可能偶然相同或接近”。文章状态不变。
4. `feature_scaling`：修正标准化系数解释：`z_j` 增加 1 个单位（原特征增加一个训练集标准差）时，在其他特征不变条件下，预测的 `next_return` 改变 `β_j`；`β_j` 的单位是目标收益率单位，不是“目标变量每变化一个单位对应的特征变化”。保留相关特征导致系数不稳定、不能解释为因果的限制。
5. `prediction_baseline`：不再声称零收益基线经过训练期拟合或优化；它恒预测 0，不读取训练特征。分布漂移只改变其在不同测试区间的相对难度和 MAE。提及历史均值基线时明确当前软件未实现。
6. `r_squared`：补充 `SS_tot=0` 时当前 `r2_score` 默认 `force_finite=True` 的实际行为：预测与常数真实值完全一致返回 1.0，否则返回 0.0；页面没有专门警告，不能把 0.0/1.0 当成普通非退化测试集的 R²。
7. 同步更新 `CATALOG.md`、`REVIEW_NOTES.md` 和 `references/source-map.md` 中受影响的分散化和 R² 表述；`README.md` 无需修改。
8. 状态与计数保持不变：批次 4 共 25 篇且全部 `drafted`；`implemented` 15、`needs_code_review` 5、`theory_only` 5；专业词条 85；批次 4 修订时 `drafted` 65、`todo` 20；全目录 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13；手册 10 篇。
9. 使用独立 `--basetemp=/tmp/qb4-revision-pytest-20261023` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；未跳过失败测试。
10. 本次只修改 `docs/knowledge-drafts/` 下的 Markdown；未修改程序、测试、数据库、`VERSION`、构建或发行文件。

## 14. 批次 5：Python、数据处理与工程（20 篇）

### 14.1 完成状态

- 20 篇专业文章已写入 `articles/programming_engineering/`：`python_values_and_types`、`python_control_flow`、`python_functions`、`python_collections`、`python_exceptions`、`python_modules_and_packages`、`type_hints_and_dataclasses`、`numpy_arrays`、`pandas_series_and_dataframe`、`datetime_and_index`、`missing_data`、`returns_and_pct_change`、`rolling_window`、`alignment_join_and_merge`、`csv_and_json`、`sqlite_and_transactions`、`schema_migration`、`hash_and_fingerprint`、`provider_api_cache_and_concurrency`、`automated_testing_git_and_modular_monolith`。
- 文章状态全部为 `drafted`；外部来源内容未逐条读取，未标 `source_checked`。
- 软件状态全部为 `implemented`（20 篇）；这里的含义是相关技术确实被项目代码使用，不表示软件为用户提供独立的 Python、Git、数据库管理或编程教学工具。
- 未新增、删除或拆分 ID，专业词条总数仍为 85；全目录功能状态保持 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13。
- 专业文章状态更新为 `drafted` 85、`todo` 0；使用手册仍为 10 篇。
- 未新增来源编号；沿用 `S008`–`S011`、`S017`–`S020`、`P001`–`P004`、`A011`、`A012` 等现有来源。

### 14.2 关键口径与代码依据

| 文章 ID | 核心口径 | 软件状态 | 主要代码依据 | 待复核/说明 |
| --- | --- | --- | --- | --- |
| `python_values_and_types` | `1% = 0.01`；`1 bp = 0.0001`；`bool` 是 `int` 子类 | `implemented` | `backtest.py:14-38`, `strategy.py:51`, `metrics.py:20-26` | 浮点不承诺精确十进制；金融参数校验应显式排除布尔值 |
| `python_control_flow` | `decision_t = signal_{t−1}`；买入手数 `while lots > 0` | `implemented` | `strategy.py:43-51`, `backtest.py:96-160`, `refresh.py:28-67` | `while` 必须有终止推进；早返回不等于失败 |
| `python_functions` | 纯函数 vs 网络/文件/数据库副作用 | `implemented` | `metrics.py:30-79`, `backtest.py:62-65`, `data.py:71-111`, `storage.py:80-124` | 默认参数在定义时求值；避免可变默认值 |
| `python_collections` | 缓存键 `(market, symbol, start, end, adjustment)` | `implemented` | `processing.py:9-10`, `data.py:138-160`, `storage.py:90-124` | `set` 不保留业务排序；字典保留插入顺序 |
| `python_exceptions` | `DataValidationError(ValueError)`；`DataUnavailableError(RuntimeError)` | `implemented` | `processing.py:13-58`, `data.py:46-111`, `refresh.py:47-67`, `names.py:81-99` | 缓存/名称查询捕获较宽异常；名称失败不代表不存在 |
| `python_modules_and_packages` | 一个 `quant_lab` 常规包；核心模块不导入 Streamlit | `implemented` | `quant_lab/__init__.py`, `ARCHITECTURE.md:3-15`, `desktop_launcher.py:171-209` | 常规包含 `__init__.py`，命名空间包可不含；单体不以进程数定义；FastAPI 只是未来计划 |
| `type_hints_and_dataclasses` | 注解不自动运行时校验；`frozen=True` 非深度不可变 | `implemented` | `backtest.py:14-60`, `market_data.py:39-64`, `data.py:25-39` | `Protocol` 不自动鉴权或注册 Provider |
| `numpy_arrays` | `isfinite` 检查 NaN/±inf；`√252 ≈ 15.8745` | `implemented` | `processing.py:39-40`, `backtest.py:81`, `statistics.py:58`, `statistics.py:126` | 数组不是主要持久化格式；sin/cos 仅教学模拟 |
| `pandas_series_and_dataframe` | 列/索引/dtype；缓存返回 `copy(deep=True)` | `implemented` | `processing.py:33-58`, `data.py:155-157`, `strategy.py:40-52` | 索引对齐不是行号对齐 |
| `datetime_and_index` | 交易日无时区；UTC 接收时间；北京时间 UTC+08:00 | `implemented` | `processing.py:34`, `data.py:105-125`, `ui_updates.py:51-58` | `received_at` 不是交易所报价时间；无盘中时段模型 |
| `missing_data` | 必需字段缺失报错；组合共同日期 `dropna`；ML 零成交量→NaN | `implemented` | `processing.py:37-47`, `portfolio.py:32-34`, `statistics.py:63-80` | 无通用插值、均值填补或缺失机制模型 |
| `returns_and_pct_change` | `r_t=P_t/P_{t−1}−1`；首行 NaN | `implemented` | `metrics.py:67-69`, `statistics.py:46`, `statistics.py:73-77`, `portfolio.py:54` | 只有 `volume_change` 明确 `fill_method=None` |
| `rolling_window` | `rolling(window=N,min_periods=N).mean()`；5/20 与 10 日窗口 | `implemented` | `strategy.py:28-31`, `statistics.py:75-77` | 窗口按观测行/交易日，不补齐停牌日 |
| `alignment_join_and_merge` | 组合日期 `inner` join；回测 raw/signal 日期逐行完全一致 | `implemented` | `portfolio.py:19-35`, `research.py:38-41`, `processing.py:43-47` | 复权信号价与不复权成交价单位相同，但口径/尺度可不同；不是外连接，不自动填补 |
| `csv_and_json` | CSV UTF-8 字节；zlib BLOB；SHA-256；JSON 假设 | `implemented` | `storage.py:76-77`, `storage.py:95-124`, `storage.py:144-154`, `storage.py:171-188` | JSON 不是加密/签名/自动 schema 验证；部分 UI 下载带 BOM |
| `sqlite_and_transactions` | `timeout=15`、`Row`、`foreign_keys=ON`、commit/rollback/close | `implemented` | `storage.py:31-46`, `paths.py:37-52` | 未显式设置 `journal_mode`，不能断言固定日志模式；无远程数据库、用户隔离、加密或防篡改保证 |
| `schema_migration` | `SCHEMA_VERSION=4`；`user_version`；backup API；`BEGIN IMMEDIATE` | `implemented` | `migrations.py:10`, `migrations.py:90-118`, `paths.py:68-105` | 备份不是远程备份或灾难恢复；`stage_library` 是另一流程 |
| `hash_and_fingerprint` | 完整 SHA-256；`audit_id` 前 16 个十六进制字符 | `implemented` | `research.py:50-63`, `storage.py:120-121`, `storage.py:144-148`, `ai_context.py:33-35` | 不是加密、签名、身份认证或第三方存证 |
| `provider_api_cache_and_concurrency` | 历史 15 分钟/64 条；快照 5 分钟/1 秒；名称 24 小时/5 分钟 | `implemented` | `market_data.py:56-64`, `data.py:66-198`, `refresh.py:19-67`, `names.py:42-99` | 进程内缓存和锁；等待 60 秒/30 秒；single-flight 只合并同 key |
| `automated_testing_git_and_modular_monolith` | pytest、Git、模块化单体三部分 | `implemented` | `tests/`, `ARCHITECTURE.md:3-15`, `desktop_launcher.py:171-209`, `README.md:101-105` | 单体不以进程数定义；桌面父/子进程仍是一个应用；测试通过不等于 WebView/外部接口/安装包验收；Git 不是应用按钮 |

### 14.3 关键边界

- Python：`bool` 是 `int` 子类；浮点不承诺精确十进制；`None`、`NaN` 和 `0` 不是同一件事；软件不是 Python 控制台。
- 数据：必需行情字段中的不可解析值、NaN、无穷值、负成交量、非正价格和异常价格关系会显式报错；不使用演示数据替换真实行情。
- 缺失：组合按共同日期内连接并 `dropna`；机器学习把零成交量替换为 NaN，最终删除含缺失特征或标签的行；当前没有通用插值、均值填补或缺失机制模型。
- 收益率与窗口：简单收益率不是对数收益率；首行收益率通常为 NaN；滚动窗口按行/交易日，不按自然日，不补齐停牌日。
- 日期：行情 `date` 是无时区交易日；`received_at`、`created_at` 是 UTC；界面显示北京时间；`received_at` 不是交易所报价时间。
- 序列化：实验 CSV 是 UTF-8 字节，SQLite 中是 zlib 压缩 BLOB；读取先解压、核对 SHA-256，再 `read_csv(parse_dates=["date"], float_precision="round_trip")`；JSON 不是加密、签名或自动 schema 验证；部分界面下载使用 UTF-8 BOM。
- 数据库：`_connect` 使用 `timeout=15`、`sqlite3.Row`、`PRAGMA foreign_keys=ON`；正常提交、异常回滚、最后关闭；代码没有显式执行 `PRAGMA journal_mode`，实际日志模式由 SQLite 初始设置和数据库已有状态决定；没有远程数据库、用户隔离、加密或防篡改保证。
- 迁移：`SCHEMA_VERSION=4`；高版本拒绝打开；非空旧库升级前用 SQLite backup API 备份；`BEGIN IMMEDIATE` 事务，成功更新版本并提交，失败回滚；迁移保留旧实验行情 BLOB 和指纹；备份不等于远程备份或灾难恢复。
- 哈希：`raw_sha256`、`signal_sha256` 和附件保存完整 SHA-256；`audit_id` 是前 16 个十六进制字符（64 位）；哈希用于完整性检查和输入标识，不是加密、数字签名、身份认证或第三方存证。
- Provider/缓存：`MarketDataProvider` 是 Protocol，默认实现是 `AKShareProvider`；快照是最近历史日线收盘参考，不是实时行情；缓存和锁只在当前进程；single-flight 只合并相同 key；等待有超时。
- 名称与目录：名称成功缓存 24 小时、失败冷却 5 分钟；失败保留旧名称，无旧值显示“名称暂不可用”，不能断言退市或不存在；证券目录 24 小时缓存，内置目录只提供离线身份候选。
- 复合词条：`automated_testing_git_and_modular_monolith` 的自动化测试、Git 和模块化单体是三个不同概念；模块化单体按应用/代码库/部署与业务边界定义，不以进程数量定义；桌面父进程、Streamlit 子进程和 WebView2 附加进程仍共同构成一个应用；Git 不是应用按钮；FastAPI 是未来计划；测试通过不代表所有外部环境都已验证。

### 14.4 来源与核验

- 批次 5 未新增来源编号；沿用 `S008`–`S011`、`S017`–`S020`、`P001`–`P004`、`A011`、`A012`。
- `S008`–`S011`、`S017`–`S020` 的页面内容未在 2026-10-23 前联网核验；文章只引用语言/库的通用行为，不引用具体版本条款。
- 来源库当前把 `S019` 登记为 Git 文档、`S020` 登记为 pytest 文档；本批次按来源库编号引用，没有交换编号。
- `A011`（pandas）和 `A012`（NumPy）书目信息仍待复核；文章用它们作概念背景，不用来证明策略有效。
- 文章状态全部 `drafted`；未把“入口可访问”写成“内容已核验”；frontmatter 的 `last_verified: 2026-10-23` 仅表示本地代码/项目文档核对日期。
- 未新增 `official.md` 或 `academic.md` 条目，因为本批次没有新增来源编号。

### 14.5 自检结果

- 20 篇批次 5 文章全部存在，文件名与计划一致，文章状态全部 `drafted`。
- 专业文章 `drafted` 85、`todo` 0；85 个专业词条 ID 无缺失、无重复。
- 使用手册仍为 10 篇；专业词条仍为 85 个。
- 所有 `prerequisites`、`related_articles`、`source_ids` 均指向现有词条或来源编号；没有悬空引用。
- 每篇文章包含完整 frontmatter 和“快速理解/软件实践/专业原理/相关知识/参考资料”模板；包含白话解释、项目内使用位置、输入输出单位、当前软件边界、正式定义、可复核小例子、前提假设、边界情况、前置/关联词条和来源编号。
- 20 篇均保持 `implemented`；正文没有虚构用户界面、控制台、代码执行入口或独立 Python/Git/数据库教学工具。
- `automated_testing_git_and_modular_monolith` 已拆成自动化测试、Git、模块化单体三个清晰部分（正文标题为“第一部分：自动化测试”“第二部分：Git”“第三部分：模块化单体”），没有把三者写成同一概念。
- 全目录扫描未发现英文内部编辑批注或未完成标记；合法状态词 `todo` 仅出现在状态定义和“0 篇”计数中。
- Markdown 表格列数检查通过；所有表格行与分隔行列数一致。
- 所有手算示例已用独立脚本复核；关键数值包括 `0.1 + 0.2 = 0.30000000000000004`、佣金 `5/30`、卖出总费用 `80`、3 日均线 `12/13/14`、3 日样本标准差 `2/1/1`、共同日期 2 天、`dropna` 后 1 行、`isfinite` 结果 `[True, False, False, False, True]`、`√252 ≈ 15.874507866387544`、`SHA-256("abc")` 前 16 个十六进制字符 `ba7816bf8f01cfea`、SQLite 回滚 0 行/提交 1 行、北京时间 `2026-10-23T09:30:00+08:00`。
- 使用独立 `--basetemp=/tmp/qb5-pytest-20261023` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；未跳过失败测试。
- 修改范围仅为 `docs/knowledge-drafts/`；未修改程序、测试、数据库、`VERSION`、构建脚本或发行文件。

### 14.6 需要 Codex 复核的问题（批次 5）

1. 确认 `bool` 是 `int` 子类但在金融参数校验中不应把 `True` 当数值 `1`；当前文章说明了这一原则，没有声称所有配置字段都已显式拒绝布尔值。
2. 确认 `HistoryCache` 的 15 分钟/64 条、`SnapshotCache` 的 5 分钟/1 秒间隔、`RefreshCache` 的 60 秒等待和 `NameCache` 的 30 秒等待与代码一致；确认等待有超时，不是无限等待。
3. 确认 `force=True` 绕过 TTL/冷却但仍合并同键并发；确认缓存读取、页面重绘和失败尝试不更新上游成功时间。
4. 确认名称失败保留旧名称、无旧值显示“名称暂不可用”、不据此断言退市或不存在；确认证券目录 24 小时缓存和原子替换。
5. 确认 `SCHEMA_VERSION=4`、高版本拒绝打开、非空旧库升级前 backup API 备份、`BEGIN IMMEDIATE` 事务、成功更新 `user_version` 并提交、失败回滚；确认迁移保留旧实验 BLOB 和指纹。
6. 确认 `stage_library` 的复制、`PRAGMA integrity_check`、临时 bootstrap 文件和 `os.replace` 激活流程与 schema 迁移是不同流程。
7. 确认 `audit_id` 只取 SHA-256 前 16 个十六进制字符，完整 SHA-256 另存 `raw_sha256`/`signal_sha256`；确认附件完整哈希和 AI 上下文截短哈希的用途。
8. 确认 CSV 归档使用 UTF-8 无 BOM、部分界面下载使用 UTF-8 BOM；确认读取顺序为解压、核对 SHA-256、`read_csv(parse_dates=["date"], float_precision="round_trip")`。
9. 确认 `automated_testing_git_and_modular_monolith` 的三部分没有把 Git 写成应用功能、没有把 FastAPI 写成已实现；确认模块化单体不以进程数定义，桌面父进程、Streamlit 子进程和 WebView2 附加进程仍是一个应用；确认测试通过不等于真实 WebView/外部接口/安装包验收。
10. 确认 20 篇文章的 `implemented` 只表示技术被代码使用，不表示软件提供独立的 Python、Git、数据库管理或编程教学工具；确认没有虚构按钮或控制台。
11. 确认 `quant_lab` 是包含 `__init__.py` 的常规包；确认文章同时说明 Python 3 命名空间包可以没有 `__init__.py`，没有把常规包定义写成无例外的语言规则。
12. 确认项目代码没有显式执行 `PRAGMA journal_mode`；文章不应断言活动数据库固定使用 rollback journal 或 WAL，实际模式由 SQLite 初始设置和数据库已有状态决定。

### 14.7 声明

批次 5 只新增/修改 `docs/knowledge-drafts/` 下的 Markdown。未修改程序代码、测试、数据库、`VERSION`、安装器、构建脚本或发行文件；未执行打包、标签或 Release；批次 5 完成后停止，不进入正式接入或程序改造。20 篇文章仍是草稿，必须由 Codex 复核、转换、测试并通过实际 WebView 验收后，才能成为正式功能。

### 14.8 批次 5 修订（2026-10-23）

1. `hash_and_fingerprint`、`csv_and_json`：统一 SHA-256 长度表述为“完整 SHA-256：64 个十六进制字符，对应 256 位；`audit_id`：前 16 个十六进制字符，对应 64 位”；删除把 64 个十六进制字符误写成 64-bit 摘要的表述；可能产生歧义的截短说法改为“前 16 个十六进制字符”。
2. `alignment_join_and_merge`：删除“复权信号价与不复权成交价单位可以不同”的错误表述；改为两者单位相同（均为对应市场币种/股），但价格口径和数值尺度可能不同，日期序列必须逐行完全一致。
3. `python_modules_and_packages`：明确传统/常规 Python 包通常包含 `__init__.py`，Python 3 也支持没有 `__init__.py` 的命名空间包；本项目 `quant_lab` 是包含 `__init__.py` 的常规包。不再把“包必须带 `__init__.py`”写成无例外的语言定义。
4. `python_modules_and_packages`、`automated_testing_git_and_modular_monolith`：模块化单体改为按应用/代码库/部署与业务边界定义，不再定义为“只有一个操作系统进程”；明确它不要求运行时只有一个 OS 进程或线程，桌面父进程、独立 Streamlit 子进程和 WebView2 附加进程仍共同构成一个应用，不是可独立部署、通过远程业务 API 协作的微服务；核心计算模块与 UI 的依赖方向不变。
5. `sqlite_and_transactions`：明确 SQLite 可以使用 rollback journal、WAL 等日志模式；当前项目代码没有显式执行 `PRAGMA journal_mode`，不能仅凭代码断言活动数据库固定采用某个模式；实际模式由 SQLite 初始设置和数据库已有状态决定；项目明确依赖事务、`commit`/`rollback`、`foreign_keys`、backup API 和 `BEGIN IMMEDIATE`，而不是某个固定 `journal_mode`。
6. `automated_testing_git_and_modular_monolith`：删除正文中的当前分支名、当前测试数量和具体 `git push` 分支名；正文只说明测试数量会变化、具体分支和测试结果以当次 `git status`/`git log`/pytest 输出为准。精确分支、提交和测试数量保留在 `REVIEW_NOTES.md` 批次记录中。
7. 同步更新 `CATALOG.md`、`REVIEW_NOTES.md`、`references/source-map.md` 中受影响的哈希长度、价格单位、包定义、模块化单体进程模型、SQLite 日志模式和过期开发状态表述；`README.md` 未发现需要同步的受影响表述，未修改。
8. 状态与计数保持不变：批次 5 共 20 篇，全部 `implemented`、`drafted`；专业文章 `drafted` 85、`todo` 0；专业词条 85；使用手册 10 篇；全目录功能状态 `implemented` 61、`theory_only` 10、`academy_demo` 1、`needs_code_review` 13。
9. 使用独立 `--basetemp=/tmp/qb5-revision-pytest-20261023` 运行 `pytest -q`：115 passed，1 warning（`.pytest_cache` 路径权限提示）；未跳过失败测试。
10. 本次只修改 `docs/knowledge-drafts/` 下的 Markdown；未修改程序、测试、数据库、`VERSION`、构建或发行文件；未打包、未创建标签、未发布 Release。
