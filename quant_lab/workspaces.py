"""Small, whitelisted workspace preferences; no prices, notes or credentials."""

from datetime import date
import json
import math
import os
import shutil
from threading import RLock
from uuid import uuid4

from quant_lab.market_data import normalize_symbol
from quant_lab.paths import user_data_dir
from quant_lab.navigation import MARKETS, RESEARCH, SECTIONS, navigation_values


NAMES=("学习","单股票研究","多股票比较")
DEFAULTS={
    "学习":{"nav_page":"Quant Academy","manual_panel_open":True,"deepseek_panel_open":False,"notes_panel_open":False,"maximized_panel":None,"active_dock_panel":"manual","left_sidebar_visible":True},
    "单股票研究":{"nav_page":"市场数据","manual_panel_open":False,"deepseek_panel_open":False,"notes_panel_open":False,"maximized_panel":None,"active_dock_panel":"manual","left_sidebar_visible":True},
    "多股票比较":{"nav_page":"多股票比较","manual_panel_open":False,"deepseek_panel_open":False,"notes_panel_open":False,"maximized_panel":None,"active_dock_panel":"manual","left_sidebar_visible":True},
}
_LOCK=RLock()
BOOLS={"manual_panel_open","deepseek_panel_open","notes_panel_open","left_sidebar_visible","comparison_watch_open"}
NUMBERS={"compare_window":(2,252),"compare_fraction":(.5,.85),"compare_cash":(100,1e12),
    "compare_commission":(0,10000),"compare_minimum":(0,1e8),"compare_buyfee":(0,10000),"compare_sellfee":(0,10000),"compare_slippage":(0,9999)}
OPTIONS={"nav_page":{"Quant Academy","市场数据","多股票比较","历史回测","策略实验室","风险与组合","统计与机器学习","美股研究","美股数据","研究实验台"},
    "nav_section":set(SECTIONS),"research_page":set(RESEARCH),
    "market_selection":set(MARKETS),"compare_market":set(MARKETS),"compare_adjustment":{"","qfq","hfq"},
    "compare_frequency":{"monthly","daily"},"history_preset":{"1 年","3 年","5 年","10 年","自定义"},
    "compare_limit":{"10%","5%","20%","30%","不模拟"},"active_dock_panel":{"manual","notes","deepseek"},"maximized_panel":{None,"manual","notes","deepseek"}}
DATES={"history_start","history_end","compare_start","compare_end"}
DATES.update({"us_price_start","us_price_end","us_compare_start","us_compare_end"})
NUMBERS.update({"us_compare_window":(2,252),"us_price_bt_fraction":(.5,.85),
               "us_price_port_fraction":(.5,.85),"us_price_val_fraction":(.5,.85),"us_price_ml_fraction":(.55,.85)})
for _prefix in ("us_price_bt", "us_price_port", "us_price_val"):
    NUMBERS.update({_prefix+"_cash":(100,1e10),_prefix+"_commission":(0,1000),
                    _prefix+"_minimum":(0,1e6),_prefix+"_slip":(0,999),_prefix+"_sellfee":(0,1000)})
OPTIONS.update({"us_research_mode":{"真实行情价格研究","离线教学样本"},
                "us_price_page":{"策略信号","历史回测","风险与组合","统计分析","专业验证"},
                "us_price_period":{1,3,5,10,"自定义"},"us_price_port_frequency":{"monthly","daily"}})


