"""Strategy signals and conservative historical backtest workspaces."""

import pandas as pd
import sqlite3
import plotly.graph_objects as go
import streamlit as st

from quant_lab.backtest import BacktestConfig, illustrative_config
from quant_lab.data import DataUnavailableError, HistoryBundle, fetch_history_cached as fetch_history
from quant_lab.processing import DataValidationError
from quant_lab.research import run_experiment, sensitivity_table
from quant_lab.strategy import STRATEGY_NAMES, StrategySpec, build_signals
from quant_lab.ui_helpers import bundle_key, percent, require_history, style_figure
from quant_lab.storage import save_experiment


def _strategy_controls(prefix: str) -> StrategySpec | None:
    kind = st.selectbox(
        "策略类型", tuple(STRATEGY_NAMES),
        format_func=lambda value: STRATEGY_NAMES[value], key=f"{prefix}_kind",
    )
    first, second = st.columns(2)
    with first:
        short = int(st.number_input(
            "短周期（交易日）", min_value=2, max_value=249,
            value=10, step=1, key=f"{prefix}_short",
        ))
    with second:
        long = int(st.number_input(
            "长周期（交易日）", min_value=3, max_value=250,
            value=30, step=1, key=f"{prefix}_long",
        ))
    try:
        return StrategySpec(kind, short, long)
    except ValueError as exc:
        st.warning(str(exc))
        return None


def render_strategy(bundle: HistoryBundle | None) -> None:
    st.subheader("交易策略实验室")
    st.caption("这里只生成收盘后才能知道的研究信号；图中标记不是实际成交。")
    if not require_history(bundle):
        return
    spec = _strategy_controls("strategy")
    if spec is None:
        return
    signals = build_signals(bundle.frame, spec)
    chart = go.Figure()
    chart.add_trace(go.Scatter(
        x=signals["date"], y=signals["close"], name="收盘价",
        line={"color": "#4F8CFF", "width": 2},
    ))
    chart.add_trace(go.Scatter(
        x=signals["date"], y=signals["ma_short"], name=f"MA {spec.short_window}",
        line={"color": "#F5B942", "width": 1.5},
    ))
    chart.add_trace(go.Scatter(
        x=signals["date"], y=signals["ma_long"], name=f"MA {spec.long_window}",
        line={"color": "#24D6A0", "width": 1.5},
    ))
    changes = signals["signal"].diff().fillna(0)
    for state, name, color, marker in (
        (1, "收盘后买入信号", "#F06A78", "triangle-up"),
        (-1, "收盘后卖出信号", "#24D6A0", "triangle-down"),
    ):
        points = signals.loc[changes == state]
        chart.add_trace(go.Scatter(
            x=points["date"], y=points["close"], mode="markers", name=name,
            marker={"color": color, "symbol": marker, "size": 10},
        ))
    st.plotly_chart(style_figure(chart, 480), width="stretch", theme=None)
    st.caption("MA 是最近 N 个交易日收盘价的算术平均；样本不足时没有均线。信号使用当日收盘数据，回测在下一交易日开盘尝试成交。")
    display = signals.tail(30).rename(columns={
        "date": "交易日", "close": "收盘价", "ma_short": "短均线",
        "ma_long": "长均线", "signal": "目标持仓信号（1=持有）",
    })
    st.dataframe(display, width="stretch", hide_index=True)


def _backtest_config(market: str) -> BacktestConfig:
    defaults = illustrative_config(market)
    with st.expander("成交与费用假设（均可调整）", expanded=False):
        st.caption("以下是研究用示例参数，不代表当前交易所、券商或个股的实际费率与成交概率。")
        cash = float(st.number_input("初始资金", min_value=1_000.0, value=1_000_000.0, step=10_000.0))
        lot = int(st.number_input(
            "买入交易单位（股，请核对标的与板块）", min_value=1,
            value=defaults.lot_size, step=1,
        ))
        commission = float(st.number_input(
            "佣金（基点）", min_value=0.0, value=defaults.commission_bps, step=1.0
        ))
        min_commission = float(st.number_input(
            "单笔最低佣金", min_value=0.0, value=defaults.min_commission, step=1.0
        ))
        buy_tax = float(st.number_input(
            "买入附加费用（基点）", min_value=0.0, value=defaults.buy_tax_bps, step=1.0
        ))
        sell_tax = float(st.number_input(
            "卖出附加费用（基点）", min_value=0.0, value=defaults.sell_tax_bps, step=1.0
        ))
        slippage = float(st.number_input(
            "单边滑点（基点）", min_value=0.0, max_value=9999.0,
            value=defaults.slippage_bps, step=1.0,
        ))
        limit = None
        if market == "A 股":
            choice = st.selectbox("简化涨跌停假设", ("10%", "5%", "20%", "30%", "不模拟"))
            limit = None if choice == "不模拟" else float(choice.rstrip("%")) / 100
    return BacktestConfig(
        market=market, initial_cash=cash, lot_size=lot,
        commission_bps=commission, min_commission=min_commission,
        buy_tax_bps=buy_tax, sell_tax_bps=sell_tax,
        slippage_bps=slippage, limit_pct=limit,
    )


def _raw_fills(bundle: HistoryBundle) -> pd.DataFrame:
    if bundle.adjustment == "":
        return bundle.frame
    start = bundle.frame["date"].iloc[0].date()
    end = bundle.frame["date"].iloc[-1].date()
    return fetch_history(bundle.market, bundle.symbol, start, end, "").frame


