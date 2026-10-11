# Quant Lab CN/HK

面向中国 A 股与香港股票市场的个人量化研究与学习平台。当前完成 **里程碑 2：A 股真实历史日线与简单价格收益率**。代码同步在 [私有 GitHub 仓库](https://github.com/Lovis-Log/quant-lab-cn-hk)。

> 只有点击“加载真实历史日线”且成功取得数据后，页面才显示真实行情和金融指标。未加载或数据源失败时，走势图是明确标记的**模拟数据**，指标和表格保持空白。项目不提供实时行情，也不执行真实资金交易。

## 项目结构

```text
app.py                   Streamlit 入口
quant_lab/data.py        AKShare 腾讯历史日线获取
quant_lab/processing.py  数据清洗与字段验证
quant_lab/metrics.py     简单价格收益率及区间统计
quant_lab/ui.py          页面、侧栏、状态展示
quant_lab/charts.py      Plotly 真实行情与演示图表
quant_lab/demo_data.py   明确标记的模拟版式数据
quant_lab/terminal.css   自有元素的少量样式
.streamlit/config.toml   官方深色主题配置
tests/                   应用与金融计算测试
LEARNING.md              逐步学习记录
CHANGELOG.md             里程碑记录
```

`demo_data.py` 只为页面预览服务，不参与金融计算。真实数据按“获取 → 验证 → 计算 → 展示”流动。

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

## 使用真实历史行情

1. 在左侧选择 **A 股**，输入六位股票代码（默认 `600519`），选择历史日期区间。
2. 点击 **加载真实历史日线**。非交易日不会产生一条新记录；页面显示实际最新交易日。
3. 查看首尾收盘价、区间简单价格收益率、最高价、最低价、交易日数，以及收盘价/成交量图和日 K 线。
4. 在历史数据表下点击 **导出 CSV**；文件采用 UTF-8 with BOM，便于 Windows Excel 识别中文列名。

港股按钮目前不执行查询；港股支持属于后续里程碑。

## 数据口径与限制

- 数据接口：`ak.stock_zh_a_hist_tx`；原始来源：腾讯证券。本页面按**股票历史日线**使用，不提供指数研究或实时行情模块；输入框只检查六位格式，尚未核对代码是否在交易所股票名录中，请输入股票代码而非指数代码。接口可能因网络或上游变化而暂时失败，失败时页面会显示错误且不会拿演示数据计算指标。
- 复权参数固定为 `adjust=""`，即**不复权**。开高低收单位为元/股，成交量单位为股，成交额单位为元。字段定义见 [AKShare 股票数据文档](https://github.com/akfamily/akshare/blob/main/docs/data/stock/stock.md)。
- 区间收益率使用首尾两个**实际交易日收盘价**：`R = P_end / P_start - 1`。只有一个交易日时不显示收益率。它是简单**价格**收益率，不含现金分红、交易费用或滑点；除权除息会影响不复权价格的可比性，不应把它解释为总回报或可实现收益。
- 数据在页面中只保留当前会话；下载 CSV 由用户主动触发。每次点击加载会重新请求上游数据。
- 上游请求或字段验证失败时，错误会显示在页面，详细异常写入本地 `logs/data_errors.log`；该目录被 Git 忽略。

## 下一里程碑

比较不复权与复权价格对收益率的影响，继续核查数据质量；随后接入港股历史日线。
