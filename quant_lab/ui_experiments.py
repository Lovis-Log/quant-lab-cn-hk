"""Research validation UI; trusted local computation, bounded grids and replay."""

from dataclasses import asdict
import sqlite3
import hashlib
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quant_lab.experiment_comparison import compare_cases,compare_saved,session_case
from quant_lab.jobs import JobState
from quant_lab.research_reports import prepare_lab_inputs,calculate_lab,replay_validation_archive
from quant_lab.research_validation import ValidationRecipe
from quant_lab.research_versions import LEGACY_VERSIONS,VALIDATION_VERSIONS
from quant_lab.storage import list_experiments,save_experiment
from quant_lab.ui_helpers import require_history,bundle_key,style_figure
from quant_lab.ui_jobs import submit_task,take_result,loading_placeholder
from quant_lab.ui_strategy import _strategy_controls,_backtest_config


def _integers(text):
    try:return tuple(int(value.strip()) for value in text.replace("，",",").split(",") if value.strip())
    except ValueError as error:raise ValueError("候选周期请使用逗号分隔的整数。") from error


def _render_comparison(result):
    if result.summary["输入标记"].eq("教学/模拟").any():st.info("所选实验含教学/模拟输入，不能把这些曲线解释为真实股票业绩。")
    if not result.directly_comparable:
        st.warning("数据、区间、证券或版本不同，不可直接比较："+"、".join(result.reasons))
    elif not result.test_comparable:
        st.warning("全样本数据模型一致，但样本外切分不同，不能直接比较样本外列。")
    st.dataframe(result.summary.style.format({"全样本收益":"{:.2%}","最大回撤":"{:.2%}","样本外收益":"{:.2%}","夏普":"{:.3f}"},na_rep="—"),width="stretch",hide_index=True)
    if not result.differences.empty:
        differences=result.differences.copy()
        fields={"strategy":"策略参数","costs":"成交与费用假设","train_fraction":"训练比例","market":"市场","symbol":"证券代码","currency":"币种",
            "start":"起点","end":"终点","source":"来源","received_at":"接收时间","versions":"算法/规则版本","version_declared":"版本是否显式记录",
            "validation_versions":"验证版本","raw_sha256":"原始价版本","signal_sha256":"信号价版本","test_start":"样本外起点"}
        for i in differences.index:
            field=differences.loc[i,"字段"]
            if field=="strategy":
                from quant_lab.strategy import STRATEGY_NAMES
                for column in differences.columns[1:]:
                    value=json.loads(differences.loc[i,column])
                    differences.loc[i,column]=f"{STRATEGY_NAMES.get(value['kind'],value['kind'])} · 短{value['short_window']} / 长{value['long_window']}"
            differences.loc[i,"字段"]=fields.get(field,field)
        st.dataframe(differences,width="stretch",hide_index=True)
    if result.curves is not None:
        colors=("#78A7DB","#C6A56D","#B4BCC5","#73B798","#D7797E","#A39CC7")
        figure=go.Figure([go.Scatter(x=result.curves.index,y=result.curves[column],name=column,line={"color":colors[i]}) for i,column in enumerate(result.curves)])
        st.plotly_chart(style_figure(figure,290),width="stretch",theme=None)
    st.caption("对比固定基础策略全样本结果；参数、费用和资金假设差异不能只归因为信号。不同币种不相加。滚动结果在各实验报告中单独核对。")


