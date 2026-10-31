"""Bounded AH stage-six live check: metadata only, never retains raw prices."""

import argparse
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]


def worker(args):
    sys.path.insert(0,str(ROOT))
    from quant_lab.comparison import collect_comparison,compare_inputs
    from quant_lab.portfolio_cash import prepare_portfolio_execution,run_portfolio_research,CashPortfolioConfig
    from quant_lab.backtest import illustrative_config
    from quant_lab.data_quality import calendar_reference
    from quant_lab.history_ranges import history_window
    now=datetime.now(timezone.utc)
    today=now.astimezone(ZoneInfo("Asia/Shanghai")).date()
    reference=calendar_reference(args.market,today-timedelta(days=20),today)
    ended=[day for day,closing in reference.sessions if closing<=now]
    end=max(ended) if ended else today-timedelta(days=1)
    start,_=history_window(end,1)
    codes=tuple(args.codes.split(","))
    receipt={"synthetic":False,"raw_prices_saved":False,"market":args.market,"codes":codes,
        "checked_at":now.isoformat(),"requested_start":str(start),"requested_end":str(end),
        "costs_and_lots":"illustrative research assumptions, not current broker or exchange certification"}
    try:
        inputs=collect_comparison(args.market,codes,start,end)
        result=compare_inputs(inputs,codes[0])
        receipt.update({"status":"comparison_passed","currency":inputs.currency,"common_rows":len(result.closes),
            "common_start":str(result.closes.index[0].date()),"common_end":str(result.closes.index[-1].date()),
            "input_fingerprint":inputs.fingerprint,"sources":[{"code":code,"source":bundle.source,
                "received_at":bundle.received_at.isoformat() if bundle.received_at else None,
                "quality":bundle.quality.coverage_label,"observations":len(bundle.frame)} for code,bundle in inputs.bundles.items()]})
        try:
            prepared=prepare_portfolio_execution(inputs)
            cfg=CashPortfolioConfig(illustrative_config(args.market),tuple((code,100) for code in codes))
            research=run_portfolio_research(prepared,cfg)
            receipt["cash_model"]={"status":"passed","train_end":str(research.train_last_date.date()),
                "test_start":str(research.test_first_date.date()),"methods":list(research.runs),
                "audits":{name:run.audit_id for name,run in research.runs.items()},
                "minimum_cash":min(float(run.equity.cash.min()) for run in research.runs.values())}
        except Exception as error:
            receipt["cash_model"]={"status":"blocked","reason":str(error)[:300] if isinstance(error,ValueError) else type(error).__name__}
    except Exception as error:
        receipt.update({"status":"failed","reason":str(error)[:300] if isinstance(error,ValueError) else type(error).__name__})
    Path(args.output).write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market",choices=("A 股","港股"),required=True)
    parser.add_argument("--codes",required=True)
    parser.add_argument("--timeout",type=int,default=55)
    parser.add_argument("--worker",action="store_true")
    parser.add_argument("--output")
    args=parser.parse_args()
    if args.worker:worker(args);return
    directory=ROOT/".tools"/("comparison-live-"+uuid4().hex)
    directory.mkdir(parents=True)
    output=directory/"receipt.json"
    command=[sys.executable,str(Path(__file__).resolve()),"--market",args.market,"--codes",args.codes,"--worker","--output",str(output)]
    env={**os.environ,"QUANT_LAB_DATA_DIR":str(directory/"user")}
    with (directory/"probe.log").open("w",encoding="utf-8") as log:
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        try:child.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            child.kill();child.wait(timeout=5)
            output.write_text(json.dumps({"status":"timeout","synthetic":False,"raw_prices_saved":False,"market":args.market}),encoding="utf-8")
    if not output.exists():
        output.write_text(json.dumps({"status":"worker_failed","exit_code":child.returncode,"synthetic":False,
            "raw_prices_saved":False,"market":args.market,"reason":"来源进程未完成；请检查隔离日志，不能当作成功。"},ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"report":str(output),**json.loads(output.read_text(encoding="utf-8"))},ensure_ascii=False))


if __name__=="__main__":main()
