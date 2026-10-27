"""Read-only live-source coverage probe; never saves raw prices or credentials."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]


def worker(args):
    sys.path.insert(0, str(ROOT))
    from quant_lab.data import AKShareProvider
    from quant_lab.data_quality import calendar_reference
    from quant_lab.history_ranges import history_window
    from quant_lab.market_data import normalize_symbol
    from quant_lab.names import NameProvider
    from quant_lab.processing import DataValidationError
    from quant_lab.data import DataUnavailableError
    from quant_lab.security import redact

    symbol = normalize_symbol(args.market, args.symbol)
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
    reference = calendar_reference(args.market, today-timedelta(days=20), today)
    finished = [day for day, close in reference.sessions if close <= now]
    end = max(finished) if finished else today-timedelta(days=1)
    start, end = history_window(end, args.years)
    try:
        name = NameProvider().lookup(args.market, symbol)
    except Exception:
        name = "名称暂不可用"
    report = {"market": args.market, "symbol": symbol, "company_name": name,
        "requested_start": str(start), "requested_end": str(end),
        "attempted_at_utc": now.isoformat(), "synthetic": False,
        "raw_prices_saved": False, "scope": "public historical interface; no paid service; metadata only"}
    try:
        provider = AKShareProvider()
        bundle = provider.history(args.market, symbol, start, end, "qfq" if args.paired else "")
        report.update({"status": "success", "source": bundle.source, "currency": bundle.currency,
            "received_at": bundle.received_at.isoformat(), "rows": len(bundle.frame),
            "actual_start": str(bundle.frame.date.iloc[0].date()) if len(bundle.frame) else None,
            "actual_end": str(bundle.frame.date.iloc[-1].date()) if len(bundle.frame) else None,
            "sha256": hashlib.sha256(bundle.frame.to_csv(index=False).encode()).hexdigest(),
            "calendar": bundle.quality.calendar_name, "calendar_version": bundle.quality.calendar_version,
            "missing_reference_dates": len(bundle.quality.missing_sessions),
            "off_calendar_dates": len(bundle.quality.off_calendar_sessions),
            "coverage_status": bundle.quality.coverage_label, "segments": bundle.segments,
            "batch_id": bundle.batch_id})
        if args.paired:
            from quant_lab.research_inputs import prepare_inputs
            inputs = prepare_inputs(bundle, fetch=lambda *params, **kwargs: provider.history(*params))
            report["paired_input_check"] = {"status":"passed", "raw_sha256":inputs.manifest["raw"]["sha256"],
                "signal_sha256":inputs.manifest["signal"]["sha256"], "revision_check":inputs.manifest["revision_check"],
                "batch_id":inputs.manifest["batch_id"], "raw_rows":len(inputs.raw), "signal_rows":len(inputs.signal)}
    except Exception as error:
        report.update({"status": "failed", "error_type": type(error).__name__,
            "error": redact(str(error)) if isinstance(error,(DataValidationError,DataUnavailableError)) else
                     "真实历史请求或校验失败；不能据此断言证券不存在。"})
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=("A 股", "港股"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--paired", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.worker:
        worker(args)
        return
    directory = ROOT / ".tools" / ("live-history-"+uuid4().hex)
    directory.mkdir(parents=True)
    output = directory / "coverage.json"
    env = {**os.environ, "QUANT_LAB_DATA_DIR": str(directory/"user")}
    command = [sys.executable,str(Path(__file__).resolve()),"--worker","--market",args.market,
               "--symbol",args.symbol,"--years",str(args.years),"--output",str(output)]
    if args.paired:
        command.append("--paired")
    with (directory/"probe.log").open("w",encoding="utf-8") as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        try:
            child.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
            output.write_text(json.dumps({"status":"timeout", "market":args.market,"symbol":args.symbol,
                "synthetic":False,"raw_prices_saved":False,"error":"真实源未在限时内返回；未使用模拟数据。"},ensure_ascii=False,indent=2),encoding="utf-8")
    if not output.exists():
        raise RuntimeError(f"Probe did not produce a receipt: {directory}")
    report = json.loads(output.read_text(encoding="utf-8"))
    print(json.dumps({"report":str(output),**report},ensure_ascii=False))


if __name__ == "__main__":
    main()
