# 使用手册与专业知识库草稿

本目录是 Quant Lab CN/HK `2.2.0-rc.1` 使用手册与专业知识库的内容输入。这里的 Markdown 是**草稿**，还不是应用内功能；必须由 Codex 复核、转换、测试并通过实际 WebView 验收后，才能进入软件。

## 当前状态

- 批次 1：10 篇使用手册已完成草稿并通过复核修订（2026-10-22）。
- 批次 2：市场与数据、收益与风险 20 篇专业文章已起草并完成修订（2026-10-23）。
- 批次 3：策略与执行、回测与研究 20 篇专业文章已起草（2026-10-23）。
- 批次 4：组合分析 8 篇、统计推断 9 篇、机器学习 8 篇，共 25 篇专业文章已起草（2026-10-23）。
- 85 个专业词条已在 `CATALOG.md` 建立稳定 ID、分类、状态、模块、关联词条和主要来源；其中 65 篇为 `drafted`，20 篇为 `todo`。专业词条状态为 `implemented` 61、`needs_code_review` 13、`theory_only` 10、`academy_demo` 1。
- 官方、学术和项目内来源见 `references/`；编号与核验状态以来源库为准。外部来源内容未逐条读取，文章不标 `source_checked`。
- 未修改程序代码、测试、数据库、`VERSION`、构建脚本或发行文件。

## 文件结构

```text
docs/knowledge-drafts/
  README.md                 本说明
  CATALOG.md                10 篇手册 + 85 个词条的总目录
  REVIEW_NOTES.md           批次 1 复核、批次 2–3 修订与批次 4 记录、needs_code_review 和 NEEDS_REVIEW
  manual/                   10 篇使用手册草稿
    quick_start.md
    workspace.md
    market_data.md
    strategy.md
    backtest.md
    risk_portfolio.md
    statistics_ml.md
    academy.md
    deepseek.md
    research_notes.md
  references/
    official.md             外部官方来源 S001–S024；项目内依据 P001–P006
    academic.md             学术来源 A001–A035
    source-map.md           手册/文章 ID 到来源与代码位置的映射
  articles/
    market_data/            市场与数据 10 篇（已起草）
    return_risk/            收益与风险 10 篇（已起草）
    strategy_execution/     策略与执行 10 篇（已起草）
    backtest_research/      回测与研究 10 篇（已起草）
    portfolio/              组合分析 8 篇（已起草）
    statistics/             统计推断 9 篇（已起草）
    machine_learning/       机器学习 8 篇（已起草）
```

## 阅读顺序

1. `CATALOG.md`：先看状态、范围、重复/缺口和待 Codex 事项。
2. `REVIEW_NOTES.md`：看 `needs_code_review`、`NEEDS_REVIEW` 和优先复核清单。
3. `manual/`：按页面阅读 10 篇手册。
4. `references/`：核对来源和支持的具体主张。

## 状态约定

- 功能状态：`implemented`、`academy_demo`、`theory_only`、`needs_code_review`。
- 文章状态：`todo`、`drafted`、`source_checked`、`review_needed`。
- `implemented` 必须有本地代码依据；未实现能力必须标 `theory_only`；无法确认的事实交回 Codex，不猜测。
- 外部来源未联网核验时标 `NEEDS_REVIEW`；软件行为以本地代码和项目文档为准。

## 批次工作方式

- 每批只交付一个批次，完成后更新 `CATALOG.md` 和 `REVIEW_NOTES.md`。
- 当前批次：批次 4（组合分析、统计推断、机器学习，共 25 篇专业文章；2026-10-23 完成草稿）。
- 下一批次（未开始）：批次 5（Python、数据处理与工程，共 20 篇）。
- 后续批次依次为：批次 5（20）、全局统一与来源复核（6）。

## 边界

- 不修改 `quant_lab/`、`tests/`、`app.py`、`desktop_launcher.py`、SQLite schema、Provider、金融计算、`VERSION`、安装器、构建脚本或 Release 文件。
- 不把模拟、缓存或历史日线写成实时行情；不写投资建议、收益承诺或实盘执行暗示。
- 不调用付费模型 API，不写入或索取任何密钥。
- 手册不使用复选框、任务状态、测验、打卡、完成度或“完成本章”措辞。