def render_backtest(bundle: HistoryBundle | None) -> None:
    st.subheader("历史回测系统")
    st.caption("研究模型：收盘后产生信号，下一交易日开盘尝试成交；只做多，不借钱，不执行真实交易。")
    if not require_history(bundle):
        return
    spec = _strategy_controls("backtest")
    config = _backtest_config(bundle.market)
    train_fraction = st.slider("样本内比例", 0.50, 0.85, 0.70, 0.05)
    if spec is None:
        return
    key = (bundle_key(bundle), spec, config, train_fraction)
    if st.button("运行历史回测", type="primary"):
        try:
            with st.spinner("计算交易、成本和样本外结果…"):
                raw = _raw_fills(bundle)
                result = run_experiment(raw, bundle.frame, spec, config, train_fraction)
            st.session_state["backtest_key"] = key
            st.session_state["backtest_result"] = result
            st.session_state["backtest_raw"] = raw
            st.session_state["backtest_error"] = None
        except (ValueError, DataUnavailableError, DataValidationError) as exc:
            st.session_state["backtest_key"] = key
            st.session_state["backtest_result"] = None
            st.session_state["backtest_error"] = str(exc)
    if st.session_state.get("backtest_key") != key:
        st.info("设置参数后点击“运行历史回测”。")
        return
    if st.session_state.get("backtest_error"):
        st.error(st.session_state["backtest_error"])
        return
    result = st.session_state.get("backtest_result")
    if result is None:
        return
    with st.container(border=True):
        cols = st.columns(4)
        cols[0].metric("策略累计收益", percent(result.full_stats.cumulative_return))
        cols[1].metric("年化收益估计", percent(result.full_stats.annualized_return))
        cols[2].metric("最大回撤", percent(result.full_stats.max_drawdown))
        cols[3].metric("夏普比率", "—" if result.full_stats.sharpe is None else f"{result.full_stats.sharpe:.2f}")
        st.caption(f"同成本买入并持有基准：{result.benchmark_stats.cumulative_return:+.2%}；实验指纹：`{result.audit_id}`。这些是模型结果，不是可实现收益。")
        if st.session_state.get("learning_mode", True):
            with st.expander("知识解释：收益、回撤、夏普"):
                st.write("累计收益比较末期与初期净值；最大回撤是相对先前峰值的最深跌幅；夏普比率用平均超额日收益除以样本日收益标准差，并乘以 √252。样本短或波动为零时不报告夏普。")
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=result.strategy.equity["date"],
        y=result.strategy.equity["equity"] / config.initial_cash,
        name="策略净值", line={"color": "#24D6A0", "width": 2},
    ))
    figure.add_trace(go.Scatter(
        x=result.benchmark.equity["date"],
        y=result.benchmark.equity["equity"] / config.initial_cash,
        name="同成本买入并持有", line={"color": "#4F8CFF", "width": 1.5},
    ))
    figure.add_vline(x=result.split_date, line_color="#F5B942", line_dash="dot")
    st.plotly_chart(style_figure(figure, 430), width="stretch", theme=None)
    st.caption(f"黄色虚线起为样本外区间（{result.split_date:%Y-%m-%d}）。前复权/后复权只用于生成信号；开盘成交与净值始终使用不复权价格。")
    st.dataframe(pd.DataFrame(
        {
            "区间": ["样本内", "样本外"],
            "累计收益率": [result.train_stats.cumulative_return, result.test_stats.cumulative_return],
            "最大回撤": [result.train_stats.max_drawdown, result.test_stats.max_drawdown],
            "夏普比率": [result.train_stats.sharpe, result.test_stats.sharpe],
        }
    ), width="stretch", hide_index=True)
    st.markdown("#### 交易与未成交记录")
    if result.strategy.orders.empty:
        st.info("此区间没有订单；均线可能尚未形成，或信号没有变化。")
    else:
        st.dataframe(result.strategy.orders, width="stretch", hide_index=True, height=240)
        st.download_button(
            "导出订单 CSV", result.strategy.orders.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{bundle.symbol}_{result.audit_id}_orders.csv", mime="text/csv",
        )
    st.markdown("#### 参数敏感性（仅样本内）")
    shorts = sorted({max(2, spec.short_window - 5), spec.short_window,
                     min(249, spec.short_window + 5)})
    longs = sorted({max(3, spec.long_window - 10), spec.long_window,
                    min(250, spec.long_window + 10)})
    grid = sensitivity_table(
        st.session_state["backtest_raw"], bundle.frame, spec.kind,
        config, shorts, longs, train_fraction,
    )
    st.dataframe(grid, width="stretch", hide_index=True)
    st.caption("A 股模拟 T+1、用户设定的买入单位、零成交量和简化涨跌停；港股交易单位也由用户输入。停牌、涨跌停队列、公司行动、幸存者偏差和真实费用无法由日线完整重建。")
    with st.expander("保存本次实验与研究笔记"):
        title = st.text_input("研究标题", value=f"{bundle.symbol} {STRATEGY_NAMES[spec.kind]}实验")
        hypothesis = st.text_area("研究假设", value="该均线规则在样本外仍具有可观察的风险收益特征。")
        notes = st.text_area("学习笔记", value="")
        if st.button("保存实验", key="save_experiment"):
            try:
                record_id = save_experiment(
                    title=title, hypothesis=hypothesis, notes=notes,
                    market=bundle.market, symbol=bundle.symbol,
                    raw_history=st.session_state["backtest_raw"],
                    signal_history=bundle.frame, spec=spec, config=config,
                    train_fraction=train_fraction, result=result,
                    source=bundle.source, adjustment=bundle.adjustment,
                    received_at=bundle.received_at,
                )
                st.success(f"实验 #{record_id} 已保存。可到“研究笔记”导出报告。")
            except (OSError, ValueError, sqlite3.Error) as exc:
                st.error(f"保存失败：{exc}")
