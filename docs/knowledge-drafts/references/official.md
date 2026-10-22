# 官方与项目内来源库

核验日期：2026-10-22

## 使用说明

- `S` 编号用于外部官方文档、数据服务和软件 API。
- `P` 编号用于本项目内已读的规范、架构、方法和数据文档；它们不是外部权威来源，只用于证明当前软件行为。
- S001–S007 的官方入口已由 Codex 于 2026-10-22 确认可访问；但入口可访问不等于接口字段、条款、生效日期或生效口径已经核验。S008–S022 在 2026-10-22 未联网核验。下列链接和用途来自项目现有文档或通行官方入口；所有外部来源的具体内容在发布前仍必须逐项核验。
- 会变化的交易规则、费用、结算、数据接口和软件 API 不应只依赖本表；写作和发布时应重新访问原始页面，并记录新的核验日期。
- 本表不使用搜索结果链接、聚合转载或内容农场作为关键定义的唯一来源。

## 外部官方来源

| ID | 标题 | 机构/作者 | 年份或版本 | 原始页面 | 适用市场/范围 | 支持的具体主张 | 核验状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S001 | AKShare 股票数据文档 | AKShare 项目 | 现行文档 | [AKShare 股票数据文档](https://github.com/akfamily/akshare/blob/main/docs/data/stock/stock.md) | A 股、港股历史日线 | `stock_zh_a_hist_tx`、`stock_hk_hist`、`stock_hk_daily` 接口与字段；复权参数 | 官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验 |
| S002 | 上海证券交易所交易规则 | 上海证券交易所 | 以官网现行版本为准 | [上海证券交易所交易规则](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml) | A 股 | 交易规则、申报单位、涨跌幅等制度背景；本软件只做简化假设 | 官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验 |
| S003 | 证券市场监管常见问题：交易运作 | 香港交易所 | 以官网现行版本为准 | [HKEX Securities Market Operations FAQ](https://www.hkex.com.hk/Global/Exchange/FAQ/Securities-Market/Trading/Securities-Market-Operations?sc_lang=en) | 港股 | 交易单位/每手股数等制度背景；软件要求用户自行核对交易单位 | 官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验 |
| S004 | 波动调节机制（VCM）常见问题 | 香港交易所 | 以官网现行版本为准 | [HKEX VCM FAQ](https://www.hkex.com.hk/Global/Exchange/FAQ/Securities-Market/Trading/VCM?sc_lang=en) | 港股 | 波动调节机制背景；当前回测未模拟 VCM | 官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验 |
| S005 | 列出模型 | DeepSeek | 现行 API 文档 | [DeepSeek List Models](https://api-docs.deepseek.com/api/list-models/) | DeepSeek API | 模型列表接口；软件从官方接口取得模型 ID 和能力 | 官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验 |
| S006 | Chat Completions | DeepSeek | 现行 API 文档 | [DeepSeek Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion/) | DeepSeek API | 对话补全、流式响应和错误状态 | 官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验 |
| S007 | JSON Output | DeepSeek | 现行指南 | [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/) | DeepSeek API | JSON 输出模式；软件在本地再次验证字段和参数 | 官方入口已由 Codex 于 2026-10-22 确认可访问，具体接口字段、条款和生效口径仍待逐项核验 |
| S008 | Python 3 文档 | Python Software Foundation | 现行版本 | [Python Documentation](https://docs.python.org/3/) | Python | 语言、异常、模块、类型注解、`sqlite3`、`dataclasses` 等 | NEEDS_REVIEW：页面未联网复核 |
| S009 | pandas 文档 | pandas 开发团队 | 现行版本 | [pandas Documentation](https://pandas.pydata.org/docs/) | Python 数据处理 | Series/DataFrame、索引、`pct_change`、`rolling`、缺失值、连接 | NEEDS_REVIEW：页面未联网复核 |
| S010 | NumPy 文档 | NumPy 开发团队 | 现行版本 | [NumPy Documentation](https://numpy.org/doc/stable/) | Python 数值计算 | 数组、有限值检查、向量化运算 | NEEDS_REVIEW：页面未联网复核 |
| S011 | SQLite 文档 | SQLite 开发团队 | 现行版本 | [SQLite Documentation](https://www.sqlite.org/docs.html) | SQLite | 数据库、事务、`PRAGMA user_version`、完整性检查 | NEEDS_REVIEW：页面未联网复核 |
| S012 | Microsoft Edge WebView2 Runtime | Microsoft | 现行版本 | [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) | Windows 桌面版 | 桌面窗口运行时；缺失时启动器提示安装 | NEEDS_REVIEW：页面未联网复核 |
| S013 | A 股基础目录 | 巨潮资讯 | 2026-10-14 接收快照 | [巨潮资讯 A 股基础目录](https://www.cninfo.com.cn/new/data/szse_stock.json) | A 股 | 代码与名称候选身份字段；不含价格和上市状态验证 | NEEDS_REVIEW：端点与字段未联网复核 |
| S014 | scikit-learn 用户指南 | scikit-learn 开发团队 | 现行版本 | [scikit-learn User Guide](https://scikit-learn.org/stable/user_guide.html) | 机器学习 | 预处理、模型评估、时间序列交叉验证背景 | NEEDS_REVIEW：页面未联网复核 |
| S015 | TimeSeriesSplit | scikit-learn 开发团队 | 现行版本 | [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) | 机器学习 | 时间序列交叉验证与 `gap` 参数 | NEEDS_REVIEW：页面未联网复核 |
| S016 | ttest_1samp | SciPy 开发团队 | 现行版本 | [scipy.stats.ttest_1samp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_1samp.html) | 统计 | 单样本 t 检验 | NEEDS_REVIEW：页面未联网复核 |
| S017 | dataclasses | Python Software Foundation | 现行版本 | [Python dataclasses](https://docs.python.org/3/library/dataclasses.html) | Python | 数据类、不可变配置对象 | NEEDS_REVIEW：页面未联网复核 |
| S018 | sqlite3 | Python Software Foundation | 现行版本 | [Python sqlite3](https://docs.python.org/3/library/sqlite3.html) | Python/SQLite | 连接、事务、参数化查询 | NEEDS_REVIEW：页面未联网复核 |
| S019 | Git 文档 | Git 项目 | 现行版本 | [Git Documentation](https://git-scm.com/doc) | 版本管理 | 分支、提交、远程同步、恢复点 | NEEDS_REVIEW：页面未联网复核 |
| S020 | pytest 文档 | pytest 开发团队 | 现行版本 | [pytest Documentation](https://docs.pytest.org/en/stable/) | 测试 | 自动化测试、断言和测试组织 | NEEDS_REVIEW：页面未联网复核 |
| S021 | Windows 凭据管理器 | Microsoft | 现行版本 | [Credential Manager](https://learn.microsoft.com/en-us/windows/win32/secauthn/credentials-management) | Windows | 用户凭据存储背景 | NEEDS_REVIEW：页面未联网复核 |
| S022 | CredWriteW | Microsoft | 现行版本 | [CredWriteW](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew) | Windows | 写入本应用凭据；配合 CredReadW/CredDeleteW | NEEDS_REVIEW：页面未联网复核 |

## 项目内依据

这些文档在 2026-10-22 已只读核对；它们证明当前软件的设计和口径，不是外部权威来源。

| ID | 文档 | 用途 | 核对状态 |
| --- | --- | --- | --- |
| P001 | [README.md](../../../README.md) | 安装、启动、资料库、使用方法、数据更新和 DeepSeek 配置 | 已读 |
| P002 | [ARCHITECTURE.md](../../../ARCHITECTURE.md) | 模块边界、数据合同、实验复现、AI 和迁移边界 | 已读 |
| P003 | [docs/METHODOLOGY.md](../../METHODOLOGY.md) | 策略信号、下一开盘成交、费用、指标、样本内外和机器学习边界 | 已读 |
| P004 | [docs/DATA.md](../../DATA.md) | 数据来源、字段、复权、缓存、名称和异常处理 | 已读 |
| P005 | [LEARNING.md](../../../LEARNING.md) | 学习路线、八节课程、统计页面操作顺序 | 已读 |
| P006 | [AGENTS.md](../../../AGENTS.md) | 项目边界、金融计算、数据复现、发布和 GUI 验收规范 | 已读 |

## 待复核事项

1. `S001`–`S007` 的官方入口已由 Codex 于 2026-10-22 确认可访问，但接口字段、条款、版本号、生效日期和生效口径仍需逐项核验；`S008`–`S022` 的页面内容未在 2026-10-22 联网核验。发布前必须重新访问原始页面。
2. `S002` 的上交所规则链接包含 2026 年日期，需确认是否为当前有效版本；`S003`、`S004` 的港交所页面需确认语言版本和更新时间。
3. `S001` 的 AKShare 文档需确认 A 股/港股接口名称、字段和复权参数仍与当前代码一致；上游接口可能变化。
4. `S013` 的巨潮资讯端点需确认仍可公开访问，且字段足以支持代码/名称候选；本软件不把目录当作上市状态验证。
5. `S005`–`S007` 的 DeepSeek API 文档需确认模型列表字段、JSON 输出要求和错误码；模型 ID 和能力可能变化。
6. `S008`–`S011`、`S014`–`S020` 的软件文档需确认版本与当前依赖一致；本项目不锁定上游文档版本。
7. 任何费用、税率、结算和交易规则数字在写入正式内容前必须以交易所、监管机构或券商官方资料重新核验；本手册只把它们作为可修改的研究假设。
