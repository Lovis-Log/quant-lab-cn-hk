"""Interactive Academy page with deliberate separation from market observations."""

import streamlit as st

from quant_lab.learning import LESSONS, lesson_experiment
from quant_lab.knowledge import LESSON_TOPICS
from quant_lab.ui_knowledge import ARTICLE_BY_TOPIC, render_knowledge
from quant_lab.charts import teaching_chart
from quant_lab.ui_helpers import reset_main_scroll
import math


@st.fragment
def render_academy() -> None:
    with st.container(key="academy_workspace"):
        catalog, reading = st.columns([1, 3.35], gap="large")
        with catalog, st.container(key="academy_catalog"):
            st.subheader("Quant Academy")
            st.caption("金融数学实验室")
            query = st.text_input("搜索课程", key="academy_search", placeholder="输入课程名称或关键词")
            groups = {"全部课程": tuple(range(8)), "收益与数据": (0,), "风险与统计": (2, 3, 4, 5, 6),
                      "策略与成交": (1,), "研究验证": (7,)}
            group = st.radio("课程专题", tuple(groups), key="academy_group", label_visibility="collapsed")
            available = [i for i in groups[group] if not query.strip() or query.strip().casefold() in
                         (LESSONS[i].title + LESSONS[i].intuition + LESSONS[i].question).casefold()]
            if not available:
                st.info("没有匹配的课程，请换一个关键词。")
                st.session_state["active_learning_context"] = None
                st.session_state["_current_ai_context"] = {"page": "Quant Academy", "data_status": "课程检索，无当前实验。"}
                return
            if st.session_state.get("academy_lesson", 0) not in available:
                st.session_state["academy_lesson"] = available[0]
            choice = st.selectbox("选择课程", available, key="academy_lesson", format_func=lambda i: LESSONS[i].title)
            st.caption(f"{len(LESSONS)} 节可用课程 · 固定教学样本")
        with reading, st.container(key="academy_reading"):
            st.caption(f"{group} / {LESSONS[choice].title}")
            st.title(LESSONS[choice].title)
            st.caption("固定教学样本 · 可离线运行")
            st.write(LESSONS[choice].intuition)
            st.latex(LESSONS[choice].formula)
            st.write(LESSONS[choice].example)
            _render_experiment(choice)
            reset_main_scroll(choice, key="lesson")


def _choose_lesson(index):
    st.session_state["academy_search"] = ""
    st.session_state["academy_group"] = "全部课程"
    st.session_state["academy_lesson"] = index


