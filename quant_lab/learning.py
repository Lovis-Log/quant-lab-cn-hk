"""Eight small, hand-checkable finance lessons independent of the UI."""

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Lesson:
    title: str
    intuition: str
    formula: str
    example: str
    code: str
    question: str
    parameter: str
    minimum: float
    maximum: float
    default: float
    step: float


LESSONS = (
    Lesson("简单收益率与复利", "收益率比较期末与期初；复利让每一期收益进入下一期本金。",
           r"R=P_1/P_0-1,\quad P_n=P_0(1+r)^n",
           "10 元涨到 11 元，简单价格收益率为 10%。100 元连续两期各涨 10%，结果为 121 元，而不是 120 元。",
           "r = end / start - 1\nfuture = principal * (1 + r) ** years",
           "若先涨 10% 再跌 10%，本金会回到原值吗？", "每期收益率（%）", -20, 30, 10, 1),
    Lesson("移动平均线", "把最近 N 个收盘价平均，短期起伏会被平滑；最后一天收盘后才知道当天均线。",
           r"MA_N(t)=\frac{1}{N}\sum_{i=0}^{N-1}P_{t-i}",
           "价格 10、12、14 元的 3 日均线是 (10+12+14)/3=12 元。",
           "ma = close.rolling(window=n, min_periods=n).mean()",
           "若窗口加长，均线会更平滑，还是更快响应新价格？", "窗口（交易日）", 2, 10, 3, 1),
    Lesson("方差与标准差", "先看每个数离均值有多远；方差平方后求平均，标准差再开方，恢复原单位。",
           r"s^2=\frac{\sum_{i=1}^{n}(x_i-\bar x)^2}{n-1},\quad s=\sqrt{s^2}",
           "样本 1、2、3 的均值为 2，样本方差为 (1+0+1)/2=1，标准差为 1。",
           "variance = returns.var(ddof=1)\nstd = returns.std(ddof=1)",
           "为什么样本方差分母是 n−1？只有一个观测时能估计样本标准差吗？", "第三个样本值", 1, 8, 3, 1),
    Lesson("波动率", "波动率用收益率的离散程度描述历史价格起伏，不告诉你涨跌方向。",
           r"\sigma_{annual}\approx s_{daily}\sqrt{252}",
           "若日收益率标准差为 1%，按 252 个交易日近似年化，约为 15.87%。",
           "daily = prices.pct_change().dropna()\nvol = daily.std(ddof=1) * (252 ** 0.5)",
           "年化波动率高，是否意味着下一年一定亏损？", "价格波动幅度", 0, 8, 3, 1),
    Lesson("最大回撤", "从之前最高净值向下看，找最深的一次跌幅；它不等于最终收益。",
           r"D_t=V_t/\max_{u\le t}V_u-1,\quad MDD=\min_t D_t",
           "净值 100、120、90、100：从 120 到 90 跌 25%，最大回撤是 −25%，最终收益为 0%。",
           "drawdown = equity / equity.cummax() - 1\nmdd = drawdown.min()",
           "如果后来净值升到 130，此前那次最大回撤会消失吗？", "低点净值", 60, 120, 90, 5),
    Lesson("夏普比率", "比较平均超额收益与波动；样本太短或波动为零时，数值没有稳定解释。",
           r"Sharpe=\frac{\bar r-r_f^{daily}}{s_r}\sqrt{252}",
           "两天收益为 1%、3%，日无风险收益近似 0，则均值 2%、样本标准差约 1.414%。这是极小样本，仅作公式练习。",
           "excess = returns.mean() - daily_rf\nsharpe = excess / returns.std(ddof=1) * (252 ** 0.5)",
           "如果所有日收益完全相同，为什么不能直接报一个无穷大的夏普比率？", "日无风险收益（%）", 0, 2, 0, 0.1),
    Lesson("相关系数", "相关系数衡量两组变化同向或反向的程度；相关不证明一个变量导致另一个变化。",
           r"\rho_{X,Y}=\frac{cov(X,Y)}{s_Xs_Y}",
           "X=[1,2,3]，Y=[2,4,6] 时相关系数为 1；Y=[6,4,2] 时为 −1。",
           "correlation = series_x.corr(series_y)",
           "两只股票历史相关系数接近 0，未来是否一定能分散风险？", "第二组中间值", 0, 8, 4, 1),
    Lesson("回测偏差与过拟合", "反复调参数，直到旧数据看起来最好，会把偶然噪声当成规律。先定规则，再看未参与选择的新区间。",
           r"选择参数只用训练集；测试集在最终评估前不参与选择",
           "若尝试 100 组参数并只汇报收益最高的一组，这个最高值往往含运气成分；应另留样本外区间。",
           "train = data.iloc[:split]\ntest = data.iloc[split:]  # 不参与选参",
           "若看过样本外结果后继续调参，该区间还是独立样本外吗？", "尝试的参数组数", 1, 100, 10, 1),
)


