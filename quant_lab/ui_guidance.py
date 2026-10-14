"""Native learning center navigation and explicit, auditable learning actions."""

from datetime import datetime, timezone
import sqlite3
import json

import plotly.graph_objects as go
import streamlit as st

from quant_lab.guidance import GUIDES, COURSES, PATHS, TASKS, course_experiment, check_answer, task_evidence_valid
from quant_lab.knowledge import KNOWLEDGE
from quant_lab.learning import LESSONS
from quant_lab import learning_store, storage
from quant_lab.security import redact
from quant_lab.ui_updates import beijing


CENTER = "新手使用指引"
SECTIONS = ("界面指南", "入门任务", "学习路径", "课程与练习", "学习进度")


def progress():
    owner = str(storage.database_path())
    if st.session_state.get("_learning_owner") != owner:
        try:
            st.session_state["_learning_progress"] = learning_store.load_progress()
            st.session_state["_learning_owner"] = owner
        except (OSError, ValueError, sqlite3.Error):
            st.error("学习进度读取失败；请检查用户数据目录。未将缺失记录标成已完成。")
            return {}
    return st.session_state.get("_learning_progress", {})


def remember(kind, item_id, details=None, *, status="completed"):
    try:
        learning_store.save_progress(kind, item_id, details, status=status,
            secrets=(st.session_state.get("deepseek_api_key", ""),))
        cached = progress()
        safe_details = json.loads(redact(json.dumps(details or {}, ensure_ascii=False),
            (st.session_state.get("deepseek_api_key", ""),)))
        cached[(kind, item_id)] = {"status": status, "details": safe_details,
                                  "updated_at": datetime.now(timezone.utc).isoformat()}
        st.session_state["_learning_progress"] = cached
        return True
    except (OSError, ValueError, sqlite3.Error):
        st.error("学习记录保存失败；当前步骤未标为完成，请检查用户数据目录。")
        return False


def complete_task(task_id, evidence):
    if task_evidence_valid(task_id, evidence) and progress().get(("task", task_id), {}).get("status") != "completed":
        return remember("task", task_id, evidence)
    return False


def history_evidence(bundle):
    from quant_lab.ui_helpers import bundle_key
    if bundle is None or bundle.frame.empty:
        return {}
    return {"market": bundle.market, "symbol": bundle.symbol, "company_name": bundle.company_name,
            "data_fingerprint": bundle_key(bundle), "history_valid": not bool(bundle.update_error),
            "received_at": bundle.received_at.isoformat() if bundle.received_at else None,
            "data_period": [str(bundle.frame.date.iloc[0].date()), str(bundle.frame.date.iloc[-1].date())],
            "adjustment": bundle.adjustment_label, "currency": bundle.currency,
            "demonstration": any(word in bundle.source.lower() for word in ("模拟", "演示", "教学", "demo", "simulation", "teaching")),
            "source": bundle.source}


def protect_research_widgets():
    # Explicit self-assignment interrupts Streamlit widget cleanup. Values stay
    # in the current session, not in ordinary settings or the research database.
    for key in list(st.session_state):
        if key.startswith(("strategy_", "backtest_", "portfolio_", "model_", "research_", "ai_question", "cost_")) or key == "academy_lesson":
            st.session_state[key] = st.session_state[key]


def navigate(page, *, section=None, guide=None, course=None):
    if page not in GUIDES:
        raise ValueError("未知功能页面。")
    if page != CENTER:
        st.session_state["learning_return_page"] = page
    st.session_state["nav_page"] = page
    if section:
        st.session_state["center_section"] = section
    if guide:
        st.session_state["center_guide"] = guide
    if course:
        st.session_state["center_course"] = course


def open_help(page):
    st.session_state["learning_return_page"] = page
    navigate(CENTER, section="界面指南", guide=page)


def _welcome_action(action):
    if remember("onboarding", "welcome", {"action": action}, status="skipped" if action == "skip" else "completed"):
        if action == "start":
            navigate(CENTER, section="入门任务")


