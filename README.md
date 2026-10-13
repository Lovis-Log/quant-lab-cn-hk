# Quant Lab CN/HK

面向中国 A 股与香港股票市场的个人量化研究与学习平台。当前提供市场数据、策略、回测、风险组合、统计机器学习、可选 AI 助手、Quant Academy 和研究笔记八个工作区。代码同步在 [私有 GitHub 仓库](https://github.com/Lovis-Log/quant-lab-cn-hk)。

> 这是学习与模拟研究平台，不提供实时行情、投资建议或真实资金交易。自选股快照是**最近历史日线收盘参考**，行情日期只有交易日，确切延迟未知；5 分钟轮询并非实时流式行情。未取得真实历史数据时，市场页只显示明确标记的模拟版式图，金融指标和表格保持空白。

## 项目结构

```text
app.py                   Streamlit 入口
quant_lab/data.py        AKShare A 股/港股历史日线获取
quant_lab/market_data.py Provider 合同与代码规范化
quant_lab/paths.py       用户可写目录
quant_lab/storage.py     SQLite 自选股与实验档案
quant_lab/learning.py    八节金融数学课程
quant_lab/processing.py  数据清洗与字段验证
quant_lab/metrics.py     价格收益与风险指标
quant_lab/strategy.py    均线与趋势信号
quant_lab/backtest.py    下一开盘模拟成交、成本与限制
quant_lab/research.py    样本内外回测与参数敏感性
quant_lab/portfolio.py   同币种多资产配置
quant_lab/statistics.py  假设检验与时间序列回归
quant_lab/ai_research.py 可选 OpenAI 假设与报告草拟
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
- **免安装版**：双击 `dist\QuantLab\QuantLab.exe`。必须保留整个 `QuantLab` 文件夹，不能只复制 EXE。Python 运行时已包含在该文件夹内，目标电脑无需另装 Python。
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

第二条命令需要 `ISCC.exe`（Inno Setup 7/6）在 PATH、标准安装目录，或 `.tools\InnoSetup7` 便携目录。构建脚本先运行测试、再用 PyInstaller `onedir` 模式生成 EXE；加 `-BuildInstaller` 时继续生成 Inno Setup 安装包。所有构建输出位于被 Git 忽略的 `dist\`。可用 `-SkipTests` 跳过已单独通过的测试。可选的真实浏览器打包冒烟测试为 `python tools\verify_packaged.py`；`python tools\verify_packaged.py --offline` 可离线检查启动、学院、自选股持久化和研究笔记。两种冒烟测试都需要另装 Playwright 和 Chrome，应用本身不依赖它们。

### GitHub Release 与过程记录

版本号保存在 `VERSION`。构建安装包后，脚本保留原有文件名，并生成带版本号的副本；构建日志与包含源码提交、测试结果、文件大小和 SHA-256 的记录位于 `dist/release/<版本>/`。

每次可交付安装包通过 [GitHub Releases](https://github.com/Lovis-Log/quant-lab-cn-hk/releases) 发布。发布过程及每版验证结果见 [docs/RELEASES.md](docs/RELEASES.md)。验证未完整的版本标记预发布，并在说明中记录限制。

### 常见问题

- **提示缺少 WebView2**：安装上述微软官方 Runtime 后重试。
- **启动超时或空白窗口**：检查 `%LOCALAPPDATA%\QuantLabCNHK\logs` 下的启动与服务日志。启动器最多等待 35 秒服务就绪、30 秒窗口加载。
- **8501 已占用**：桌面版自动选择其他 `127.0.0.1` 端口，不需要关闭原有 Web 版。
- **行情请求失败**：检查网络与数据源日志；应用不会把演示数据当成真实行情。
- **AI 功能未启用**：按下文配置你自己的 `OPENAI_API_KEY`；离线受控实验不需要 Key。

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 使用方法

1. 左侧选择市场、股票代码、日期范围与价格口径；A 股用六位代码（如 `600519`），港股用五位代码（如 `00700`）。点击 **加载真实历史日线**。
2. **市场数据**：查看实际交易日、价格/成交量、K 线、区间指标和 CSV 导出。
3. **策略实验室**：调节单均线、双均线或趋势策略周期，观察收盘后信号。
4. **历史回测**：设置示例资金、交易单位、费用、滑点和 A 股涨跌停假设；比较策略与同成本买入持有基准、样本内外及参数敏感性。
5. **风险与组合**：查看方差、标准差、波动率和回撤；输入同一市场的 2–4 只股票，比较等权与训练期逆波动率配置的样本外曲线。
6. **统计与机器学习**：查看均值为零的 t 检验和按时间切分的次日收益率线性回归。
7. **AI 研究助手**：即使没有 API Key，也可运行固定模板的受控实验和下载审计报告；配置 Key 后可草拟假设、示例代码和审阅意见。模型生成代码只展示，绝不自动执行。
8. **自选股**：在市场数据页加入当前股票（最多 10 只），查看历史日线收盘参考、行情日期、接收时间、来源与缓存状态；默认每 5 分钟检查一次，可暂停或手动刷新，手动请求最短间隔 60 秒。
9. **Quant Academy**：八节课程按“直觉、公式、手算例子、Python、调参实验、思考问题”学习；侧栏可切换学习/专业模式。
10. **研究笔记**：在历史回测页保存标题、假设、笔记和完整输入快照；在研究笔记页复算并导出 Markdown 报告或可复现 ZIP。

CSV 使用 UTF-8 with BOM，便于 Windows Excel 识别中文列名。已验证历史查询在进程内缓存 15 分钟，最多 64 个查询；自选股与已保存实验持久化到 SQLite。行情缓存不等于上游新数据。

## 数据口径与限制

- A 股通过 AKShare 的腾讯接口，港股通过 AKShare 的新浪接口；价格和成交额分别使用 CNY/HKD，成交量单位为股。可选不复权、前复权或后复权。字段与来源详见 [docs/DATA.md](docs/DATA.md) 和 [AKShare 股票数据文档](https://github.com/akfamily/akshare/blob/main/docs/data/stock/stock.md)。
- 本应用只做**股票**研究，不提供指数模块；输入框只核对位数，尚未用交易所名录验证代码身份，请勿输入指数代码。
- 区间收益率使用首尾两个**实际交易日收盘价**：`R = P_end / P_start - 1`。只有一个交易日时不显示收益率。它是简单**价格**收益率，不含现金分红、交易费用或滑点；除权除息会影响不复权价格的可比性，不应把它解释为总回报或可实现收益。
- 回测信号可以使用选定的复权价格，但模拟成交和净值始终使用同日期的**不复权开盘/收盘价**。日线无法验证订单簿成交、真实费用、停牌细节、涨跌停队列或幸存者偏差；详见 [docs/METHODOLOGY.md](docs/METHODOLOGY.md)。
- 上游请求或字段验证失败时，错误会显示在页面，详细异常写入用户数据目录的 `logs/data_errors.log`；不会用模拟数据替代。

## 可选 AI 配置

AI 草拟功能需要用户自己的 OpenAI API Key。请在启动应用的同一个 PowerShell 会话中设置 `OPENAI_API_KEY`，可选用 `OPENAI_MODEL` 指定账户可访问且支持结构化输出的模型；默认使用 `gpt-6-luna`。不要将 Key 写入仓库或聊天消息。没有 Key 时，其余研究功能照常可用。AI 报告的证据表和实验指纹由本地代码生成，AI 文本需人工复核。
