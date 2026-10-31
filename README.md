# Quant Lab

面向 **A股、港股与美股** 的个人量化研究与学习平台。使用 Python、Streamlit 和 WebView2 构建，主要面向 Windows 桌面，也可从源码在本地浏览器运行。

本仓库为 **public**：[源码](https://github.com/Lovis-Log/quant-lab-cn-hk) · [Release](https://github.com/Lovis-Log/quant-lab-cn-hk/releases) · [问题反馈](https://github.com/Lovis-Log/quant-lab-cn-hk/issues)

**当前安装版：v2.3.0-rc.1（预发布）** — [下载Windows安装包](https://github.com/Lovis-Log/quant-lab-cn-hk/releases/download/v2.3.0-rc.1/QuantLab-CN-HK-2.3.0-rc.1-Setup.exe) · [发布说明与校验文件](https://github.com/Lovis-Log/quant-lab-cn-hk/releases/tag/v2.3.0-rc.1) · [构建与验证记录](docs/releases/v2.3.0-rc.1.md)

> 用于历史日线学习与模拟研究，不提供实时行情、投资建议或实盘下单。教学样本均明确标记；数据源失败不会替换为模拟行情。

## 可以做什么

| 工作区 | 功能 |
| --- | --- |
| 市场数据 | A/H/美股代码与名称搜索、自选股、1/3/5/10年及自定义区间、历史K线与OHLCV、覆盖与质量说明、刷新、表格全屏和CSV导出 |
| 研究工作台 | 均线与趋势策略、下一交易日开盘模拟成交、费用与滑点、样本内外分析、风险指标、统计检验和时间序列回归 |
| 多股票比较 | 同市场同币种2–10只股票的价格/净值、回撤、滚动波动、相关性比较；等权/逆波动率现金持仓组合 |
| 专业验证 | 有上限的参数扫描、滚动样本外与成本压力测试、2–6个实验比较，以及满足留存条件的报告与离线复算 |
| Quant Academy | 7个专题、共28节离线课程，包含Python金融数据基础、手算、参数实验、代码说明与思考题；先修课程支持逐层返回 |

顶部可打开 **使用手册、DeepSeek助手、研究笔记**，支持并排、调整宽度和最大化。内置10篇操作手册与85篇专业文章，阅读和搜索不调用AI。后台任务提供等待、取消和失败状态，切页不会把旧任务结果当成新查询。

## 安装与启动

### Windows安装版

1. 下载 [QuantLab-CN-HK-2.3.0-rc.1-Setup.exe](https://github.com/Lovis-Log/quant-lab-cn-hk/releases/download/v2.3.0-rc.1/QuantLab-CN-HK-2.3.0-rc.1-Setup.exe)，运行安装器。
2. 电脑需要 [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)。安装包未内置该运行时，也未作商业代码签名。
3. 从开始菜单的 **Quant Lab** 启动。首次使用按界面选择资料存放位置；随后默认进入“市场数据”，使用手册默认关闭。

本版为预发布。已完成332项核心测试，以及隔离安装版的实际WebView2关键课程操作、正常关闭和卸载检查。完整真实行情、付费AI及正式性能专项未在本次发行中重新验证，具体范围见[版本验证记录](docs/releases/v2.3.0-rc.1-validation.json)。

### 从源码运行

发行构建使用 Python 3.12。Windows PowerShell：

```powershell
git clone https://github.com/Lovis-Log/quant-lab-cn-hk.git
cd quant-lab-cn-hk
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe desktop_launcher.py
```

桌面启动器自动选择本机端口，无需手动打开浏览器。仅使用本地浏览器时可安装 `requirements.txt`，然后运行：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

访问 `http://127.0.0.1:8501`；若端口被占用，将命令和访问地址中的端口一起改为8502。真实行情与DeepSeek请求需要联网，课程和手册可以离线使用。

## 开始一次研究

1. 在左侧展开“研究参数”，选择市场、股票和日期范围，明确价格口径后点击“加载真实历史日线”。A股示例 `600519`，港股 `00700`，美股 `AAPL` 或 `BRK.B`。
2. 在市场数据页核对来源、接收时间、请求/实际覆盖、币种和质量提示，再进入研究工作台。自定义起点可早于十年，实际可用范围取决于来源与证券历史。
3. 按“策略信号 → 历史回测 → 风险与组合 → 统计分析 → 专业验证”查看结果。修改参数后明确提交；信号最早在下一交易日正常开盘模拟执行。
4. 多股票比较选择同市场、同币种的股票，核对共同覆盖再看组合。不同币种的金额不能直接加总。
5. 想补基础时进入Quant Academy。前4课从金融数据讲Python，后续逐课解释代码；点击建议先修后，用标题下的“← 返回”逐层回到原课程，并恢复专题、搜索和滑块值。

## 数据与研究边界

- 行情是**历史日线或最近收盘参考**。行情日期与成功接收时间分开显示；自动轮询不等于实时流式行情，关闭软件后不更新。
- A/H股历史主要复用AKShare接口；美股接入免费日线与证券基础资料。来源、原始/复权口径、覆盖和异常以当前查询说明为准，名称暂不可用不表示证券不存在。
- 请求十年不代表已取得完整十年。来源错误、异常价格、缺失成交日等会阻断相应研究；不能把所有缺口当停牌，也不能前值填充可成交价格。
- 回测可用复权价形成信号，成交与估值使用配对的不复权价格。当前A/H和美股价格/成本模型不保证完整公司行动、分红现金账本或结算核算，收益不能直接称为含分红总回报；严格美股现金教学模型独立保留。
- 费用、滑点、交易单位和成交条件均是明确的研究假设，不覆盖交易所全部规则。日线无法验证订单簿成交、排队或实际流动性。
- 当前真实来源的完整行情留存许可仍有限制：会话计算、CSV或摘要导出不等于完整离线实验档案。旧档案保留可读；新增完整快照/报告需满足相应校验与许可条件。

方法和模型细节见 [METHODOLOGY](docs/METHODOLOGY.md)、[数据说明](docs/DATA.md)、[美股价格研究](docs/US_PRICE_RESEARCH.md)及[来源记录](docs/data-sources/README.md)。

## 本地资料与DeepSeek

研究数据库、笔记附件、备份、日志、缓存及WebView资料保存到本机资料库，安装目录视为只读。Windows默认入口在 `%LOCALAPPDATA%\QuantLabCNHK`；自选资料库位置以设置页显示为准。开发和测试可通过 `QUANT_LAB_DATA_DIR` 指定隔离目录。SQLite升级前备份，失败回滚，不重写旧行情快照。

DeepSeek为可选功能，在左上设置中配置用户自己的API Key及模型。Key只存于当前会话或Windows凭据管理器，安全存储失败时回退会话；不保存到普通设置、数据库或导出文件。

只有明确发送、生成或总结等操作才触发付费AI请求。默认上下文使用当前课程/数据/实验的摘要，排除私人笔记、完整行情和数据库；AI返回的示例代码不会任意执行。会话显示最终回答，不保存思考过程。公开仓库保存源码和文档，运行时资料应留在本机，不要提交资料库或密钥。

## 开发与构建

```powershell
# 运行核心测试
.\.venv\Scripts\python.exe -m pytest -q

# 从干净、已提交的源码构建EXE与Windows安装包；流程会先运行测试
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1 -BuildInstaller
```

构建需要 `requirements-desktop.txt` 和 Inno Setup 7/6。`ISCC.exe`可放在PATH、标准安装位置或 `.tools\InnoSetup7`。产物位于 `dist/packages/<版本>/QuantLab/` 和 `dist/installer/`，日志与构建清单位于 `dist/release/<版本>/`；这些本地目录不进入源码提交。

课程服务位于 `quant_lab/courses/`，旧8课计算接口在 `quant_lab/learning.py` 保留兼容。行情与计算服务不导入Streamlit，界面集中在 `quant_lab/ui*.py`；后续扩展复用同一组模型和服务。开发约定见 [AGENTS.md](AGENTS.md)，模块关系见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 文档与反馈

| 文档 | 内容 |
| --- | --- |
| [学习路线](LEARNING.md) / [28课目录](docs/ACADEMY_STAGE4.md) | 从Python金融数据基础到综合研究 |
| [架构](ARCHITECTURE.md) / [方法口径](docs/METHODOLOGY.md) | 模块、金融定义和模型限制 |
| [更新记录](CHANGELOG.md) / [发行记录](docs/RELEASES.md) | 功能历史、安装包及验证回执 |
| [路线](docs/ROADMAP.md) / [开发交接](docs/HANDOFF.md) | 已确认安排、工作单和未达项 |

欢迎在 [Issues](https://github.com/Lovis-Log/quant-lab-cn-hk/issues) 反馈问题，附版本号、市场/代码、操作步骤和可复现的错误信息；请勿附带API Key或私人数据库。
