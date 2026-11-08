"""Finite batch screening controls and explicit research handoffs."""
import sqlite3
import streamlit as st
from quant_lab.screening import ScreenRecipe, METRICS, LABELS, collect_screen
from quant_lab.screen_presets import ScreenPresetStore
from quant_lab.security_identity import normalize_security
from quant_lab.storage import list_watchlist
from quant_lab.paths import user_data_dir
from quant_lab.ui_jobs import submit_task, take_result, loading_placeholder, cancel_task
from quant_lab.jobs import JobState


def queue_screen_launch(recipe, dates, codes, route):
    st.session_state["_screen_origin"] = (recipe, dates)
    st.session_state["_screen_navigation"] = (recipe, dates, codes, route)


def apply_screen_navigation():
    if st.session_state.pop("_screen_return", False):
        recipe, dates = st.session_state["_screen_origin"]
        st.session_state["_screen_preset_pending"] = recipe
        st.session_state["market_selection"] = recipe.market
        st.session_state["history_start"], st.session_state["history_end"] = dates
        st.session_state["nav_section"] = "市场数据"
        st.session_state["market_view"] = "批量选股"
        st.session_state.pop("_screen_origin", None)
    pending = st.session_state.pop("_screen_navigation", None)
    if not pending:
        return
    recipe, dates, codes, route = pending
    from quant_lab.ui_comparison import change_comparison_market
    change_comparison_market(recipe.market)
    st.session_state.pop("_course_origin", None)
    st.session_state["market_view"] = "单股行情"
    st.session_state["history_start"], st.session_state["history_end"] = dates
    st.session_state["history_adjustment_"+recipe.market] = {"": "不复权", "qfq": "前复权", "hfq": "后复权"}[recipe.adjustment]
    st.session_state["nav_section"] = "多股票比较" if route == "比较" else "研究工作台" if route == "回测" else "市场数据"
    if route == "比较":
        prefix = "us_compare" if recipe.market == "美股" else "compare"
        st.session_state[prefix+"_codes"] = ",".join(codes)
        st.session_state[prefix+"_baseline" if recipe.market == "美股" else "compare_benchmark"] = codes[0]
        st.session_state[prefix+"_start"], st.session_state[prefix+"_end"] = dates
        if recipe.market != "美股":
            st.session_state["compare_adjustment"] = recipe.adjustment
    else:
        st.session_state["us_price_symbol" if recipe.market == "美股" else "symbol_"+recipe.market] = codes[0]
        st.session_state["research_page"] = "历史回测"
        st.session_state["us_research_mode"] = "真实行情价格研究"


def render_screen_return():
    if st.session_state.get("_screen_origin"):
        st.button("返回筛选结果", key="screen_return_button", on_click=lambda: st.session_state.update({"_screen_return": True}))


def _queue_preset(recipe):
    st.session_state["_screen_preset_pending"] = recipe
    st.session_state["market_selection"] = recipe.market


