"""Bounded live validation probe; no raw-price export or paid requests."""

import argparse
from datetime import datetime,timedelta,timezone
import json,os
from pathlib import Path
import subprocess,sys
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]


def worker(args):
    sys.path.insert(0,str(ROOT))
    from quant_lab.backtest import illustrative_config
    from quant_lab.data import fetch_history_cached
    from quant_lab.data_quality import calendar_reference
    from quant_lab.history_ranges import history_window
    from quant_lab.research_reports import prepare_lab_inputs,calculate_lab
    from quant_lab.research_validation import ValidationRecipe
    from quant_lab.strategy import StrategySpec
    now=datetime.now(timezone.utc)
    today=now.astimezone(ZoneInfo("Asia/Shanghai")).date()
    reference=calendar_reference(args.market,today-timedelta(days=20),today)
    completed=[day for day,close in reference.sessions if close<=now]
    end=max(completed) if completed else today-timedelta(days=1)
    start,_=history_window(end,1)
    receipt={"synthetic":False,"raw_prices_saved":False,"market":args.market,"symbol":args.symbol,
        "checked_at":now.isoformat(),"requested_start":str(start),"requested_end":str(end),"scope":"AH price/cost research assumptions, not market-rule certification"}
    try:
        bundle=fetch_history_cached(args.market,args.symbol,start,end)
        inputs=prepare_lab_inputs(bundle)
        n=len(inputs.raw)
        train=min(126,max(35,n//2))
        recipe=ValidationRecipe(StrategySpec(),illustrative_config(args.market),rolling_train=train,rolling_test=min(42,max(5,(n-train)//3)))
        suite,report=calculate_lab(inputs,recipe)
        receipt.update({"status":"passed","source":bundle.source,"received_at":bundle.received_at.isoformat(),
            "actual_start":str(inputs.raw.date.iloc[0].date()),"actual_end":str(inputs.raw.date.iloc[-1].date()),"rows":n,
            "candidates":len(suite.scan),"folds":len(suite.folds),"rolling_rows":len(suite.rolling.equity),
            "stress_status":suite.stress[["multiplier","status"]].to_dict(orient="records"),
            "versions":suite.manifest["versions"],"raw_sha256":suite.manifest["raw_sha256"],"audit_id":suite.audit_id,
            "charged_fees":suite.diagnostics.summary["charged_fees"],"report_export_allowed":report is not None})
    except Exception as error:receipt.update({"status":"failed","reason":str(error)[:350] if isinstance(error,ValueError) else type(error).__name__})
    Path(args.output).write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market",choices=("A 股","港股"),default="A 股")
    parser.add_argument("--symbol",default="600519")
    parser.add_argument("--timeout",type=int,default=55)
    parser.add_argument("--worker",action="store_true")
    parser.add_argument("--output")
    args=parser.parse_args()
    if args.worker:worker(args);return
    directory=ROOT/".tools"/("validation-live-"+uuid4().hex)
    directory.mkdir(parents=True)
    output=directory/"receipt.json"
    with (directory/"probe.log").open("w",encoding="utf-8") as log:
        child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"--worker","--market",args.market,"--symbol",args.symbol,"--output",str(output)],
            cwd=ROOT,env={**os.environ,"QUANT_LAB_DATA_DIR":str(directory/"user")},stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        try:child.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
    if not output.exists():output.write_text(json.dumps({"status":"timeout-or-worker-failed","synthetic":False,"raw_prices_saved":False,"exit_code":child.returncode}),encoding="utf-8")
    print(json.dumps({"report":str(output),**json.loads(output.read_text(encoding="utf-8"))},ensure_ascii=False))


if __name__=="__main__":main()
