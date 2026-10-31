"""Explicit offline, generated US examples, never a fallback for a live failure."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
import pandas as pd

from quant_lab.us_market import USInstrument, SettlementCalendar, us_schedule, NY
from quant_lab.us_data import USDataset, USAction, USActionBook
from quant_lab.source_rights import RetentionPolicy


TEACHING_US_RIGHTS=RetentionPolicy("quantlab-us-generated-v1",True,"repo:quant_lab/us_teaching.py","2026-10-28",
    "本地生成的美股教学样本，非真实股票行情；可以保存教学结果。")


def teaching_us_inputs():
    start,end=date(2024,5,20),date(2024,7,12)
    schedule=us_schedule(start,end)
    days=pd.DatetimeIndex(schedule.index).tz_localize(None)
    settlement_schedule=us_schedule(start,end+timedelta(days=20))
    # Deliberately supplied as a teaching assumption, not inferred to be the
    # production DTC calendar. Both capabilities are independently gated.
    settlement=SettlementCalendar(start,end+timedelta(days=20),tuple(settlement_schedule.index.date),
        "teaching-regular-sessions-v1","repo:quant_lab/us_teaching.py; synthetic settlement assumption",True)
    datasets={}
    for k,symbol in enumerate(("TEACHA","TEACHB")):
        price=100+np.arange(len(days))*.16+np.sin(np.arange(len(days))*.47+k)*2
        split_day=date(2024,6,10)
        ex_day=date(2024,6,18)
        if k==0:
            price[days.date>=split_day]/=2
            price[days.date>=ex_day]-=.5
        frame=pd.DataFrame({"date":days,"open":price,"high":price+1,"low":price-1,"close":price,"volume":100000.})
        known=datetime(2024,5,1,12,tzinfo=timezone.utc)
        events=(USAction("teaching-split",symbol,"split",split_day,"generated event",known,2,1),
                USAction("teaching-dividend",symbol,"dividend",ex_day,"generated event",known,
                    amount_per_share=Decimal('.5'),pay_at=datetime(2024,6,25,17,tzinfo=NY))) if k==0 else ()
        instrument=USInstrument(symbol,"离线教学证券"+str(k+1),"XNAS",source_codes=(("teaching",symbol),),identity_evidence="generated teaching identity")
        datasets[symbol]=USDataset(instrument,frame,"平台生成的固定美股教学样本（非真实行情）",
            datetime(2024,7,13,tzinfo=timezone.utc),USActionBook(symbol,start,end,True,"generated complete event book",events),
            "generated original execution prices","unadjusted-execution",TEACHING_US_RIGHTS,True)
    return datasets,settlement
