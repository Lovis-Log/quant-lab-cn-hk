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
            if key=="compare_window" and type(number) is not int:raise ValueError("滚动窗口须为整数。")
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
    return {**restored, **navigation_values(restored)}
