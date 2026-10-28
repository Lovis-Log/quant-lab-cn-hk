"""UI-owned task tickets and polling; workers never receive session state."""

from uuid import uuid4

import streamlit as st

from quant_lab.jobs import JobState, TERMINAL, job_manager
from quant_lab.paths import user_data_dir


def task_scope():
    st.session_state.setdefault("_task_session_id", uuid4().hex)
    return str(user_data_dir()) + "/" + st.session_state["_task_session_id"]


def cancel_task(slot):
    ticket = st.session_state.setdefault("_task_tickets", {}).pop(slot, None)
    finished = st.session_state.setdefault("_finished_task_tickets", {}).pop(slot, None)
    ticket = ticket or finished
    if ticket:
        job_manager().cancel(ticket["id"], task_scope())


def submit_task(slot, fingerprint, function, *args, cpu=False, **kwargs):
    tickets = st.session_state.setdefault("_task_tickets", {})
    st.session_state.setdefault("_finished_task_tickets", {}).pop(slot, None)
    ticket = tickets.get(slot)
    fingerprint = repr(fingerprint)
    if ticket and ticket["fingerprint"] != fingerprint:
        cancel_task(slot)
    identifier = job_manager().submit(task_scope(), slot, fingerprint, function, *args, cpu=cpu, **kwargs)
    tickets[slot] = {"id": identifier, "fingerprint": fingerprint}
    return identifier


def take_result(slot, fingerprint):
    tickets = st.session_state.setdefault("_task_tickets", {})
    finished = st.session_state.setdefault("_finished_task_tickets", {})
    ticket = tickets.get(slot) or finished.get(slot)
    if not ticket:
        return None
    if ticket["fingerprint"] != repr(fingerprint):
        cancel_task(slot)
        return None
    job = job_manager().get(ticket["id"], task_scope())
    if job is None or job.state in TERMINAL:
        tickets.pop(slot, None)
        finished.pop(slot, None)
        return job
    return None


TASK_LABELS = {"history": "历史日线", "history_refresh": "历史日线更新", "name": "证券名称",
    "directory": "证券目录", "watch": "观察列表", "backtest": "历史回测",
    "portfolio": "组合研究", "statistics": "统计模型", "sensitivity": "参数扫描"}
TASK_LABELS.update({"backtest_raw": "回测成交价格", "portfolio_data": "组合行情"})
TASK_LABELS.update({"us_research":"美元教学研究","us_source_check":"免费美股来源核验"})


def render_background_tasks():
    tickets = st.session_state.get("_task_tickets", {})
    if not tickets:
        return

    @st.fragment(run_every=.25)
    def monitor():
        current = st.session_state.get("_task_tickets", {})
        for slot, ticket in tuple(current.items()):
            job = job_manager().get(ticket["id"], task_scope())
            if job is None or job.state in TERMINAL:
                st.session_state.setdefault("_finished_task_tickets", {})[slot] = current.pop(slot)
                st.rerun(scope="app")
            text, action = st.columns([8, 1])
            state = "排队中" if job.state == JobState.QUEUED else "进行中"
            text.caption(f"{TASK_LABELS.get(slot, slot)} · {state}")
            if action.button("取消", key=f"cancel_job_{slot}"):
                cancel_task(slot)
                st.rerun(scope="app")
    monitor()


def loading_placeholder(height=220):
    st.html(f'<div class="ql-loading-placeholder" role="status" aria-label="正在加载" style="height:{int(height)}px"></div>')
