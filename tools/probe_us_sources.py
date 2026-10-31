"""Bounded, metadata-only US free-source probe; no application market enablement."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[1]


def worker(args):
    import akshare as ak
    import pandas as pd
    sys.path.insert(0,str(ROOT))
    from quant_lab.us_market import us_schedule
    from quant_lab.history_ranges import history_window
    now=datetime.now(timezone.utc)
    today=now.astimezone(ZoneInfo("America/New_York")).date()
    schedule=us_schedule(today-timedelta(days=20),today)
    ended=schedule.loc[schedule["close"]<=pd.Timestamp(now)]
    if ended.empty:
        raise ValueError("参考交易日历未给出最近已结束日线。")
    end=ended.index[-1].date()
    start,_=history_window(end,10)
    report = {"source": args.source, "ticker": "AAPL", "synthetic": False,
        "checked_at": now.isoformat(), "requested": [str(start),str(end)],
        "raw_prices_saved": False, "application_backtest_enabled": False, "results": {}}
    for adjustment in ("", "qfq"):
        name = adjustment or "unadjusted_parameter"
        try:
            if args.source == "akshare-sina":
                frame = ak.stock_us_daily(symbol="AAPL", adjust=adjustment)
            else:
                frame = ak.stock_us_hist(symbol="105.AAPL", period="daily", start_date=start.strftime("%Y%m%d"),
                                         end_date=end.strftime("%Y%m%d"), adjust=adjustment)
                frame = frame.rename(columns={"日期":"date", "开盘":"open", "收盘":"close",
                    "最高":"high", "最低":"low", "成交量":"volume"})
            if "date" not in frame:
                frame = frame.reset_index()
            frame["date"] = pd.to_datetime(frame.date)
            frame = frame.loc[frame.date.between(pd.Timestamp(start),pd.Timestamp(end))].sort_values("date")
            valid_prices = frame.loc[:,["open","high","low","close"]].apply(pd.to_numeric,errors="coerce")
            item = {"status":"returned", "rows":len(frame), "columns":list(frame.columns),
                "actual_start":str(frame.date.iloc[0].date()) if len(frame) else None,
                "actual_end":str(frame.date.iloc[-1].date()) if len(frame) else None,
                "duplicate_dates":int(frame.date.duplicated().sum()),
                "invalid_price_rows":int((valid_prices.isna().any(axis=1)|(valid_prices<=0).any(axis=1)).sum()),
                "sha256":hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()}
            before = frame.loc[frame.date.eq("2020-08-28"),"close"]
            after = frame.loc[frame.date.eq("2020-08-31"),"close"]
            if len(before)==len(after)==1 and float(after.iloc[0])>0:
                item["split_boundary_close_ratio_diagnostic"] = round(float(before.iloc[0])/float(after.iloc[0]),6)
            item["company_actions_payment_dates_verified"] = False
            item["raw_execution_price_definition_verified"] = False
            item["retention_permission_verified"] = False
            report["results"][name] = item
        except Exception as error:
            report["results"][name] = {"status":"failed", "error_type":type(error).__name__,
                "note":"真实请求或结构校验失败，没有回退到模拟数据。"}
        Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",choices=("akshare-sina","akshare-eastmoney"),required=True)
    parser.add_argument("--timeout",type=int,default=75)
    parser.add_argument("--worker",action="store_true")
    parser.add_argument("--output")
    args=parser.parse_args()
    if args.worker:
        worker(args)
        return
    directory=ROOT/".tools"/("us-source-probe-"+uuid4().hex)
    directory.mkdir(parents=True)
    output=directory/"receipt.json"
    command=[sys.executable,str(Path(__file__).resolve()),"--source",args.source,"--worker","--output",str(output)]
    env={**os.environ,"QUANT_LAB_DATA_DIR":str(directory/"user")}
    with (directory/"probe.log").open("w",encoding="utf-8") as log:
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        try:
            child.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
            receipt=json.loads(output.read_text(encoding="utf-8")) if output.exists() else {"source":args.source,"results":{}}
            receipt.update({"status":"timeout", "synthetic":False, "raw_prices_saved":False,
                "application_backtest_enabled":False, "note":"限时终止真实请求；未完成口径未知。"})
            output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    if not output.exists():
        raise RuntimeError("Source worker exited without a receipt; inspect isolated probe log.")
    print(json.dumps({"report":str(output),**json.loads(output.read_text(encoding="utf-8"))},ensure_ascii=False))


if __name__=="__main__":
    main()