def _render_experiment(choice):
    lesson = LESSONS[choice]
    chart_area = st.empty()
    if lesson.step < 1:
        bounds = (float(lesson.minimum), float(lesson.maximum),
                  float(lesson.default), float(lesson.step))
    else:
        bounds = (int(lesson.minimum), int(lesson.maximum),
                  int(lesson.default), int(lesson.step))
    with st.container(key="academy_experiment"):
        controls, table = st.columns([1, 1.2], gap="medium")
        with controls:
            st.markdown("#### 参数实验")
            parameter_key = f"academy_parameter_{choice}"
            if parameter_key in st.session_state:
                value = st.slider(lesson.parameter, min_value=bounds[0], max_value=bounds[1], step=bounds[3], key=parameter_key)
            else:
                value = st.slider(lesson.parameter, *bounds, key=parameter_key)
            frame, conclusion = lesson_experiment(choice, value)
            st.info(conclusion)
        with table:
            st.markdown("#### 教学数据与结果")
            percent_columns = {name: st.column_config.NumberColumn(name, format="percent")
                for name in ("回撤", "演示收益率", "训练期演示收益", "测试期演示收益") if name in frame}
            st.dataframe(frame, width="stretch", hide_index=True, height=min(280, 38 + 35 * len(frame)),
                         column_config=percent_columns)
    with chart_area.container():
        st.plotly_chart(teaching_chart(choice, frame), width="stretch", theme=None,
                        key=f"academy_chart_{choice}", config={"displaylogo": False, "scrollZoom": False})
    st.session_state["active_learning_context"] = {"course_id": LESSON_TOPICS[choice][0],
        "topic": lesson.title, "parameter": value, "experiment_conclusion": conclusion,
        "status": "固定教学样本，不是股票行情"}
    # A fragment rerun does not re-enter render_app: refresh the AI whitelist
    # explicitly so a follow-up never receives the previous lesson's numbers.
    st.session_state["_current_ai_context"] = {
        "page": "Quant Academy", "lesson": choice,
        "data_status": "离线教学实验，不是股票行情。",
        "learning_context": st.session_state["active_learning_context"],
    }
    with st.expander("Python 实现 · 逐行解释"):
        st.code(lesson.code, language="python")
        guides = (
            "end / start 是期末与期初的比值；减 1 得到收益率。** 表示乘方，years 表示期数。",
            "close 是按日期排列的收盘价。rolling(n) 每次只看当前及此前 n 行；mean() 对窗口求平均。",
            "returns 是一列数值。var 和 std 分别计算方差和标准差；ddof=1 使用样本分母 n−1。",
            "pct_change() 把价格变成逐期收益；dropna() 去掉首个无前期价格的空值。**0.5 表示开平方。",
            "cummax() 记录截至每个时点出现过的最高净值。当前净值除以此前最高值再减 1 得到回撤。",
            "先从收益均值减去同周期无风险收益，再除以样本标准差。最后按交易日近似年化。",
            "series_x 和 series_y 是同一组日期上的两列数据；corr() 返回它们的线性相关系数。",
            "iloc 按行的位置切片；:split 取较早样本，split: 取较晚样本。测试样本不参与选参。",
        )
        st.write(guides[choice])
    readings = {}
    current_readings = {}
    if choice == 0:
        readings = {"simple_return": float(frame["本金"].iloc[-1]/100-1), "compound": float(frame["本金"].iloc[-1]/100-1)}
    elif choice == 1:
        readings["moving_average"] = float(frame["均线"].iloc[-1])
    elif choice == 2:
        readings = {"variance": float(frame["样本值"].var(ddof=1)), "std": float(frame["样本值"].std(ddof=1))}
    elif choice == 3:
        readings["volatility"] = float(frame["演示价格"].pct_change().dropna().std(ddof=1)*math.sqrt(252))
    elif choice == 4:
        readings["drawdown"] = float(frame["回撤"].min())
    elif choice == 5:
        daily = frame["演示收益率"]
        readings["sharpe"] = float((daily.mean()-value/100)/daily.std(ddof=1)*math.sqrt(252))
    elif choice == 6:
        readings["correlation"] = float(frame["X"].corr(frame["Y"]))
    elif choice == 7:
        current_readings["bias"] = (
            f"当前固定教学样本比较 {int(value)} 组参数。{conclusion}"
            "本课没有单一的‘偏差值’；应比较训练期选出的参数在测试期是否仍成立。"
        )
    for topic in LESSON_TOPICS[choice]:
        render_knowledge(
            topic,
            readings.get(topic),
            key="academy",
            period="当前固定教学样本（不是行情）",
            expanded=False,
            lazy=True,
            current_reading=current_readings.get(topic),
        )
    with st.expander("思考题与参考答案"):
        st.write(lesson.question)
        answers = (
            "不会。100 × 1.1 × 0.9 = 99，累计亏损 1%。两次百分比使用了不同基数。",
            "窗口越长通常越平滑，但响应也更慢。平滑和延迟需要一起比较。",
            "均值由同一组样本估计后，偏差之和固定为零，独立偏差少一个。只有一个观测无法估计样本标准差。",
            "不会。历史波动衡量离散程度，不直接给出未来方向或未来亏损概率。",
            "不会。后来的新高可以结束回撤区间，但已经发生的最大历史跌幅仍保留。",
            "标准差为零时分母为零，不能报一个可解释的无限夏普；短样本也不支持稳定推断。",
            "不保证。相关性可能随市场状态改变，历史样本也可能不具代表性。",
            "不再独立。看到测试结果后继续修改规则，相当于让测试信息参与了选择，需要新的未用样本。",
        )
        st.write(answers[choice])
    previous, following = st.columns(2)
    previous.button("上一课", key="academy_previous", disabled=choice == 0, on_click=_choose_lesson, args=(choice-1,))
    following.button("下一课", key="academy_next", disabled=choice == len(LESSONS)-1, on_click=_choose_lesson, args=(choice+1,))
    from quant_lab.ui_manual import open_manual_article
    st.button(
        "在使用手册中继续阅读",
        key="academy_to_manual",
        on_click=open_manual_article,
        args=(ARTICLE_BY_TOPIC[LESSON_TOPICS[choice][0]],),
    )