def render_experiment_lab(bundle):
    st.caption("有界参数研究 · 连续滚动样本外 · 成本压力 · 离线复算")
    mode=st.radio("研究实验台内容",("当前行情验证","存档实验比较"),horizontal=True,key="lab_mode")
    st.session_state["active_lab_context"]={"page":"研究实验台","data_status":"本地研究，尚未完成新验证"}
    if mode=="存档实验比较":
        try:records=list_experiments(include_deleted=False)
        except (ValueError,OSError,sqlite3.Error) as error:st.error(str(error));return
        labels={row["id"]:f"#{row['id']} {row['title']} · {row['market']} {row['symbol']}" for row in records}
        previous=st.session_state.get("lab_saved_selection",[])
        if any(value not in labels for value in previous):st.session_state["lab_saved_selection"]=[value for value in previous if value in labels]
        selected=st.multiselect("选择2–6个存档实验",tuple(labels),format_func=lambda value:labels[value],key="lab_saved_selection")
        requested=st.button("复算并比较所选存档",disabled=not 2<=len(selected)<=6,key="lab_compare_saved")
        key=tuple(selected)
        if requested:submit_task("lab_saved_compare",key,compare_saved,key,cpu=True,job_timeout=300)
        completed=take_result("lab_saved_compare",key)
        if completed and completed.state==JobState.SUCCEEDED:
            st.session_state["lab_saved_comparison"]=(key,completed.result)
            st.session_state.pop("lab_saved_error",None)
        elif completed and completed.state==JobState.FAILED:st.session_state["lab_saved_error"]=(key,completed.error)
        failure=st.session_state.get("lab_saved_error")
        if failure and failure[0]==key:st.error(failure[1]+"；已显示的结果仍是上次成功复算。")
        saved=st.session_state.get("lab_saved_comparison")
        if saved and saved[0]==key:
            _render_comparison(saved[1])
            facts=saved[1].summary[["输入标记","市场","代码","币种","全样本收益","最大回撤"]].to_dict(orient="records")
            st.session_state["active_lab_context"]={"page":"研究实验台","data_status":"上次成功复算，本次失败；私人笔记未附带" if failure and failure[0]==key else "存档数字已本地复算，私人笔记未附带",
                "data_fingerprint":hashlib.sha256(repr((key,facts)).encode()).hexdigest(),
                "statistics":{"experiment_comparison":{"count":len(key),"directly_comparable":saved[1].directly_comparable,"facts":facts}}}
        with st.expander("完整验证配方离线复算"):
            st.caption("重跑一个已保存验证实验的扫描、滚动与压力，不联网、不改旧档；普通旧基础档没有验证配方时会明确提示。")
            if selected:
                if st.session_state.get("lab_replay_id") not in selected:st.session_state["lab_replay_id"]=selected[0]
                identifier=st.selectbox("选择完整复算实验",tuple(selected),format_func=lambda value:labels[value],key="lab_replay_id")
                if st.button("复算存档验证配方",key="lab_replay_validation"):
                    submit_task("lab_archive_replay",identifier,replay_validation_archive,identifier,cpu=True,job_timeout=300)
                replayed=take_result("lab_archive_replay",identifier)
                if replayed and replayed.state==JobState.SUCCEEDED:
                    st.session_state["lab_archive_replay_result"]=(identifier,replayed.result)
                    st.session_state.pop("lab_archive_replay_error",None)
                elif replayed and replayed.state==JobState.FAILED:st.session_state["lab_archive_replay_error"]=(identifier,replayed.error)
                failure=st.session_state.get("lab_archive_replay_error")
                failed=bool(failure and failure[0]==identifier)
                if failed:st.error(failure[1]+"；未把旧结果冒充本次复算成功。")
                outcome=st.session_state.get("lab_archive_replay_result")
                if outcome and outcome[0]==identifier and not failed:
                    st.success("验证配方离线复算一致："+outcome[1].audit_id)
                    st.caption(f"{len(outcome[1].scan)}组候选，{len(outcome[1].folds)}折，{len(outcome[1].stress)}个成本情景；原记录未改写。")
            else:st.caption("请先选择需要读取的存档实验。")
        if not records:st.info("尚无存档。现有未获留存许可的真实数据不会自动写入实验库；会话对比可用于当前研究。")
        return
    if not require_history(bundle):return
    teaching=any(token in bundle.source.lower() for token in ("教学","模拟","demo","teaching","simulation"))
    if teaching:st.info("当前为固定教学/模拟数据，非真实股票行情；验证仅用于核对本地研究流程。")
    st.caption("验证只使用配对后的不复权数据生成信号；所选复权口径只用于一致性核对。A/H价格与成本模型，不含股息或公司行动重建。")
    with st.form("lab_validation_parameters",border=False):
        spec=_strategy_controls("lab")
        config=_backtest_config(bundle.market)
        columns=st.columns(3)
        shorts=columns[0].text_input("扫描短周期",value="5,10",key="lab_shorts")
        longs=columns[1].text_input("扫描长周期",value="20,30",key="lab_longs")
        score=columns[2].selectbox("训练选参目标",("return","sharpe"),format_func=lambda x:"训练累计收益" if x=="return" else "训练夏普",key="lab_score")
        fraction=st.slider("固定训练比例",.5,.85,.7,.05,key="lab_fraction")
        columns=st.columns(3)
        default_train=min(126,max(35,len(bundle.frame)//2))
        train=columns[0].number_input("滚动训练条数",min_value=35,max_value=5000,value=default_train,key="lab_train")
        test=columns[1].number_input("每折测试条数",min_value=5,max_value=1000,value=min(42,max(5,(len(bundle.frame)-default_train)//3)),key="lab_test")
        folds=columns[2].number_input("最多滚动折数",min_value=1,max_value=8,value=4,key="lab_folds")
        stress=st.text_input("成本倍数（含1，最多6种）",value="0,1,2,3",key="lab_stress")
        st.caption("最多36组有效候选、8折、200万预计行次；每折测试不参与该折选参。最近最多N折连续执行，不免费重置持仓。")
        requested=st.form_submit_button("运行研究验证",type="primary")
    if spec is None:return
    try:
        recipe=ValidationRecipe(spec,config,_integers(shorts),_integers(longs),fraction,int(train),int(test),int(folds),score,
            tuple(float(value.strip()) for value in stress.replace("，",",").split(",") if value.strip()))
        recipe.validate(len(bundle.frame))
    except (ValueError,TypeError,OverflowError) as error:st.warning(str(error));return
    key=(bundle_key(bundle),bundle.source,bundle.currency,bundle.received_at,recipe)
    if requested:submit_task("lab_inputs",key,prepare_lab_inputs,bundle,job_timeout=300)
    prepared=take_result("lab_inputs",key)
    if prepared and prepared.state==JobState.SUCCEEDED:
        st.session_state["lab_pending"]=(key,prepared.result)
        submit_task("lab_validation",(key,prepared.result.input_manifest["batch_id"]),calculate_lab,prepared.result,recipe,cpu=True,job_timeout=300)
    elif prepared and prepared.state==JobState.FAILED:st.session_state["lab_error"]=(key,prepared.error)
    pending=st.session_state.get("lab_pending")
    completed=take_result("lab_validation",(key,pending[1].input_manifest["batch_id"] if pending and pending[0]==key else None))
    if completed and completed.state==JobState.SUCCEEDED:
        inputs=st.session_state["lab_pending"][1]
        suite,report=completed.result
        st.session_state["lab_result"]=(key,inputs,suite,report)
        st.session_state.pop("lab_error",None)
        shelf=st.session_state.setdefault("lab_shelf",{})
        shelf.pop(suite.audit_id,None)
        shelf[suite.audit_id]=(inputs,recipe,suite)
        while len(shelf)>6:shelf.pop(next(iter(shelf)))
    elif completed and completed.state==JobState.FAILED:st.session_state["lab_error"]=(key,completed.error)
    error=st.session_state.get("lab_error")
    if error and error[0]==key:st.error(error[1])
    saved=st.session_state.get("lab_result")
    if any(slot in st.session_state.get("_task_tickets",{}) for slot in ("lab_inputs","lab_validation")):
        st.caption("正在执行本地验证，可切页或取消；旧结果仍对应上次完成的输入。")
        if not saved or saved[0]!=key:loading_placeholder(240)
    if not saved or saved[0]!=key:return
    _,inputs,suite,report=saved
    stale=bool(error and error[0]==key)
    if stale:st.warning("本次验证失败；以下仍为上次成功结果，不是新计算。")
    st.markdown("#### 研究验证已完成")
    st.caption(f"{suite.audit_id} · {suite.manifest['candidates']}组有效候选 · 无效配对{suite.manifest['rejected_pairs']}组未计算")
    columns=st.columns(4)
    columns[0].metric("基础策略价格收益",f"{suite.base.full_stats.cumulative_return:.2%}")
    columns[1].metric("滚动样本外收益",f"{suite.rolling.equity.equity.iloc[-1]/config.initial_cash-1:.2%}")
    fee=suite.diagnostics.summary["charged_fees"]
    compact=f"{fee/1e8:.2f}亿" if fee>=1e8 else f"{fee/10000:.2f}万" if fee>=10000 else f"{fee:,.2f}"
    columns[2].metric(f"实收费用（{inputs.provenance['currency']}）",compact,help=f"完整费用：{fee:,.6f}；不含另列滑点估计。")
    columns[3].metric("平均仓位暴露",f"{suite.diagnostics.summary['average_exposure']:.2%}")
    scan_tab,walk_tab,stress_tab,diagnostic_tab=st.tabs(("训练参数扫描","滚动样本外","成本压力","成交与风险诊断"),key="lab_result_tab",on_change="rerun")
    with scan_tab:
        if scan_tab.open:
            table=suite.scan.rename(columns={"short":"短周期","long":"长周期","training_return":"训练收益","training_sharpe":"训练夏普","training_drawdown":"训练回撤","score":"训练目标值","filled_orders":"成交次数"})
            st.dataframe(table.style.format({"训练收益":"{:.2%}","训练夏普":"{:.3f}","训练回撤":"{:.2%}",
                "训练目标值":"{:.2%}" if recipe.score=="return" else "{:.3f}"},na_rep="—"),width="stretch",hide_index=True)
    with walk_tab:
        if walk_tab.open:
            table=suite.folds.rename(columns={"fold":"折数","train_start":"训练起点","train_end":"训练终点","test_start":"测试起点","test_end":"测试终点",
                "short":"短周期","long":"长周期","training_score":"训练目标值","test_return":"样本外收益"})
            for field in ("训练起点","训练终点","测试起点","测试终点"):table[field]=table[field].dt.strftime("%Y-%m-%d")
            st.dataframe(table.style.format({"样本外收益":"{:.2%}","训练目标值":"{:.2%}" if recipe.score=="return" else "{:.3f}"}),width="stretch",hide_index=True)
            figure=go.Figure(go.Scatter(x=suite.rolling.equity.date,y=suite.rolling.equity.equity/config.initial_cash,name="连续滚动样本外",line={"color":"#78A7DB"}))
            st.plotly_chart(style_figure(figure,300),width="stretch",theme=None)
            coverage=suite.manifest["rolling_coverage"]
            st.caption(f"滚动测试 {coverage['first_test']} 至 {coverage['last_test']}，共{coverage['test_rows']}条；尾部{coverage['tail_rows_not_tested']}条未测试。后续训练可包含此前已结束的测试观察。")
    with stress_tab:
        if stress_tab.open:
            table=suite.stress.rename(columns={"multiplier":"成本倍数","status":"状态","return":"策略价格收益","max_drawdown":"最大回撤","charged_fees":"实收费用","slippage_estimate":"滑点价差估计","error":"失败原因"})
            table["状态"]=table["状态"].replace({"success":"成功","failed":"失败"})
            st.dataframe(table.style.format({"策略价格收益":"{:.2%}","最大回撤":"{:.2%}","实收费用":"{:,.2f}","滑点价差估计":"{:,.2f}"},na_rep="—"),width="stretch",hide_index=True)
    with diagnostic_tab:
        if diagnostic_tab.open:
            labels={"order_attempts":"订单尝试","filled_orders":"成交订单","blocked_orders":"未成交订单","commission":"佣金","additional_fees":"附加费用",
                "charged_fees":"实收费用","slippage_estimate":"滑点价差估计","traded_notional":"累计成交金额","notional_turnover":"成交金额/平均权益",
                "average_exposure":"平均仓位暴露","maximum_exposure":"最大仓位暴露"}
            st.table(pd.DataFrame([{"指标":labels.get(key,key),"数值":f"{value:.2%}" if key.endswith("exposure") else value} for key,value in suite.diagnostics.summary.items()]))
            st.dataframe(suite.diagnostics.costs,width="stretch",hide_index=True)
            st.dataframe(suite.diagnostics.blocked,width="stretch",hide_index=True)
            st.caption("实收费用不含成交价差滑点估计；换手为累计双边成交金额/平均日权益。公司行动未核验且未重建，不是已确认无事件。")
    if report:
        st.download_button("导出可离线复算研究报告",report,file_name=suite.audit_id.replace(":","_")+".zip",mime="application/zip",key="lab_export")
        if st.button("保存验证实验",key="lab_save"):
            try:
                p=inputs.provenance
                identifier=save_experiment(title=f"{p['symbol']} 研究验证 {suite.audit_id[-6:]}",hypothesis="固定参数与滚动样本外结果在明确费用假设下可复算。",notes="",
                    market=p["market"],symbol=p["symbol"],raw_history=inputs.raw,signal_history=inputs.raw,spec=recipe.base,config=config,
                    train_fraction=fraction,result=suite.base,source=p["source"],adjustment="",received_at=bundle.received_at,
                    company_name=p["company_name"],input_manifest=inputs.input_manifest,version_metadata=LEGACY_VERSIONS,
                    validation_metadata={"versions":dict(VALIDATION_VERSIONS),"recipe":suite.manifest["recipe"],"provenance":suite.manifest["provenance"],"audit_id":suite.audit_id})
                st.success(f"验证实验 #{identifier} 已保存，原始输入及配方可离线复算。")
            except (ValueError,OSError,sqlite3.Error) as error:st.error(str(error))
    else:st.caption("来源留存许可未通过：可在会话研究/对比，暂不导出含完整行情的报告或新增存档；旧档保持可用。")
    shelf=st.session_state.get("lab_shelf",{})
    with st.expander("比较会话实验（最近6个）"):
        previous=st.session_state.get("lab_session_selection",[])
        if any(value not in shelf for value in previous):st.session_state["lab_session_selection"]=[value for value in previous if value in shelf]
        identifiers=st.multiselect("选择2–6个会话实验",tuple(shelf),format_func=lambda value:value[-12:],key="lab_session_selection")
        if 2<=len(identifiers)<=6:
            _render_comparison(compare_cases(tuple(session_case(*shelf[value]) for value in identifiers)))
        else:st.caption("每次完成不同参数的验证都会保留到会话对比架，最多6个；不是自动磁盘存档。")
    st.session_state["active_lab_context"]={"page":"研究实验台","data_fingerprint":suite.audit_id,"market":bundle.market,"symbol":bundle.symbol,
        "data_status":("本次失败，沿用上次成功结果；" if stale else "")+("教学/模拟，非真实行情；" if teaching else "历史原始价格本地研究；")+"公司行动未重建","statistics":{"research_validation":{"base_return":suite.base.full_stats.cumulative_return,
            "rolling_return":float(suite.rolling.equity.equity.iloc[-1]/config.initial_cash-1),"folds":len(suite.folds),"charged_fees":suite.diagnostics.summary["charged_fees"]}}}