def render_welcome():
    if progress().get(("onboarding", "welcome"), {}).get("status") in {"completed", "skipped"}:
        return
    with st.expander("欢迎 · 从第一次量化研究开始", expanded=True):
        st.write("Quant Lab 用于 A 股与港股的历史数据、模拟研究和学习，不执行实盘交易。金融分析描述数据，量化研究还要提出可检验假设、定义规则、控制成本并检验样本外结果。")
        st.write("建议从新手使用指引的八步任务开始：选股 → 核对历史行情 → 读图与质量 → 策略 → 回测 → 解释风险 → 保存判断。四条学习路径把金融、数学、Python 与研究方法串起来。")
        st.caption("教学实验、操作指南和测验离线可用。真实日线需要网络；缓存不是实时行情，回测不保证未来收益。DeepSeek 仅在你明确发送时请求模型，学习笔记默认保密。")
        st.button("开始入门任务", key="welcome_start", on_click=_welcome_action, args=("start",))
        st.button("跳过首次引导", key="welcome_skip", on_click=_welcome_action, args=("skip",))


def render_page_help(page):
    if page == CENTER:
        return
    left, right = st.columns([4, 1])
    if st.session_state.get("learning_mode", True):
        left.caption(GUIDES[page].purpose)
    right.button("查看本页使用指南", key=f"page_help_{page}", on_click=open_help, args=(page,))


def teaching_draft(topic, *, guide=None, course=None):
    st.session_state["deepseek_prompt"] = f"请辅导我理解{KNOWLEDGE[topic].title}，先问一个小问题，让我尝试后再解释；不要直接给出当前测验答案。"
    st.session_state["ai_knowledge"] = {"topic": KNOWLEDGE[topic].title, "origin_page": CENTER,
        "learning_id": course or guide}
    st.session_state["deepseek_answer_mode"] = "教学辅导模式"
    st.session_state["ai_open"] = True


def _guide():
    page = st.selectbox("选择页面指南", tuple(GUIDES), key="center_guide")
    guide = GUIDES[page]
    st.markdown(f"### {page} · 使用指南")
    st.write(guide.purpose)
    st.dataframe([{"控件与图表": label, "用途": meaning} for label, meaning in guide.controls], hide_index=True, width="stretch")
    st.markdown("#### 操作步骤")
    for i, step in enumerate(guide.steps, 1):
        st.write(f"{i}. {step}")
    st.markdown("#### 可复现案例")
    st.write(guide.example)
    with st.expander("常见错误与解决办法", expanded=page == "统计与机器学习"):
        for error in guide.errors:
            st.write("• " + error)
    topic = st.selectbox("相关术语", guide.topics, format_func=lambda t: KNOWLEDGE[t].title,
                         key=f"guide_topic_{page}")
    from quant_lab.ui_knowledge import render_knowledge
    render_knowledge(topic, key="guide", expanded=True)
    if topic in COURSES:
        st.button("进入相关交互课程", key="guide_to_course", on_click=navigate,
                  args=(CENTER,), kwargs={"section": "课程与练习", "course": topic})
    st.button("打开对应功能页面", key="guide_to_page", on_click=navigate, args=(page,))
    st.button("下一步功能：" + guide.next_page, key="guide_next", on_click=navigate, args=(guide.next_page,))
    if st.button("标记本指南已阅读", key="guide_complete"):
        if remember("guide", page, {"confirmed_read": True}):
            st.success("已记录你的阅读确认。")
    st.session_state["active_learning_context"] = {"guide": page, "topic": KNOWLEDGE[topic].title,
        "definition": KNOWLEDGE[topic].definition, "status": "软件操作指南，不是股票行情"}


