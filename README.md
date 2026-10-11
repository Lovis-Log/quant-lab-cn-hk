# Quant Lab CN/HK

面向中国 A 股与香港股票市场的个人量化研究与学习平台。当前完成 **里程碑 1：Streamlit 深色终端界面骨架**。

> 当前没有接入任何真实行情。走势图和活动量是由固定随机种子生成的无单位**模拟数据**，只用于预览版式；指标卡和历史数据表均为空。项目不执行真实资金交易。

## 项目结构

```text
app.py                   Streamlit 入口
quant_lab/ui.py          页面、侧栏、状态展示
quant_lab/charts.py      Plotly 图表
quant_lab/demo_data.py   明确标记的模拟版式数据
quant_lab/terminal.css   自有元素的少量样式
.streamlit/config.toml   官方深色主题配置
tests/                   应用冒烟测试
LEARNING.md              逐步学习记录
CHANGELOG.md             里程碑记录
```

后续真实数据模块将分成获取、清洗验证和金融指标计算三个独立层，再接入 UI。当前 `demo_data.py` 只为页面预览服务，不能用于金融分析。

## Windows 启动

在项目目录下的 PowerShell 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

浏览器通常打开 `http://localhost:8501`。不必激活虚拟环境，直接使用其 Python 可避免 PowerShell 执行策略问题。

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 当前页面

- 左侧导航、市场和股票代码选择、日期范围输入，均为界面演示。
- 顶部标的状态、四个待接入指标卡。
- 可交互的模拟走势图与活动量预览，以及 K 线预留区。
- 空历史数据表、数据状态和研究提示。

## 下一里程碑

接入并验证一只 A 股的真实历史日线行情，明确接口、字段单位和复权方式；随后计算区间简单价格收益率，并用手算样本验证。港股与 CSV 导出按路线逐步加入。
