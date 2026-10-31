"""Bounded deterministic teaching experiments, never observed market data."""

import hashlib
import json
import math

import numpy as np
import pandas as pd

from quant_lab.learning import lesson_experiment
from .models import ChartSpec, TeachingResult


TEACHING_VERSION = "academy-teaching-v1"


def sample_std(values):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all():
        return None
    return float(values.std(ddof=1))


def safe_correlation(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if len(x) != len(y) or not sample_std(x) or not sample_std(y):
        return None
    return float(np.corrcoef(x, y)[0, 1])


def sample_sharpe(values, daily_rf=0.):
    std = sample_std(values)
    if not std or not math.isfinite(daily_rf):
        return None
    return float((np.mean(values) - daily_rf) / std * math.sqrt(252))


def inverse_weights(volatility):
    values = np.asarray(volatility, dtype=float)
    if values.size == 0 or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("逆波动率权重要求有限、正的训练波动率。")
    inverse = 1 / values
    return inverse / inverse.sum()


def regression_scores(actual, predicted):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if (len(actual) != len(predicted) or not len(actual)
            or not np.isfinite(actual).all() or not np.isfinite(predicted).all()):
        return {"mae": None, "r_squared": None}
    error = actual - predicted
    total = float(np.sum((actual - actual.mean()) ** 2))
    return {"mae": float(np.mean(np.abs(error))),
            "r_squared": 1 - float(np.sum(error ** 2)) / total if total > 0 else None}


def _prices():
    return pd.Series([10., 12., 14., 13., 15., 18., 16., 17., 19., 20.])


def _result(frame, x, series, conclusion, metrics=None, percent=(), kind="line", y_percent=False,
            report=""):
    return TeachingResult(frame, ChartSpec(x, tuple(series), kind, y_percent), conclusion,
                          metrics or {}, tuple(percent), report=report)


def _variables(p):
    shares = np.arange(int(p) + 1)
    frame = pd.DataFrame({"股数": shares, "买入金额": 10 * shares, "剩余现金": 1000 - 10 * shares})
    return _result(frame, "股数", ("买入金额", "剩余现金"),
                   f"计划{int(p)}股；金额{10*p:.2f}；剩余现金{1000-10*p:.2f}。未含费用，尚未成交。",
                   {"amount": 10 * p, "cash": 1000 - 10 * p})


def _sequences(p):
    prices = [10., 12., 11., 13., 15.][:int(p)]
    frame = pd.DataFrame({"位置": range(len(prices)), "可见价格": prices})
    return _result(frame, "位置", ("可见价格",),
                   f"仅使用前{int(p)}个观察；最新已知价格{prices[-1]:.2f}，后续数据未进入窗口。",
                   {"latest": prices[-1]})


def _missing(p):
    frame = pd.DataFrame({"日期": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-03", "2024-01-04"]),
                          "收盘": [10., 11., 11., 12.]})
    if p:
        frame.loc[int(p) - 1, "收盘"] = np.nan
    missing = int(frame["收盘"].isna().sum())
    duplicate = int(frame["日期"].duplicated().sum())
    frame["额外重复日期"] = frame["日期"].duplicated()
    frame.insert(0, "行", np.arange(1, 5))
    return _result(frame, "行", ("收盘",),
                   f"缺失价格{missing}条；额外重复日期{duplicate}条。保留原表、不填充，不通过真实成交输入校验。",
                   {"missing": missing, "duplicates": duplicate})


def _shift(p):
    close = _prices()
    n = int(p)
    ma = close.rolling(n, min_periods=n).mean()
    signal = (close > ma).astype(float).where(ma.notna())
    frame = pd.DataFrame({"观察": np.arange(1, 11), "收盘": close, "均线": ma,
                          "收益率": close.pct_change(fill_method=None), "收盘信号": signal,
                          "次日可用信号": signal.shift(1)})
    return _result(frame, "观察", ("收盘", "均线"),
                   f"窗口{n}；前{n-1}个均线为空，次日信号再后移一行。未模拟实际成交。",
                   {"last_ma": float(ma.iloc[-1])}, ("收益率",))


def _log(p):
    prices = pd.Series([100., 110., 99., 108.])
    simple = prices.pct_change(fill_method=None)
    logs = np.log(prices / prices.shift(1))
    total = float(np.expm1(logs.sum()))
    annual = (1 + total) ** (p / 3) - 1
    frame = pd.DataFrame({"观察": range(4), "价格": prices, "简单收益": simple, "对数收益": logs})
    return _result(frame, "观察", ("简单收益", "对数收益"),
                   f"三期累计收益{total:.2%}；按每年{int(p)}期外推年化{annual:.2%}。极短样本外推不是预测。",
                   {"total_return": total, "annual_return": annual}, ("简单收益", "对数收益"), y_percent=True)


def _ohlcv(p):
    valid = 0 < 9 <= min(10, p) <= max(10, p) <= 12
    frame = pd.DataFrame({"观察": [1], "开盘": [10.], "最高": [12.], "最低": [9.],
                          "收盘": [p], "成交量（股）": [1000], "价格关系合格": [bool(valid)]})
    return _result(frame, "观察", ("开盘", "最高", "最低", "收盘"),
                   "教学OHLC价格关系" + ("通过；不认证身份、覆盖或来源许可。" if valid else "失败，不能继续作为成交输入。"),
                   {"valid_ohlc": int(valid)}, kind="bar")


def _basis(p):
    frame = pd.DataFrame({"拆股倍数": [p], "拆前股数": [1.], "拆前价格": [100.],
                          "拆后股数": [p], "拆后价格": [100 / p], "现金（每旧股2）": [2.],
                          "总财富": [102.]})
    return _result(frame, "拆股倍数", ("拆前价格", "拆后价格"),
                   f"拆后{p:g}股×{100/p:.2f}=100；加教学现金2，总财富102、收益2%。只看每股价格会误判为{1/p-1:.2%}。",
                   {"price_only_return": 1 / p - 1, "wealth": 102., "wealth_return": .02}, kind="bar")


LEGACY_CHARTS = (
    ChartSpec("期数", ("本金",)), ChartSpec("交易日", ("价格", "均线")),
    ChartSpec("序号", ("样本值",), "bar"), ChartSpec("交易日", ("演示价格",)),
    ChartSpec("时点", ("演示净值",)), ChartSpec("交易日", ("演示收益率",), "bar", True),
    ChartSpec("X", ("Y",), "scatter"),
    ChartSpec("参数组", ("训练期演示收益", "测试期演示收益"), percent=True),
)


def _legacy(index, p):
    # Preserve the original public eight-lesson implementation unchanged.
    frame, conclusion = lesson_experiment(index, p)
    readers = {
        0: lambda: {"simple_return": float(frame["本金"].iloc[-1] / 100 - 1),
                    "compound": float(frame["本金"].iloc[-1] / 100 - 1)},
        1: lambda: {"moving_average": float(frame["均线"].iloc[-1])},
        2: lambda: {"variance": float(frame["样本值"].var(ddof=1)), "std": sample_std(frame["样本值"])},
        3: lambda: {"volatility": sample_std(frame["演示价格"].pct_change().dropna()) * math.sqrt(252)},
        4: lambda: {"drawdown": float(frame["回撤"].min())},
        5: lambda: {"sharpe": sample_sharpe(frame["演示收益率"], p / 100)},
        6: lambda: {"correlation": safe_correlation(frame.X, frame.Y), "covariance": float(frame.X.cov(frame.Y))},
        7: lambda: {},
    }
    metrics = readers[index]()
    readings = {"bias": "本课没有单一的‘偏差值’；" + conclusion} if index == 7 else {}
    return TeachingResult(frame, LEGACY_CHARTS[index], conclusion, metrics,
                          tuple(c for c in ("回撤", "演示收益率", "训练期演示收益", "测试期演示收益") if c in frame),
                          metrics, readings)


def _dual(p):
    close = _prices()
    short, long = close.rolling(int(p)).mean(), close.rolling(5).mean()
    signal = (short > long).astype(float).where(long.notna())
    frame = pd.DataFrame({"观察": range(1, 11), "价格": close, "短均线": short, "长均线": long,
                          "五期动量": close.pct_change(5, fill_method=None), "收盘信号": signal,
                          "次日可用信号": signal.shift(1)})
    return _result(frame, "观察", ("价格", "短均线", "长均线"),
                   f"短窗口{int(p)}、长窗口5。最后收盘信号{int(signal.iloc[-1])}；不等于成交或业绩。",
                   {"last_signal": float(signal.iloc[-1])}, ("五期动量",))


def _next(p):
    close = pd.Series([10., 11., 12., 11.])
    opens = pd.Series([10., 10., p, 12.])
    signal = close > 10.5
    buy = signal & ~signal.shift(1, fill_value=False)
    execute = buy.shift(1, fill_value=False)
    frame = pd.DataFrame({"交易观察": range(1, 5), "开盘": opens, "收盘": close,
                          "收盘买入触发": buy, "开盘买入执行": execute,
                          "实际买价": opens.where(execute)})
    pnl = float(close[execute].iloc[0] - opens[execute].iloc[0])
    return _result(frame, "交易观察", ("开盘", "收盘"),
                   f"第2观察收盘触发，第3观察开盘{p:.2f}买入1股；当天收盘12，持仓盈亏{pnl:+.2f}。未含费用。",
                   {"buy_price": p, "close_pnl": pnl})


def _costs(p):
    price = 10 * (1 + p / 10000)
    shares = int(max(0, 1005 - 5) // (price * 100)) * 100
    fee = 5. if shares else 0.
    cash = 1005 - shares * price - fee
    frame = pd.DataFrame({"情景": ["当前预算"], "成交价": [price], "股数": [shares],
                          "金额": [shares * price], "佣金": [fee], "剩余现金": [cash]})
    return _result(frame, "情景", ("金额", "佣金", "剩余现金"),
                   f"模拟买入{shares}股；佣金{fee:.2f}；剩余现金{cash:.2f}。" +
                   ("预算刚好满足教学整单位约束。" if shares else "未成交：现金不足一个完整交易单位及费用。"),
                   {"shares": shares, "commission": fee, "cash": cash}, kind="bar")


def _split(p):
    r = np.array([.01, -.02, .03, .01, -.01, .02, -.03, .04, .01, -.02])
    k = int(p)
    wealth = np.cumprod(1 + r[k:])
    frame = pd.DataFrame({"收益观察": range(1, 11), "收益率": r,
                          "归属": ["训练"] * k + ["测试"] * (10-k),
                          "测试净值": [np.nan] * k + list(wealth)})
    total = float(wealth[-1] - 1)
    return _result(frame, "收益观察", ("测试净值",),
                   f"前{k}期训练、后{10-k}期测试；测试累计{total:+.2%}。仅演示切分，未训练策略。",
                   {"test_return": total}, ("收益率",))


def _walk(p):
    a = np.array([.01, .02, 0., -.02, .01, .03, -.01, .02, 0., -.02])
    b = np.array([0., .01, 0., .01, -.01, 0., .02, -.01, .01, .01])
    rows = []
    w = int(p)
    for t in range(w, len(a)):
        mean_a, mean_b = a[t-w:t].mean(), b[t-w:t].mean()
        use_a = mean_a >= mean_b
        rows.append((t + 1, t-w+1, t, mean_a, mean_b, "A" if use_a else "B", a[t] if use_a else b[t]))
    frame = pd.DataFrame(rows, columns=["测试观察", "训练起点", "训练终点", "A训练均值", "B训练均值", "选择", "测试收益"])
    frame["连续净值"] = (1 + frame["测试收益"]).cumprod()
    total = float(frame["连续净值"].iloc[-1] - 1)
    return _result(frame, "测试观察", ("连续净值",),
                   f"{len(frame)}折、每折仅用过去{w}期选择；连续测试收益{total:+.2%}。未计候选切换成本。",
                   {"test_return": total}, ("A训练均值", "B训练均值", "测试收益"))


def _resample(p):
    r = np.array([.01, -.02, .03, .01, -.01, .02, -.03, .04])
    samples = np.random.default_rng(20261031).choice(r, size=(200, len(r)), replace=True)
    net = np.prod(1 + samples - p / 10000, axis=1) - 1
    low, high = np.quantile(net, [.025, .975])
    frame = pd.DataFrame({"重采样组": range(1, 201), "净累计收益": net})
    return _result(frame, "重采样组", ("净累计收益",),
                   f"固定种子、200组；经验2.5%至97.5%分位为{low:+.2%}至{high:+.2%}。独立抽样假设，不是未来保证。",
                   {"low": float(low), "high": float(high)}, ("净累计收益",), kind="bar", y_percent=True)


def _weights(p):
    weights = inverse_weights([.01, p / 100])
    test_return = float(weights @ np.array([.01, -.01]))
    frame = pd.DataFrame({"资产": ["A", "B"], "训练日波动": [.01, p / 100],
                          "等权": [.5, .5], "逆波动权重": weights, "固定测试收益": [.01, -.01]})
    return _result(frame, "资产", ("等权", "逆波动权重"),
                   f"A/B逆波动权重{weights[0]:.2%}/{weights[1]:.2%}；固定测试期组合收益{test_return:+.3%}。未含费用和整数约束。",
                   {"weight_a": float(weights[0]), "weight_b": float(weights[1]), "test_return": test_return},
                   ("训练日波动", "等权", "逆波动权重", "固定测试收益"), kind="bar", y_percent=True)


def _rebalance(p):
    prices, quantities, cash, rate = [12., 8.], [50, 50], 100., .001
    initial = cash + sum(q * price for q, price in zip(quantities, prices))
    target = [math.floor(initial * p / 100 / 12), math.floor(initial * (1-p/100) / 8)]
    rows = [("初始", "—", 0, 0., 0., cash)]
    gross, fees = 0., 0.
    for selling in (True, False):
        for i, asset in enumerate(("A", "B")):
            if selling:
                shares = max(0, quantities[i] - target[i])
            else:
                shares = min(max(0, target[i] - quantities[i]), math.floor(cash / (prices[i] * (1+rate))))
            if not shares:
                continue
            amount, fee = shares * prices[i], shares * prices[i] * rate
            cash += amount - fee if selling else -amount - fee
            quantities[i] += -shares if selling else shares
            gross, fees = gross + amount, fees + fee
            rows.append(("卖出" if selling else "买入", asset, shares, amount, fee, cash))
    final = cash + sum(q * price for q, price in zip(quantities, prices))
    frame = pd.DataFrame(rows, columns=["动作", "资产", "股数", "成交金额", "费用", "现金余额"])
    frame.insert(0, "步骤", range(len(rows)))
    return _result(frame, "步骤", ("现金余额",),
                   f"调仓前{initial:.2f}；调仓后{final:.2f}；费用{fees:.3f}；现金{cash:.3f}；A/B={quantities[0]}/{quantities[1]}股；双边金额换手{gross/initial:.2%}。",
                   {"initial_equity": initial, "final_equity": final, "fees": fees, "cash": cash,
                    "shares_a": quantities[0], "shares_b": quantities[1], "turnover": gross / initial})


def _concentration(p):
    rho = p / 100
    hhi = .8 ** 2 + .2 ** 2
    vol = math.sqrt(max(0, .2 ** 2 * (hhi + 2 * .8 * .2 * rho)))
    frame = pd.DataFrame({"情景": ["相关为0", "当前相关", "相关为1"], "组合年化波动": [.2 * math.sqrt(hhi), vol, .2]})
    return _result(frame, "情景", ("组合年化波动",),
                   f"80/20权重HHI={hhi:.2f}、有效资产数{1/hhi:.2f}；当前相关{rho:.2f}，组合波动{vol:.2%}。",
                   {"hhi": hhi, "effective_assets": 1/hhi, "volatility": vol}, ("组合年化波动",), kind="bar", y_percent=True)


def _quality(p):
    raw = pd.DataFrame({"日期": pd.date_range("2024-01-02", periods=5), "开盘": [10.] * 5,
                        "最高": [12.] * 5, "最低": [9.] * 5, "收盘": [11.] * 5})
    if p == 1:
        raw.loc[2, "收盘"] = np.nan
    elif p == 2:
        raw.loc[2, "日期"] = raw.loc[1, "日期"]
    elif p == 3:
        raw.loc[2, "最高"] = 8.
    elif p == 4:
        raw.loc[2, "收盘"] = 0.
    prices = raw[["开盘", "最高", "最低", "收盘"]]
    complete = prices.notna().all(axis=1)
    ohlc = ((raw["最低"] <= raw[["开盘", "收盘"]].min(axis=1)) &
            (raw[["开盘", "收盘"]].max(axis=1) <= raw["最高"]))
    counts = [int(prices.isna().sum().sum()), int(raw["日期"].duplicated().sum()),
              int((prices <= 0).any(axis=1).sum()), int((complete & ~ohlc).sum())]
    frame = pd.DataFrame({"检查": ["缺失单元格", "额外重复日期", "非正价格行", "完整行OHLC矛盾"], "问题数": counts})
    return _result(frame, "检查", ("问题数",),
                   ("教学数值检查通过" if not any(counts) else "教学数值检查失败") + "；不认证真实身份、交易日覆盖或留存许可。问题可重叠计数。",
                   {"issue_count": sum(counts)}, kind="bar",
                   report="固定教学原表（自然日仅作排序标签，不代表市场日历）：\n\n" + raw.to_csv(index=False))


def _regression(p):
    train_x, train_y = np.array([0., 1., 2.]), np.array([1., 3., 5.])
    beta, alpha = np.polyfit(train_x, train_y, 1)
    test_x = np.array([3., 4., 5.])
    prediction = alpha + beta * test_x
    actual = np.array([7., 9., 11.]) + p
    scores = regression_scores(actual, prediction)
    frame = pd.DataFrame({"测试x": test_x, "实际y": actual, "训练拟合预测": prediction,
                          "训练均值预测基线": [train_y.mean()] * 3})
    return _result(frame, "测试x", ("实际y", "训练拟合预测", "训练均值预测基线"),
                   f"只在训练样本拟合：截距{alpha:.2f}、斜率{beta:.2f}；测试MAE={scores['mae']:.3f}，R²={scores['r_squared']:.3f}。不是交易收益。",
                   {**scores, "alpha": float(alpha), "beta": float(beta)})


def _compare(p):
    gross, turnover = np.array([.03, .025]), np.array([2., .5])
    drag = turnover * p / 10000
    net = gross - drag
    frame = pd.DataFrame({"实验": ["A", "B"], "毛收益": gross, "双边金额换手": turnover,
                          "成本侵蚀": drag, "净收益近似": net})
    return _result(frame, "实验", ("毛收益", "净收益近似"),
                   f"同一教学测试区间/币种/资金；A净{net[0]:+.2%}、B净{net[1]:+.2%}。成本是近似扣减，不能替代逐笔核算。",
                   {"net_a": float(net[0]), "net_b": float(net[1])}, ("毛收益", "成本侵蚀", "净收益近似"), kind="bar", y_percent=True)


def teaching_manifest(p):
    return {"version": TEACHING_VERSION, "course_id": "research_archive", "source": "固定教学样本",
            "currency": "教学同币种单位", "close": [10., 11., 12., 11., 12., 13.],
            "buy_observation": 2, "buy_open": 10., "signal_observation": 1,
            "initial_cash": 1000., "shares": 1, "commission_bps": p,
            "assumptions": "收盘信号、下一观察开盘买入；只做多、1股；无公司行动/结算/滑点；末日未卖出"}


def replay_teaching_manifest(manifest):
    """Read-only teaching-only protocol; never routes historical production archives."""
    if manifest.get("version") != TEACHING_VERSION or manifest.get("course_id") != "research_archive":
        raise ValueError("未知教学报告版本或课程。")
    expected = teaching_manifest(manifest.get("commission_bps"))
    if manifest != expected:
        raise ValueError("教学报告输入不符合固定实验合同。")
    rate = manifest["commission_bps"]
    if not isinstance(rate, (int, float)) or not math.isfinite(rate) or not 0 <= rate <= 100:
        raise ValueError("无效教学费率。")
    fee = manifest["shares"] * manifest["buy_open"] * rate / 10000
    cash = manifest["initial_cash"] - manifest["shares"] * manifest["buy_open"] - fee
    wealth = cash + manifest["shares"] * manifest["close"][-1]
    return {"fee": fee, "cash": cash, "wealth": wealth, "total_return": wealth / manifest["initial_cash"] - 1}


def _archive(p):
    manifest = teaching_manifest(p)
    encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
    original = replay_teaching_manifest(manifest)
    replayed = replay_teaching_manifest(json.loads(encoded))
    # The visible report includes the complete fixed input and numerical output.
    document = {"input": manifest, "input_sha256": fingerprint, "result": original,
                "replay_matches": original == replayed}
    prices = manifest["close"]
    frame = pd.DataFrame({"观察": range(1, 7), "收盘": prices,
                          "持股": [0] + [1] * 5,
                          "现金": [1000.] + [original["cash"]] * 5})
    frame["财富"] = frame["现金"] + frame["持股"] * frame["收盘"]
    return _result(frame, "观察", ("财富",),
                   f"买入费{original['fee']:.3f}；末日未卖出，财富{original['wealth']:.3f}，收益{original['total_return']:+.3%}；内存复算一致。仅教学报告。",
                   original, report=json.dumps(document, ensure_ascii=False, indent=2))


EXPERIMENTS = {
    "financial_variables": _variables, "price_sequences": _sequences, "frames_missing": _missing,
    "returns_shift": _shift, "log_annual": _log, "ohlcv_time": _ohlcv, "price_basis": _basis,
    "dual_trend": _dual, "next_open": _next, "execution_costs": _costs,
    "temporal_split": _split, "walk_forward": _walk, "resampling_stress": _resample,
    "portfolio_weights": _weights, "rebalance_cash": _rebalance, "concentration": _concentration,
    "hypothesis_quality": _quality, "benchmark_regression": _regression,
    "compare_experiments": _compare, "research_archive": _archive,
}


def execute(course, parameter):
    if course.legacy_index is not None:
        return _legacy(course.legacy_index, parameter)
    return EXPERIMENTS[course.course_id](parameter)