def sanitized(values):
    result={}
    for key in BOOLS:
        if key in values:
            if type(values[key]) is not bool:raise ValueError("布局开关必须为布尔值。")
            result[key]=values[key]
    for key,(low,high) in NUMBERS.items():
        if key in values:
            number=values[key]
            if isinstance(number,bool) or not isinstance(number,(int,float)) or not math.isfinite(number) or not low<=number<=high:
                raise ValueError("工作区数值设置超出允许范围。")
            if key in {"compare_window","us_compare_window"} and type(number) is not int:raise ValueError("滚动窗口须为整数。")
            result[key]=number
    for key,options in OPTIONS.items():
        if key in values:
            if values[key] not in options:raise ValueError("工作区选项不受支持。")
            result[key]=values[key]
    for key in DATES:
        if key in values:
            value=values[key]
            result[key]=value.isoformat() if isinstance(value,date) else date.fromisoformat(value).isoformat()
    market=values.get("compare_market","A 股")
    if "compare_codes" in values and market != "美股":
        codes=[normalize_symbol(market,code.strip()) for code in values["compare_codes"].split(",") if code.strip()]
        if len(codes)>10 or len(set(codes))!=len(codes):raise ValueError("保存的比较代码须为至多10只唯一股票。")
        result["compare_codes"]=",".join(codes)
    if "compare_benchmark" in values and market != "美股":
        result["compare_benchmark"]=normalize_symbol(market,values["compare_benchmark"]) if values["compare_benchmark"].strip() else ""
    if "compare_lots" in values and market != "美股":
        lots=values["compare_lots"]
        if not isinstance(lots,dict) or len(lots)>10 or any(type(lot) is not int or lot<1 or lot>1000000 for lot in lots.values()):
            raise ValueError("保存的逐股单位无效。")
        result["compare_lots"]={normalize_symbol(market,code):lot for code,lot in lots.items()}
    for market_name in ("A 股","港股"):
        key="symbol_"+market_name
        if key in values:result[key]=normalize_symbol(market_name,values[key].split(" · ")[0])
    from quant_lab.us_market import normalize_us_symbol
    if "us_compare_codes" in values:
        codes=[normalize_us_symbol(value) for value in values["us_compare_codes"].replace("，",",").split(",") if value.strip()]
        if len(codes)>10 or len(set(codes))!=len(codes):raise ValueError("美股比较代码须为至多10只唯一股票。")
        result["us_compare_codes"]=",".join(codes)
    for key in ("us_price_symbol","us_compare_baseline"):
        if key in values:
            result[key]=normalize_us_symbol(values[key]) if values[key].strip() else ""
    return result


class WorkspaceStore:
    def __init__(self,path=None):
        self.path=path

    def _path(self):return self.path or user_data_dir()/"workspace-presets.json"

    def load(self):
        path=self._path()
        if not path.exists():return {"format":2,"active":None,"profiles":{}}
        if path.stat().st_size>65536:raise ValueError("工作区设置文件超过64KB。")
        payload=json.loads(path.read_text(encoding="utf-8"))
        if payload.get("format") not in (1,2) or payload.get("active") not in (None,*NAMES) or not isinstance(payload.get("profiles"),dict):
            raise ValueError("工作区设置版本或结构无法读取，原文件保留。")
        return {"format":payload["format"],"active":payload["active"],"profiles":{name:sanitized(value) for name,value in payload["profiles"].items() if name in NAMES}}

    def _write(self,payload):
        path=self._path()
        path.parent.mkdir(parents=True,exist_ok=True)
        if payload["format"] == 1:
            backup = path.with_name(path.name + ".v1.bak")
            if path.exists() and not backup.exists():
                shutil.copy2(path, backup)
        payload = {**payload, "format": 2}
        temporary=path.with_name(path.name+"."+uuid4().hex+".tmp")
        try:
            temporary.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            os.replace(temporary,path)
        finally:
            if temporary.exists():temporary.unlink()

    def save(self,name,values):
        if name not in NAMES:raise ValueError("未知工作区预设。")
        clean=sanitized(values)
        with _LOCK:
            payload=self.load()
            payload["profiles"][name]=clean
            payload["active"]=name
            self._write(payload)

    def activate(self,name):
        if name not in NAMES:raise ValueError("未知工作区预设。")
        with _LOCK:
            payload=self.load()
            payload["active"]=name
            self._write(payload)
            return {**DEFAULTS[name],**payload["profiles"].get(name,{})}


def restore_values(values):
    restored = {key:date.fromisoformat(value) if key in DATES else value for key,value in values.items()}
    # Old US-only controls remain readable; shared values take precedence.
    if restored.get("market_selection") == "美股":
        for old, new in (("us_price_start", "history_start"), ("us_price_end", "history_end")):
            if old in restored:
                restored.setdefault(new, restored[old])
        if "us_price_period" in restored:
            period = restored["us_price_period"]
            restored.setdefault("history_preset", f"{period} 年" if isinstance(period, int) else "自定义")
        if "us_price_page" in restored and "research_page" not in restored:
            restored["research_page"] = next(key for key, label in RESEARCH.items() if label == restored["us_price_page"])
    return {**restored, **navigation_values(restored)}