def lesson_experiment(index: int, parameter: float) -> tuple[pd.DataFrame, str]:
    """Deterministic examples only; never interpreted as observed prices."""
    if not 0 <= index < len(LESSONS):
        raise ValueError("未知课程。")
    if index == 0:
        years = np.arange(0, 6)
        values = 100 * (1 + parameter / 100) ** years
        return pd.DataFrame({"期数": years, "本金": values}), f"第 5 期：{values[-1]:.2f}；总收益率：{values[-1]/100-1:+.2%}"
    if index == 1:
        prices = pd.Series([10, 12, 14, 13, 15, 18, 16, 17, 19, 20], dtype=float)
        n = int(parameter)
        frame = pd.DataFrame({"交易日": range(1, 11), "价格": prices,
                              "均线": prices.rolling(n, min_periods=n).mean()})
        return frame, f"最后一天 {n} 日均线：{frame['均线'].iloc[-1]:.2f}"
    if index == 2:
        values = pd.Series([1.0, 2.0, float(parameter)])
        return pd.DataFrame({"序号": [1, 2, 3], "样本值": values}), f"均值 {values.mean():.3f}；样本方差 {values.var(ddof=1):.3f}；标准差 {values.std(ddof=1):.3f}"
    if index == 3:
        prices = pd.Series([100, 101, 99, 102, 100 + parameter, 104], dtype=float)
        returns = prices.pct_change().dropna()
        return pd.DataFrame({"交易日": range(1, 7), "演示价格": prices}), f"日收益率样本标准差 {returns.std(ddof=1):.2%}；年化近似 {returns.std(ddof=1)*math.sqrt(252):.2%}"
    if index == 4:
        equity = pd.Series([100, 120, float(parameter), 100, 130], dtype=float)
        dd = equity / equity.cummax() - 1
        return pd.DataFrame({"时点": range(1, 6), "演示净值": equity, "回撤": dd}), f"最大回撤 {dd.min():.2%}；末期收益 {equity.iloc[-1]/equity.iloc[0]-1:+.2%}"
    if index == 5:
        returns = pd.Series([0.01, 0.03, -0.01, 0.02])
        std = returns.std(ddof=1)
        sharpe = (returns.mean() - parameter / 100) / std * math.sqrt(252)
        return pd.DataFrame({"交易日": range(1, 5), "演示收益率": returns}), f"样本均值 {returns.mean():.2%}；样本标准差 {std:.2%}；年化夏普示例 {sharpe:.2f}（样本极短）"
    if index == 6:
        x = pd.Series([1.0, 2.0, 3.0, 4.0])
        y = pd.Series([2.0, float(parameter), 6.0, 8.0])
        return pd.DataFrame({"X": x, "Y": y}), f"皮尔逊相关系数：{x.corr(y):.3f}"
    attempts = int(parameter)
    x = np.arange(1, attempts + 1)
    # A fixed deterministic noise illustration, not a probability estimate.
    training = 0.02 + 0.04 * np.sin(x * 1.9) + 0.0004 * x
    testing = 0.01 + 0.03 * np.cos(x * 2.3)
    best = int(np.argmax(training))
    return pd.DataFrame({"参数组": x, "训练期演示收益": training, "测试期演示收益": testing}), f"训练期最佳为第 {best+1} 组：{training[best]:+.2%}；其测试期：{testing[best]:+.2%}。这是固定模拟值，不能推断普遍胜率。"
