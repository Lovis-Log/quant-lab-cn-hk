# Quant Lab CN/HK

面向中国 A 股与香港股票市场的个人量化研究与学习平台。当前提供数据、策略、回测、风险组合、统计机器学习与可选 AI 研究助手六个工作区。代码同步在 [私有 GitHub 仓库](https://github.com/Lovis-Log/quant-lab-cn-hk)。

> 这是学习与模拟研究平台，不提供实时行情、投资建议或真实资金交易。未取得真实行情时，市场页只显示明确标记的模拟版式图，金融指标和表格保持空白。

## 项目结构

```text
app.py                   Streamlit 入口
quant_lab/data.py        AKShare A 股/港股历史日线获取
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
LEARNING.md              逐步学习记录
CHANGELOG.md             里程碑记录
```

`demo_data.py` 只为页面预览服务，不参与金融计算。真实数据按“获取 → 验证 → 策略/统计计算 → 展示”流动。

## Windows 启动

在项目目录下的 PowerShell 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

浏览器通常打开 `http://localhost:8501`。不必激活虚拟环境，直接使用其 Python 可避免 PowerShell 执行策略问题。查询真实行情需要联网。

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

CSV 使用 UTF-8 with BOM，便于 Windows Excel 识别中文列名。数据仅保留在当前 Streamlit 会话；每次点击加载会重新请求上游。

## 数据口径与限制

- A 股通过 AKShare 的腾讯接口，港股通过 AKShare 的新浪接口；价格和成交额分别使用 CNY/HKD，成交量单位为股。可选不复权、前复权或后复权。字段与来源详见 [docs/DATA.md](docs/DATA.md) 和 [AKShare 股票数据文档](https://github.com/akfamily/akshare/blob/main/docs/data/stock/stock.md)。
- 本应用只做**股票**研究，不提供指数模块；输入框只核对位数，尚未用交易所名录验证代码身份，请勿输入指数代码。
- 区间收益率使用首尾两个**实际交易日收盘价**：`R = P_end / P_start - 1`。只有一个交易日时不显示收益率。它是简单**价格**收益率，不含现金分红、交易费用或滑点；除权除息会影响不复权价格的可比性，不应把它解释为总回报或可实现收益。
- 回测信号可以使用选定的复权价格，但模拟成交和净值始终使用同日期的**不复权开盘/收盘价**。日线无法验证订单簿成交、真实费用、停牌细节、涨跌停队列或幸存者偏差；详见 [docs/METHODOLOGY.md](docs/METHODOLOGY.md)。
- 上游请求或字段验证失败时，错误会显示在页面，详细异常写入本地 `logs/data_errors.log`；该目录被 Git 忽略。

## 可选 AI 配置

AI 草拟功能需要用户自己的 OpenAI API Key。请在启动应用的同一个 PowerShell 会话中设置 `OPENAI_API_KEY`，可选用 `OPENAI_MODEL` 指定账户可访问且支持结构化输出的模型；默认使用 `gpt-6-luna`。不要将 Key 写入仓库或聊天消息。没有 Key 时，其余研究功能照常可用。AI 报告的证据表和实验指纹由本地代码生成，AI 文本需人工复核。