def _tasks():
    records = progress()
    finished = sum(records.get(("task", item), {}).get("status") == "completed" for item in TASKS)
    st.progress(finished / len(TASKS), text=f"入门任务 {finished}/{len(TASKS)}")
    st.caption("自动项来自成功操作的证据；确认项记录你的学习判断。历史完成记录不表示当前股票查询有效。")
    for task_id, task in TASKS.items():
        record = records.get(("task", task_id))
        with st.expander(task.title + (" · 已完成" if record else " · 待完成"), expanded=not record):
            st.write("目标：" + task.goal)
            st.caption("先修建议：" + ("；".join(TASKS[p].title for p in task.prerequisites) or "无"))
            for i, step in enumerate(task.steps, 1):
                st.write(f"{i}. {step}")
            st.write("完成条件：" + task.condition)
            st.caption("常见错误：" + task.error)
            st.button("去操作 · " + task.page, key=f"task_go_{task_id}", on_click=navigate, args=(task.page,))
            st.button("先学 · " + KNOWLEDGE[task.course].title, key=f"task_course_{task_id}",
                on_click=navigate, args=(CENTER,), kwargs={"section": "课程与练习", "course": task.course})
            if record:
                st.caption("完成时间：" + beijing(record["updated_at"]))
                with st.expander("查看完成证据（不含私人判断正文）"):
                    st.json(record["details"])
            elif not task.automatic:
                prerequisites_ready = all(records.get(("task", p), {}).get("status") == "completed" for p in task.prerequisites)
                if st.button("我已核对并理解", key=f"task_confirm_{task_id}", disabled=not prerequisites_ready):
                    if complete_task(task_id, {"confirmed": True, "method": "用户明确确认"}):
                        st.rerun()
            else:
                st.caption("完成相关操作后自动记录；这里不能手动伪造完成。")
    st.session_state["active_learning_context"] = {"topic": "第一次量化研究", "status": "操作任务指引，不自动发送学习进度"}


def _paths():
    path = st.selectbox("学习路径", tuple(PATHS), key="center_path")
    st.caption("按顺序学习；同一知识可跨路径复用。计划中节点仅列出先修和下一步，不能标成已完成课程。")
    previous = "无"
    for i, (title, course_id) in enumerate(PATHS[path], 1):
        with st.container(border=True):
            st.markdown(f"**{i}. {title}**")
            st.caption("路径先修建议：" + previous)
            if course_id:
                course = COURSES[course_id]
                st.caption("交叉先修：" + ("、".join(KNOWLEDGE[p].title for p in course.prerequisites) or "无"))
                done = progress().get(("course", course_id), {}).get("status") == "completed"
                st.caption("课程状态：" + ("已完成实验与测验" if done else "已有交互课程，可开始"))
                st.button("学习这节课", key=f"path_course_{i}", on_click=navigate,
                    args=(CENTER,), kwargs={"section": "课程与练习", "course": course_id})
            else:
                st.caption("计划中 · 本版没有完整可完成课程。可先查页面指南与知识解释。")
            previous = title
    st.button("查看统计与机器学习的完整操作教程", key="path_statistics", on_click=navigate,
              args=(CENTER,), kwargs={"section": "界面指南", "guide": "统计与机器学习"})


