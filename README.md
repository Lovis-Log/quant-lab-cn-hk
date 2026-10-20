# Quant Lab CN/HK

面向中国 A 股与香港股票市场的个人量化研究与学习平台。V2 Learning Center MVP 提供市场数据、策略、回测、风险组合、统计机器学习、DeepSeek、Quant Academy、研究笔记和新手使用指引九个工作区。代码同步在 [私有 GitHub 仓库](https://github.com/Lovis-Log/quant-lab-cn-hk)。

> 这是学习与模拟研究平台，不提供实时行情、投资建议或真实资金交易。自选股快照是**最近历史日线收盘参考**，行情日期只有交易日，确切延迟未知；5 分钟轮询并非实时流式行情。未取得真实历史数据时，市场页只显示明确标记的模拟版式图，金融指标和表格保持空白。

## 项目结构

```text
app.py                   Streamlit 入口
quant_lab/data.py        AKShare A 股/港股历史日线获取
quant_lab/market_data.py Provider 合同与代码规范化
quant_lab/paths.py       用户可写目录
quant_lab/storage.py     SQLite 自选股与实验档案
quant_lab/learning.py    八节金融数学课程
quant_lab/guidance.py    九页指南、四条路径、八步任务与课程引用
quant_lab/learning_store.py SQLite 学习进度、测验、目标与恢复位置
quant_lab/ui_guidance.py 新手学习中心与统一帮助导航
quant_lab/processing.py  数据清洗与字段验证
quant_lab/metrics.py     价格收益与风险指标
quant_lab/strategy.py    均线与趋势信号
quant_lab/backtest.py    下一开盘模拟成交、成本与限制
quant_lab/research.py    样本内外回测与参数敏感性
quant_lab/portfolio.py   同币种多资产配置
quant_lab/statistics.py  假设检验与时间序列回归
quant_lab/ai_research.py DeepSeek 假设与报告草拟、本地参数验证
quant_lab/securities.py 可搜索证券目录与带来源时间的快照
quant_lab/ui*.py         页面、侧栏、各研究工作区
quant_lab/charts.py      Plotly 真实行情与演示图表
quant_lab/demo_data.py   明确标记的模拟版式数据
quant_lab/terminal.css   自有元素的少量样式
.streamlit/config.toml   官方深色主题配置
tests/                   应用与金融计算测试
docs/                    字段口径与方法假设
LEARNING.md              从高中数学到量化研究的学习路线
ARCHITECTURE.md          模块职责、数据流与未来边界
AGENTS.md                长期开发规范
CHANGELOG.md             里程碑记录
```

`demo_data.py` 只为页面预览服务，不参与金融计算。真实数据按“获取 → 验证 → 缓存 → 策略/统计计算 → 展示或归档”流动。模块边界详见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## Windows 启动

在项目目录下的 PowerShell 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

浏览器通常打开 `http://localhost:8501`。不必激活虚拟环境，直接使用其 Python 可避免 PowerShell 执行策略问题。查询真实行情需要联网。

## Windows 桌面版

- **安装版**：双击 `dist\installer\QuantLab-CN-HK-Setup.exe`，默认安装到 Windows 程序目录。安装后从开始菜单的 **Quant Lab CN-HK** 启动；安装时可选桌面快捷方式。正常卸载不会删除个人研究数据。
- **免安装版**：双击 `dist/packages/2.0.1-rc.1/QuantLab/QuantLab.exe`。必须保留整个 `QuantLab` 文件夹，不能只复制 EXE。Python 运行时已包含在该文件夹内，目标电脑无需另装 Python。
- 两种方式都在本机自动启动原有 Streamlit 后端，随机选一个空闲端口并**只监听 `127.0.0.1`**，随后在独立 pywebview 窗口打开；不会自动打开系统浏览器。关闭窗口后只停止本次启动的后端进程。
- Windows 电脑还需要 [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)。本安装包目前不内置它；若缺失，启动器会显示安装提示。当前构建的 EXE 和安装包未做商业代码签名，Windows 可能提示未知发布者。
- 用户设置、WebView 缓存、日志和 `research.sqlite3` 写入 `%LOCALAPPDATA%\QuantLabCNHK`，不写入安装目录。主要日志是 `logs\launcher.log`、`logs\streamlit.log` 和 `logs\data_errors.log`。可用 `QUANT_LAB_DATA_DIR` 指定另一用户可写目录。

### 开发环境启动桌面窗口

```powershell
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-desktop.txt
.\.venv\Scripts\python.exe desktop_launcher.py
```

开发调试用 `python.exe` 可查看错误；需要无控制台窗口时可用 `.\.venv\Scripts\pythonw.exe desktop_launcher.py`。原有 `streamlit run app.py` 方式仍可使用。

### 重建 EXE 和安装包

在 Windows PowerShell 中运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1 -BuildInstaller
```

第二条命令需要 `ISCC.exe`（Inno Setup 7/6）在 PATH、标准安装目录，或 `.tools\InnoSetup7` 便携目录。构建脚本先运行测试、再用 PyInstaller `onedir` 模式生成版本独立目录 `dist\\packages\\<版本>\\QuantLab`，避免清理正在使用的旧版目录；加 `-BuildInstaller` 时继续生成 Inno Setup 安装包。所有构建输出位于被 Git 忽略的 `dist\`。可用 `-SkipTests` 跳过已单独通过的测试。可选的真实浏览器打包冒烟测试为 `python tools\verify_packaged.py`；`python tools\verify_packaged.py --offline` 可离线检查启动、学院、自选股持久化和研究笔记。两种冒烟测试都需要另装 Playwright 和 Chrome，应用本身不依赖它们。

### GitHub Release 与过程记录

版本号保存在 `VERSION`。构建安装包后，脚本保留原有文件名，并生成带版本号的副本；构建日志与包含源码提交、测试结果、文件大小和 SHA-256 的记录位于 `dist/release/<版本>/`。

每次可交付安装包通过 [GitHub Releases](https://github.com/Lovis-Log/quant-lab-cn-hk/releases) 发布。发布过程及每版验证结果见 [docs/RELEASES.md](docs/RELEASES.md)。验证未完整的版本标记预发布，并在说明中记录限制。

`1.2.1-rc.1` 名称和 DeepSeek 修复曾仅在本地交付，记录保留。当前 V2 独立升级遵循项目通用同步与预发布流程；实际发布状态见 [发布记录](docs/RELEASES.md)。

V2 本地构建路径为 `dist/packages/2.0.1-rc.1/QuantLab/QuantLab.exe` 和 `dist\installer\QuantLab-CN-HK-2.0.0-rc.1-Setup.exe`，实际验证与构建状态见 [V2 验收报告](docs/V2_ACCEPTANCE.md)。[1.2.1 记录](docs/releases/v1.2.1-rc.1.md)和[1.2.0 升级记录](docs/UPGRADE_1.2.0.md)保留历史事实，不作为 V2 新验收证据。

### 常见问题

- **提示缺少 WebView2**：安装上述微软官方 Runtime 后重试。
- **启动超时或空白窗口**：检查 `%LOCALAPPDATA%\QuantLabCNHK\logs` 下的启动与服务日志。启动器最多等待 35 秒服务就绪、30 秒窗口加载。
- **8501 已占用**：桌面版自动选择其他 `127.0.0.1` 端口，不需要关闭原有 Web 版。
- **行情请求失败**：检查网络与数据源日志；应用不会把演示数据当成真实行情。
- **AI 功能未启用**：从顶栏打开 DeepSeek 助手，在停靠面板中配置密钥并选择模型；研究实验和对话共用同一连接，离线受控实验不需要 Key。

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 使用方法

1. 左侧选择市场，在“搜索股票候选（代码 / 名称）”里选股票或手动输入代码，设置日期范围与价格口径。A 股用六位代码（如 `600519`），港股用五位代码（如 `00700`）。点击 **加载真实历史日线**。
2. **市场数据**：查看实际交易日、价格/成交量、K 线、区间指标和 CSV 导出。
3. **策略实验室**：调节单均线、双均线或趋势策略周期，观察收盘后信号。
4. **历史回测**：设置示例资金、交易单位、费用、滑点和 A 股涨跌停假设；比较策略与同成本买入持有基准、样本内外及参数敏感性。
5. **风险与组合**：查看方差、标准差、波动率和回撤；输入同一市场的 2–4 只股票，比较等权与训练期逆波动率配置的样本外曲线。
6. **统计与机器学习**：查看均值为零的 t 检验和按时间切分的次日收益率线性回归。
7. **AI 研究助手**：即使没有 API Key，也可运行固定模板的受控实验和下载审计报告；配置 Key 后可草拟假设、示例代码和审阅意见。模型生成代码只展示，绝不自动执行。
8. **自选股**：股票以“市场 代码（公司简称）”显示，最多 10 只；名称接口失败保留代码。市场页显示最近日线收盘参考、行情日期、成功获取时间、来源、缓存年龄、更新结果及下次尝试时间。
9. **Quant Academy**：八节课程按“直觉、公式、手算例子、Python、调参实验、思考问题”学习；侧栏可切换学习/专业模式。
10. **研究笔记**：在历史回测页保存标题、假设、笔记和完整输入快照；在研究笔记页复算并导出 Markdown 报告或可复现 ZIP。
11. **新手使用指引**：阅读对应页面的真实控件说明，按八步任务实践；四条学习路径关联八节七层交互课程，保存实验并通过本地测验后标记课程完成。学习目标、笔记、课程位置与进度可重启恢复。

首次欢迎可开始或跳过，学习进度页可以重新启动。每个主要页面的“查看本页使用指南”打开对应教程，“返回研究任务”保留当前会话中的窗口、成本、训练比例和未保存笔记；研究数据跨重启恢复须使用存档。新手/专业模式只减少教学提示，金融计算一致。重置需要明确确认，仅清学习进度与测验，保留研究、行情、笔记和密钥。路径中“计划中”节点没有完整课程，不会伪造完成。

CSV 使用 UTF-8 with BOM，便于 Windows Excel 识别中文列名。已验证历史查询在进程内缓存 15 分钟，最多 64 个查询；自选股与已保存实验持久化到 SQLite。行情缓存不等于上游新数据。

## 数据更新机制

侧栏可设置 5、10 或 15 分钟轮询，默认 5 分钟；市场页按钮可暂停/恢复。只有市场页与相关会话运行时，已加载的当前历史查询和自选股才自动检查；关闭软件后不更新，策略/回测/课程/研究笔记不会后台更新数据。

“立即更新历史日线”和“立即更新自选股”绕过对应缓存，实际请求上游；同一查询的并发请求会合并，连续点击有 5 秒防抖，自选股上游请求至少间隔 1 秒。普通重绘保留会话数据，不伪造成功获取时间。成功但数据相同显示“检查成功，数据未变化”；失败保留上次有效数据，标明可能过期。显示时间均为北京时间 `UTC+08:00`。行情日期是价格对应的交易日，确切延迟未知。

更新行情不会修改已有研究快照。重新研究应运行回测并另存实验；档案复算只读原始输入。名称从东方财富证券资料接口取得，按市场＋代码缓存 24 小时，失败重试冷却 5 分钟；不会重绘就拉全量列表。

## DeepSeek 配置与对话

应用顶部提供横跨整个窗口的固定工作台导航栏；**新手使用指引**和 **DeepSeek 助手**不再占用左侧导航。两个入口可独立打开，也可同时作为 VS Code 风格的右侧停靠面板显示。拖动任一面板左边缘可调整宽度；按住顶栏中的任一面板按钮并左右拖过另一按钮，可同步交换顶栏按钮与对应面板顺序。宽度与顺序只保存在本机 WebView。面板不产生遮罩，左侧导航和中间研究区仍可见、可操作，中间区会为总面板宽度让出空间。AI 研究实验保留在 DeepSeek 面板的“AI 工作区”切换中。展开“DeepSeek 连接设置”，填写密码形式的 API Key，点击“测试连接”读取官方 `https://api.deepseek.com/models`。在下拉框选择可用模型，或在列表失败时手动填写模型 ID；下一条发送使用新模型，历史回答保留实际模型标记。思考强度仅在模型列表声明支持时提供，不向所有模型强行发送温度等参数。

默认密钥仅在当前会话内。选“记住密钥”并应用时写入 Windows 凭据管理器；下一次启动会自动读取本应用已记住的密钥，也可手动重新读取。系统安全存储不可用时仍为会话模式，绝不写入明文文件或 SQLite。“清除密钥”清除会话及本应用已记住凭据，不修改其他工具配置。

使用的是用户自己的 DeepSeek API 账户。“发送到 DeepSeek”“生成 AI 假设”“让 AI 审阅实验”分别触发付费请求；测试连接/刷新列表只查询模型，重绘、行情轮询和课程切换不发送对话。支持流式回答、清空对话及把选定回答保存为学习笔记。发送前可查看当前程序事实摘要，默认不附带私人笔记、完整行情或数据库；切换数据或实验后不会发送上一份研究的对话历史。没有 Key 时离线课程、知识解释与研究功能照常使用。

接口说明：[DeepSeek 官方模型列表](https://api-docs.deepseek.com/api/list-models/)、[Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)。首次真实连接请在软件内测试，不要把 Key 发到聊天。

## 数据库升级与知识解释

SQLite schema 版本为 3；首次打开旧库时在用户数据目录 `backups/` 创建一致性备份，用事务补足名称、设置、证券资料、学习笔记以及新增进度/测验表。失败回滚原库，重复执行不会重复迁移；旧实验和行情 BLOB 不重写，旧指纹仍可复算与导出。

知识内容集中在 `knowledge.py`，离线提供定义、刻画特征、研究意义、公式与符号、手算例子、当前值模板解读、局限和思考题。覆盖八节课程及费用、滑点、年化收益、基准、p 值、MAE、R²、协方差。知识入口的“向 AI 追问”只填写草稿，仍需确认发送。

## 数据口径与限制

- A 股通过 AKShare 的腾讯接口，港股以 AKShare 的东方财富历史接口为主、失败时回退新浪接口并明确标注；价格和成交额分别使用 CNY/HKD，成交量单位为股。可选不复权、前复权或后复权。字段与来源详见 [docs/DATA.md](docs/DATA.md) 和 [AKShare 股票数据文档](https://github.com/akfamily/akshare/blob/main/docs/data/stock/stock.md)。
- 本应用只做**股票**研究，不提供指数模块；输入框只核对位数，尚未用交易所名录验证代码身份，请勿输入指数代码。
- 区间收益率使用首尾两个**实际交易日收盘价**：`R = P_end / P_start - 1`。只有一个交易日时不显示收益率。它是简单**价格**收益率，不含现金分红、交易费用或滑点；除权除息会影响不复权价格的可比性，不应把它解释为总回报或可实现收益。
- 回测信号可以使用选定的复权价格，但模拟成交和净值始终使用同日期的**不复权开盘/收盘价**。日线无法验证订单簿成交、真实费用、停牌细节、涨跌停队列或幸存者偏差；详见 [docs/METHODOLOGY.md](docs/METHODOLOGY.md)。
- 上游请求或字段验证失败时，错误会显示在页面，详细异常写入用户数据目录的 `logs/data_errors.log`；不会用模拟数据替代。

## DeepSeek 研究助手与股票候选

“AI 研究助手”在本页集中配置 DeepSeek 会话密钥和模型，通过“研究实验 / 对话与辅导”切换用途，不再要求 OpenAI 环境变量。依次填写研究问题、生成假设、运行本地受控实验、让 AI 审阅实验。结构化回复遵循 [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/) 并在本地验证字段与策略参数；示例代码不执行，报告记录实际模型。未配置时仍可使用固定策略运行实验、下载本地审计报告。

候选目录包含 2026-10-14 接收的 6,181 条 A 股、3,033 条五位港股资料（含 H 股、非 H 股与红筹股）；巨潮资讯 A 股目录和东方财富港股证券资料只提供代码与名称。常见股票排在前面，输入代码或中文名称可搜索，在同一个“股票（代码 / 名称）”框中选择候选；未收录代码可输入后选择新增项确认，仍需加载日线。目录不是买入推荐，也不验证证券当前上市或可交易状态。“更新股票候选目录”联网更新，失败保留旧目录和获取时间；运行时更新写入用户目录，安装目录只读。

名称改用东方财富证券基础资料接口，避免原 A 股报价接口断连导致名称缺失。“重新获取证券名称”可绕过成功缓存与失败冷却，成功后当前已加载行情的名称也会更新；失败保留已知名称并显示警告。

统计页面的操作和指标含义见 [LEARNING.md](LEARNING.md#统计与机器学习页面的操作顺序)，页面内也有“这个页面怎么用”。

DeepSeek 的连接、问答与研究实验统一从顶栏停靠面板使用，并提供“研究实验 / 对话与辅导”及“研究解释模式 / 教学辅导模式”。新手使用指引在相邻停靠面板提供教程、课程、测验、目标和进度。统计模型运行后摘要包含实际检验结果、训练/测试数量、MAE、基线、R² 与方向；课程摘要包含定义、参数和教学结论，不含测验答案、私人笔记或学习目标。切换数据、实验、课程、指南或模式会隔离发送的历史。点击知识追问/课程辅导会同时保留学习面板并打开 DeepSeek 面板准备草稿，确认发送才请求模型。AI 不可用时全部操作教程、教学实验、测验与进度仍正常。

项目审查和后续 P2/P3 计划见 [V2_PLAN.md](docs/V2_PLAN.md)，本次金融、统计、Python、数据库和架构学习报告见 [V2_LEARNING_REPORT.md](docs/V2_LEARNING_REPORT.md)。本版没有新增大型机器学习框架、因子研究、优化器或实时行情。
