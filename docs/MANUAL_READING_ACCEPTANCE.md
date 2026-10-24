# 文字手册版验收记录

日期：2026-10-24

分支：`codex/manual-reading-v1`

验收起点：`00e1312`

本轮搜索与面板优化起点：`6b33268`；恢复分支：`codex/recovery-before-manual-search-ui-20261024`

范围：源码、离线内容、浏览器和实际 WebView2；不含打包、安装、标签或 Release

## 结论

验收通过。文字手册版可以离线加载 10 篇手册和 85 篇专业文章，默认打开使用手册，并保留市场数据、策略、回测、组合、统计、DeepSeek、Quant Academy 和研究笔记能力。本轮新增确定性相关度搜索、固定工具栏、术语直达和 DeepSeek 聊天优先布局；任务式学习产品继续保留在 `codex/learning-center-v2`。

## 自动测试

执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

结果：`134 passed`。

覆盖内容包括：

- 10 篇手册和 85 篇专业文章全部可发现、解析和查询；
- 分类数量为 10/10/10/10/8/9/8/20；
- 软件状态为 `implemented` 61、`needs_code_review` 13、`theory_only` 10、`academy_demo` 1；
- 必填 frontmatter、重复 ID、非法状态和缺失引用均显式失败；
- 中文标题、英文标题、别名、核心解释、正文及手册正文的统一相关度搜索；
- 精确匹配优先、正文弱匹配、稳定同分顺序、上下文解释片段、空查询和 12 项分页；
- 10 篇手册的相关术语全部解析为文章 ID，引用存在且过期提示已删除；
- 双列结果、显示更多、搜索/目录返回、搜索结果文章返回和术语/文章关联跳转；
- DeepSeek 打开即聊天、设置默认隐藏、研究实验进入/返回且切换不触发模型请求；
- 离线启动不访问 requests 或 socket，上游不可用时仍能阅读手册和打开 Academy；
- 旧 SQLite 学习表和记录在 schema v4 下保持可读，不删除、不迁移；
- DeepSeek 只有明确发送才调用模型，Key 不进入普通设置或数据库。

## ego-browser 验收

使用已安装的 ego lite `0.6.0.22` 和独立 TaskSpace 18 检查源码服务 `http://127.0.0.1:8516/`；数据目录与凭据目标均与真实资料隔离。ego lite 报告有可用更新，本轮未获升级授权，因此保持当前已验证版本。

浏览器实际检查：

- “复权”查询返回 53 项，默认渲染 12 张卡片；展开后为 24 张，首项是“价格复权 / Price Adjustment”并带“最相关”和一句话解释；
- 相邻两张卡片横向并列，最大化面板中为等宽双列；
- 滚动搜索结果 1200px 后，分区、返回和搜索工具栏保持可见；该检查先发现 Streamlit 包装层限制 sticky，修复后复验通过；
- 从搜索打开文章再返回可恢复查询和 24 项展开状态，继续返回可恢复搜索前的快速开始；
- 快速开始中的“价格复权”相关术语直接打开对应专业文章；
- DeepSeek 打开后聊天输入框直接可见，设置内容默认不可见；展开设置可见回答模式、事实摘要、上下文预览、快捷问题和清空操作；
- 研究实验可进入并返回聊天，过程中未发送模型请求；
- 最终页面标题、手册/DeepSeek 面板和输入框可见，Streamlit 异常元素为 0。

专业文章视觉样本：

- 市场与数据：OHLCV、Trading Calendar；
- 收益与风险：Log Return、Maximum Drawdown；
- 策略与执行：Next-Open Execution、Mean Reversion；
- 回测与研究：Overfitting、Cash, Position, and PnL；
- 组合分析：Diversification、Rebalancing and Turnover；
- 统计推断：t-Test、Confidence Interval；
- 机器学习：Features and Targets、MAE and RMSE；
- Python 与工程：Python Functions、SQLite and Transactions。

## 实际 WebView2 验收

执行：

```powershell
.\.venv\Scripts\python.exe tools\verify_desktop_gui.py --manual-reading
```

使用独立 `.tools/desktop-validation-*` 用户目录和随机测试凭据目标。最终结果：

- 实际 WebView DOM 和页面身份通过；
- 手册默认入口、三入口、目录、12 张双列搜索卡片、固定工具栏、代码块和状态通过；
- 三面板固定标题、滚动、拖宽、排序、最大化/恢复和左栏边界通过；
- Academy 第 8 课解释通过，旧任务/测验/进度控件不存在；
- DeepSeek 打开即聊天、隐藏设置入口、研究实验入口、全局连接设置和凭据控件通过；
- 控制台 error/warning 为 0，Streamlit 控件状态警告为 0；
- WebView loaded 事件、子进程关闭和退出码均通过。

## 已知限制与未验证范围

- 1280px 宽度同时打开三个右侧面板会明显压缩主工作区；面板本身仍可阅读和独立滚动。窄窗口建议只保留一到两个面板，或最大化当前面板。
- 当前桌面窗口最小宽度为 1100px，没有单独验收手机视口。
- 真实付费 DeepSeek 请求未执行；仅验证本地控件、隔离模拟和显式发送边界。
- 阶段 5 使用离线/隔离数据，没有把真实上游行情请求作为完成条件。
- 未构建当前源码的 EXE 或安装器，因此没有注册或验证安装器测试 AppId；不能用旧安装包代表当前源码。AppId、安装、升级和卸载只在用户另行授权发行流程后验证。
- 95 篇内容全部经过程序化完整性测试；视觉检查采用全部 10 篇手册加跨分类、跨状态的 16 篇专业文章，不声称逐篇人工审读 85 篇文章。

## 外部来源状态

- S001–S007、S023–S024 的官方入口曾确认可访问，但具体接口字段、条款、生效口径仍未逐项核验；
- S008–S022 仍为 `NEEDS_REVIEW`；
- A001–A031 仍为 `NEEDS_REVIEW`；
- A032–A035 的书目、DOI 或 ISBN 已核验；
- 85 篇专业文章保持 `drafted`，不得称为全部来源已核验或正式发布内容。

## 发行边界

本阶段未修改 `VERSION`，未构建 EXE/安装包，未创建或推送标签，未创建或发布 GitHub Release。