def _course():
    course_id = st.selectbox("选择交互课程", tuple(COURSES), key="center_course", format_func=lambda c: KNOWLEDGE[c].title)
    course = COURSES[course_id]
    item, lesson = KNOWLEDGE[course.topic], LESSONS[course.lesson]
    st.subheader(item.title + " · 七层学习")
    st.caption("先修建议：" + ("、".join(KNOWLEDGE[p].title for p in course.prerequisites) or "无") + "；未学先修也可预览，不伪装已掌握。")
    for number, heading, text in ((1, "概念定义", item.definition), (2, "直观解释", lesson.intuition)):
        st.markdown(f"#### {number} · {heading}")
        st.write(text)
    st.markdown("#### 3 · 数学原理与假设")
    st.latex(item.formula)
    st.write(item.symbols)
    st.write("手算例子：" + item.example)
    st.markdown("#### 4 · 刻画对象")
    st.write(item.feature)
    st.markdown("#### 5 · 实际意义")
    st.write(item.importance)
    st.button("到研究页面检验 · " + course.page, key="course_research", on_click=navigate, args=(course.page,))
    st.markdown("#### 6 · 交互实验")
    st.caption("固定教学数据，不是行情。先预测调参影响，再拖动滑块验证；代码仅供阅读。")
    if lesson.step < 1:
        bounds = (float(lesson.minimum), float(lesson.maximum), float(lesson.default), float(lesson.step))
    else:
        bounds = (int(lesson.minimum), int(lesson.maximum), int(lesson.default), int(lesson.step))
    resume = progress().get(("onboarding", "resume"), {}).get("details", {})
    if resume.get("course_id") == course_id and lesson.minimum <= resume.get("parameter", lesson.default) <= lesson.maximum:
        default = float(resume["parameter"]) if lesson.step < 1 else int(resume["parameter"])
        bounds = (bounds[0], bounds[1], default, bounds[3])
    parameter = st.slider(lesson.parameter, *bounds, key=f"center_parameter_{course_id}")
    position = {"course_id": course_id, "section": "课程与练习", "parameter": parameter}
    if position != resume:
        remember("onboarding", "resume", position, status="in_progress")
    frame, conclusion = course_experiment(course_id, parameter)
    columns = {
        "simple_return": ("本金",), "moving_average": ("价格", "均线"), "variance": ("样本值",),
        "volatility": ("演示价格",), "drawdown": ("回撤",), "sharpe": ("演示收益率",),
        "correlation": ("Y",), "bias": ("训练期演示收益", "测试期演示收益"),
    }[course_id]
    figure = go.Figure()
    for column in columns:
        figure.add_scatter(x=frame.iloc[:, 0], y=frame[column], name=column, mode="lines+markers")
    figure.update_layout(title="教学实验 · " + item.title, xaxis_title=frame.columns[0],
        yaxis_title="收益率 / 回撤（%）" if course_id in {"drawdown", "sharpe", "bias"} else "教学样本数值",
        height=300, margin={"l": 15, "r": 15, "t": 45, "b": 25})
    if course_id in {"drawdown", "sharpe", "bias"}:
        figure.update_yaxes(tickformat=".0%")
    st.plotly_chart(figure, width="stretch")
    st.dataframe(frame, hide_index=True, width="stretch")
    st.info(conclusion)
    st.code(lesson.code, language="python")
    if st.button("保存交互实验记录", key="course_experiment_save"):
        if remember("experiment", course_id, {"parameter": parameter, "conclusion": conclusion, "source": "固定教学样本"}):
            if any(row["course_id"] == course_id and row["correct"] for row in learning_store.quiz_attempts()):
                remember("course", course_id, {"method": "实验记录 + 本地测验通过"})
            st.success("教学实验已保存，可重启后继续练习。")
    st.markdown("#### 7 · 局限与练习")
    st.write(item.limitation)
    st.write(lesson.question)
    with st.form(f"course_quiz_{course_id}"):
        st.write(course.quiz)
        answer = st.number_input("你的数值答案", value=0.0, step=0.01, key=f"center_answer_{course_id}")
        submitted = st.form_submit_button("提交课程测验")
    if submitted:
        correct = check_answer(course_id, answer)
        try:
            learning_store.save_quiz_attempt(course_id, answer, correct)
            if correct:
                st.success("答对了。" + course.explanation)
                if progress().get(("experiment", course_id)):
                    remember("course", course_id, {"method": "实验记录 + 本地测验通过"})
                else:
                    st.info("再保存一份交互实验记录后，这节课程才标为完成。")
            else:
                st.warning("还需再想一想。先检查基数、单位、分母和符号，再重复练习。")
                with st.expander("提交后查看解题思路"):
                    st.write(course.explanation)
        except (ValueError, OSError, sqlite3.Error):
            st.error("测验保存失败，未记录为完成。")
    st.button("使用 DeepSeek 辅导这节课", key="course_ai", on_click=teaching_draft,
              args=(course.topic,), kwargs={"course": course_id})
    st.caption("这只准备问题；在原有 DeepSeek 侧栏核对摘要并明确发送，才会请求模型。")
    st.session_state["active_learning_context"] = {"course_id": course_id, "topic": item.title,
        "definition": item.definition, "formula": item.formula, "parameter": parameter,
        "experiment_conclusion": conclusion, "status": "固定教学实验，不是股票行情；不含测验答案"}