def render_screening(market, dates, adjustment):
    st.subheader("批量条件选股")
    st.caption("自选股与手动候选，最多20只同市场股票；使用左侧日期范围与价格口径。加载与立即更新只由本页按钮触发。")
    prefix = "screen_"+market+"_"
    store = ScreenPresetStore()
    try:
        presets = store.load()
    except (ValueError, TypeError, OSError, KeyError) as error:
        st.error(f"读取筛选方案失败：{error}")
        presets = {}
    if presets:
        selected_preset = st.selectbox("已保存方案", tuple(presets), key="screen_preset")
        left, right = st.columns(2)
        left.button("加载方案", key="screen_load_preset", on_click=_queue_preset, args=(presets[selected_preset],))
        if right.button("删除方案", key="screen_delete_preset"):
            try:
                store.write(selected_preset, delete=True)
                st.rerun()
            except (ValueError, TypeError, OSError) as error:
                st.error(str(error))
    pending = st.session_state.pop("_screen_preset_pending", None)
    if pending:
        if pending.market != market:
            st.session_state["_screen_preset_pending"] = pending
            st.rerun()
        st.session_state[prefix+"manual"] = ",".join(pending.codes)
        st.session_state[prefix+"watched"] = []
        st.session_state[prefix+"enabled"] = [v[0] for v in pending.bounds]
        st.session_state[prefix+"sort"] = pending.sort
        st.session_state[prefix+"ascending"] = pending.ascending
        st.session_state[prefix+"basis"] = pending.adjustment
        for key, low, high in pending.bounds:
            scale = 100 if key in METRICS[:4] else 1
            if key in METRICS[-2:]:
                st.session_state[prefix+key+"_bool"] = bool(low)
            else:
                st.session_state[prefix+key+"_low"] = float(low * scale) if low is not None else -1e12
                st.session_state[prefix+key+"_high"] = float(high * scale) if high is not None else 1e12
    # Explicit screen price selection avoids changing an already-created sidebar widget.
    basis = st.selectbox("筛选价格口径", ("",) if market == "美股" else ("", "qfq", "hfq"),
                         index=("", "qfq", "hfq").index(adjustment), key=prefix+"basis", format_func=lambda v:{"":"不复权","qfq":"前复权","hfq":"后复权"}[v])
    try:
        watched = [code for m, code in list_watchlist() if m == market]
    except (ValueError, OSError, sqlite3.Error) as error:
        st.error(str(error)); return
    with st.form("screen_candidates"):
        chosen = st.multiselect("从自选股加入", watched, key=prefix+"watched")
        manual = st.text_area("手动候选代码（逗号或换行分隔）", key=prefix+"manual")
        # Form submission makes condition changes atomic with the selected query.
        enabled = st.multiselect("启用条件（全部满足）", METRICS, format_func=LABELS.get, key=prefix+"enabled")
        st.caption("首次选择条件后点击“应用条件”显示阈值；未启用条件不限制结果。百分比按百分数输入，回撤使用正的跌幅。")
        st.form_submit_button("应用条件")
        bounds = []
        for metric in enabled:
            if metric in METRICS[-2:]:
                value = st.selectbox(LABELS[metric], (True, False), format_func=lambda v:"是" if v else "否", key=prefix+metric+"_bool")
                bounds.append((metric, int(value), int(value)))
            else:
                cols = st.columns(2)
                low = cols[0].number_input(LABELS[metric]+"下限", value=-100. if metric.startswith("return") else 0., key=prefix+metric+"_low")
                high = cols[1].number_input(LABELS[metric]+"上限", value=10. if metric=="volume_ratio" else 300. if metric=="volatility20" else 100., key=prefix+metric+"_high")
                scale = 100 if metric in METRICS[:4] else 1
                bounds.append((metric, low/scale, high/scale))
        sort = st.selectbox("排序指标", METRICS, format_func=LABELS.get, key=prefix+"sort")
        ascending = st.checkbox("升序", key=prefix+"ascending")
        left, right = st.columns(2)
        run = left.form_submit_button("运行筛选", type="primary")
        force = right.form_submit_button("立即更新并筛选")
    try:
        codes = tuple(dict.fromkeys(normalize_security(market, v.strip()) for v in [*chosen, *manual.replace("，", ",").replace("\n", ",").split(",")] if v.strip()))
        recipe = ScreenRecipe(market, codes, basis, tuple(bounds), sort, ascending)
        recipe.validate()
        if not dates or dates[0] > dates[1]:
            raise ValueError("请选择有效日期范围。")
    except ValueError as error:
        st.info(str(error)); return
    title = st.text_input("筛选方案名称", key="screen_preset_title")
    if st.button("保存或覆盖方案", key="screen_save_preset"):
        try:
            store.write(title, recipe)
            st.success("方案已保存；不包含行情、结果或截止日。")
            st.rerun()
        except (ValueError, TypeError, OSError) as error:
            st.error(str(error))
    key = (str(user_data_dir()), recipe, dates)
    if run or force:
        if force:
            cancel_task("screening")
        submit_task("screening", key, collect_screen, recipe, *dates, str(user_data_dir()), force=force,
                    cooperative_io=True, job_timeout=600)
    completed = take_result("screening", key)
    if completed:
        if completed.state == JobState.SUCCEEDED:
            st.session_state["_screen_result"] = (key, completed.result)
            st.session_state.pop("_screen_error", None)
        elif completed.state == JobState.FAILED:
            st.session_state["_screen_error"] = (key, completed.error)
    failure = st.session_state.get("_screen_error")
    failed = bool(failure and failure[0] == key)
    if failed:
        st.error(failure[1]+"；旧结果只供核对，不用于本次选股。")
    saved = st.session_state.get("_screen_result")
    if "screening" in st.session_state.get("_task_tickets", {}):
        st.caption("批量取数中，可切页或取消；取消后停止后续请求，已发送请求仍可能结束。")
    if not saved or saved[0] != key:
        if "screening" in st.session_state.get("_task_tickets", {}): loading_placeholder(160)
        return
    result = saved[1]
    if "screening" in st.session_state.get("_task_tickets", {}):
        st.info("正在更新，以下为上次成功筛选结果。")
    table = result.table
    st.caption(f"统一已收市截止：{result.cutoff}；合格 {int(table.status.eq('合格').sum())}，失败 {int(table.status.ne('合格').sum())}，命中 {int(table.matched.sum())}。样本不足或零量分母指标留空。")
    display = table.rename(columns={**LABELS, "code":"代码", "name":"名称", "status":"数据状态", "matched":"命中", "condition_note":"条件说明", "error":"失败原因", "source":"来源", "received_at":"接收时间", "cached":"缓存", "quality":"质量", "actual_start":"实际开始", "actual_end":"实际截止", "currency":"币种", "adjustment":"价格口径"})
    st.dataframe(display, hide_index=True, width="stretch", column_config={LABELS[m]:st.column_config.NumberColumn(LABELS[m],format="percent") for m in METRICS[:4]})
    st.download_button("导出筛选CSV", display.to_csv(index=False).encode("utf-8-sig"), file_name="screen.csv", mime="text/csv")
    eligible = tuple(table.loc[table.matched, "code"])
    selected = st.multiselect("选择命中股票进入研究", eligible, key="screen_selected_"+result.fingerprint[:12])
    a,b,c = st.columns(3)
    for col, route, valid in ((a,"行情",len(selected)==1),(b,"回测",len(selected)==1),(c,"比较",2<=len(selected)<=10)):
        col.button("进入"+route, key="screen_go_"+route, disabled=not valid or failed or "screening" in st.session_state.get("_task_tickets", {}),
                   on_click=queue_screen_launch, args=(recipe, dates, tuple(selected), route))
    st.caption("这是当前候选池的历史日线价格筛选，不是历史成分回测，也不授予回测或行情留存资格。")
