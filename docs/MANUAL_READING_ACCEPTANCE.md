# 文字手册版阶段 5 验收记录

日期：2026-10-24

分支：`codex/manual-reading-v1`

验收起点：`00e1312`

范围：源码、离线内容、浏览器和实际 WebView2；不含打包、安装、标签或 Release

## 结论

阶段 5 通过。文字手册版可以离线加载 10 篇手册和 85 篇专业文章，默认打开使用手册，并保留市场数据、策略、回测、组合、统计、DeepSeek、Quant Academy 和研究笔记能力。任务式学习产品继续保留在 `codex/learning-center-v2`。

## 自动测试

执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

结果：`127 passed`。

覆盖内容包括：

- 10 篇手册和 85 篇专业文章全部可发现、解析和查询；
- 分类数量为 10/10/10/10/8/9/8/20；
- 软件状态为 `implemented` 61、`needs_code_review` 13、`theory_only` 10、`academy_demo` 1；
- 必填 frontmatter、重复 ID、非法状态和缺失引用均显式失败；
- 中文标题、英文标题、别名、正文及手册正文搜索；
- 离线启动不访问 requests 或 socket，上游不可用时仍能阅读手册和打开 Academy；
- 旧 SQLite 学习表和记录在 schema v4 下保持可读，不删除、不迁移；
- DeepSeek 只有明确发送才调用模型，Key 不进入普通设置或数据库。

## Browser 插件验收

ego lite 未安装，Windows 环境无法通过技能脚本自动安装；按用户授权和浏览器技能规则改用可用的 ChatGPT Browser 插件。测试地址为 `http://127.0.0.1:8515/`，浏览器视口为 1280×720，用户目录和凭据目标均与真实资料隔离。

浏览器实际检查：

- 页面标题为 `Quant Lab CN/HK`，首屏非空，无框架异常覆盖层；
- 使用手册默认打开，关闭后可重新打开；
- 全部 10 篇功能手册逐篇打开并返回目录；
- 八个专业分类数量全部与内容模型一致；
- 抽样 16 篇专业文章，覆盖八个分类和四种软件状态；
- 验证空搜索、前置概念、相关词条、下一篇和文章间跳转；
- 验证长篇 Python 文章代码块、独立滚动和固定标题；
- 验证“显示详细解释提示”和 `⚙ → DeepSeek` 文案；
- 验证手册、DeepSeek、研究笔记三面板同时打开、关闭重开、左栏切换、拖宽、排序和最大化；
- 浏览器控制台 error/warning 均为 0。

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
- 手册默认入口、三入口、目录、搜索、代码块和状态通过；
- 三面板固定标题、滚动、拖宽、排序、最大化/恢复和左栏边界通过；
- Academy 第 8 课解释通过，旧任务/测验/进度控件不存在；
- DeepSeek 设置和凭据控件通过；
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