def _progress_page():
    records = progress()
    st.caption("课程完成要求保存交互实验并通过本地测验；任务完成保留来源证据。学习笔记和研究档案独立保存。")
    categories = {"task":"入门任务", "guide":"页面指南", "course":"课程", "experiment":"教学实验", "goal":"学习目标", "onboarding":"引导"}
    titles = {item: task.title for item, task in TASKS.items()}
    titles.update({item: KNOWLEDGE[item].title for item in COURSES})
    titles.update({"welcome":"首次欢迎", "resume":"继续学习位置", "current":"当前目标"})
    statuses = {"completed":"已完成", "in_progress":"学习中", "skipped":"已跳过"}
    st.dataframe([{"类别": categories[kind], "项目": titles.get(item, item),
        "状态": statuses[row["status"]], "时间": beijing(row["updated_at"])}
        for (kind, item), row in records.items()], width="stretch", hide_index=True)
    attempts = learning_store.quiz_attempts()
    st.markdown("#### 测验记录")
    st.dataframe([{"课程": KNOWLEDGE.get(row["course_id"], KNOWLEDGE["simple_return"]).title,
        "提交答案": row["answer"], "结果": "正确" if row["correct"] else "待复习",
        "时间": beijing(row["created_at"])} for row in attempts], width="stretch", hide_index=True)
    current = records.get(("goal", "current"), {}).get("details", {}).get("text", "完成第一次有证据的量化研究")
    with st.form("learning_goal_form"):
        goal = st.text_input("当前学习目标", value=current, max_chars=500)
        if st.form_submit_button("保存学习目标"):
            if goal.strip() and remember("goal", "current", {"text": goal.strip()}, status="in_progress"):
                st.success("学习目标已保存；不会自动发送给 AI。")
    with st.form("center_note_form"):
        title = st.text_input("学习笔记标题", max_chars=100)
        content = st.text_area("学习笔记内容", max_chars=5000)
        if st.form_submit_button("保存学习笔记"):
            storage.save_learning_note(title, content, secrets=(st.session_state.get("deepseek_api_key", ""),))
            st.success("学习笔记已保存。")
    for note in storage.list_learning_notes()[:20]:
        with st.expander(f"#{note['id']} {note['title']}"):
            st.write(note["content"])
    st.button("重新启动首次引导", key="welcome_restart", on_click=remember,
              args=("onboarding", "welcome", {"action": "restart"}), kwargs={"status": "in_progress"})
    with st.form("reset_learning_form"):
        confirmed = st.checkbox("确认只重置学习进度与测验；保留研究、行情、笔记和密钥")
        if st.form_submit_button("重置学习进度"):
            if not confirmed:
                st.warning("请先明确确认重置范围。")
            else:
                learning_store.reset_progress()
                st.session_state.pop("_learning_owner", None)
                st.success("学习进度与测验已重置，研究数据和笔记保留。")
                st.rerun()


def render_learning_center():
    st.subheader("新手使用指引 · Learning Center")
    resume = progress().get(("onboarding", "resume"), {}).get("details", {})
    if resume.get("course_id") in COURSES:
        st.session_state.setdefault("center_course", resume["course_id"])
        st.session_state.setdefault("center_section", "课程与练习")
    target = st.session_state.get("learning_return_page", "市场数据")
    st.button("返回研究任务 · " + target, key="center_return", on_click=navigate, args=(target,))
    section = st.radio("学习中心分区", SECTIONS, horizontal=True, key="center_section")
    try:
        {"界面指南": _guide, "入门任务": _tasks, "学习路径": _paths,
         "课程与练习": _course, "学习进度": _progress_page}[section]()
    except (ValueError, OSError, sqlite3.Error):
        st.error("学习中心记录读取或保存失败；请检查用户数据目录。没有将失败步骤标为已完成。")
