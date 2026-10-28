"""Measure actual WebView2 DOM interactions in an isolated source copy.

Synthetic data is injected ONLY into the copy. No credentials, paid APIs, or
production user files are read. Reports live in the ignored .tools directory.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def summary(values):
    ordered = sorted(values)
    return {"samples": len(values), "median_ms": round(ordered[len(ordered)//2], 1),
            "p95_ms": round(ordered[math.ceil(.95*len(ordered))-1], 1),
            "max_ms": round(ordered[-1], 1)}


def settle(page):
    page.wait_for_timeout(50)
    page.wait_for_function("""() => document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning' && ['manual','deepseek','notes'].every(kind=>document.querySelectorAll(`.st-key-${kind}_side_panel`).length<=1)""", timeout=45000)


@contextmanager
def capture_failure(page, directory):
    try:
        yield
    except Exception:
        try:
            page.screenshot(path=str(directory / "failure.png"))
            (directory / "failure-dom.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
            state = page.evaluate("""() => ({active:document.querySelector('.ql-dock-active')?.dataset.panel,compact:document.documentElement.dataset.qlDockCompact,panels:['manual','deepseek','notes'].map(kind=>{const node=document.querySelector(`.st-key-${kind}_side_panel`);return {kind,present:!!node,display:node&&getComputedStyle(node).display,style:node?.getAttribute('style')};})})""")
            (directory / "failure-layout.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        raise


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--functional", action="store_true")
    parser.add_argument("--viewport", choices=("1366x768", "1920x1080"))
    parser.add_argument("--io-delay", type=float, default=0)
    parser.add_argument("--visual", action="store_true")
    parser.add_argument("--legacy-theme", action="store_true")
    parser.add_argument("--diagnose-events", action="store_true")
    parser.add_argument("--history-quality", action="store_true")
    parser.add_argument("--us-research", action="store_true")
    parser.add_argument("--comparison", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 100:
        parser.error("repetitions must be 1..100")
    directory = ROOT / ".tools" / ("performance-" + uuid4().hex)
    source = directory / "source"
    source.mkdir(parents=True)
    for filename in ("app.py", "desktop_launcher.py"):
        shutil.copy2(ROOT / filename, source / filename)
    for folder in ("quant_lab", ".streamlit", "docs", "assets"):
        shutil.copytree(ROOT / folder, source / folder,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    app = source / "app.py"
    fixture = ROOT / "tools" / "performance_fixture.py"
    body = app.read_text(encoding="utf-8")
    lines = body.splitlines(keepends=True)
    tree = ast.parse(body)
    position = tree.body[0].end_lineno if ast.get_docstring(tree) else 0
    lines.insert(position, f"import runpy\nrunpy.run_path({str(fixture)!r})\n")
    app.write_text("".join(lines), encoding="utf-8")
    launcher = source / "desktop_launcher.py"
    # __future__ must remain first; set the test AppId immediately after it.
    code = launcher.read_text(encoding="utf-8")
    marker = "from __future__ import annotations"
    code = code.replace(marker, marker + f"\nimport ctypes\nctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('QuantLab.Validation.{directory.name}')", 1)
    launcher.write_text(code, encoding="utf-8")
    probe = directory / "probe.json"
    environment = {**os.environ, "QUANT_LAB_DATA_DIR": str(directory / "user"),
        "QUANT_LAB_CREDENTIAL_TARGET": "QuantLab/Validation/" + uuid4().hex,
        "QUANT_LAB_GUI_PROBE": "1", "QUANT_LAB_GUI_TEST_SECONDS": "600",
        "QUANT_LAB_TEST_IO_DELAY": str(args.io_delay),
        "QUANT_LAB_TEST_ROWS": "252" if args.visual else "2520",
        "QUANT_LAB_TEST_EVENTS": "1" if args.diagnose_events else "0",
        "QUANT_LAB_TEST_US_SOURCE": "1" if args.us_research else "0",
        "QUANT_LAB_TEST_COMPARISON": "1" if args.comparison else "0",
        "QUANT_LAB_SMOKE_RESULT": str(probe), "PYTHONPATH": str(source)}
    if args.legacy_theme:
        profile = directory / "user" / ".streamlit" / "config.toml"
        profile.parent.mkdir(parents=True)
        profile.write_text('[theme]\nbase="dark"\nprimaryColor="#24D6A0"\nbackgroundColor="#090D16"\n', encoding="utf-8")
    report = {"label": args.label, "synthetic": True, "source_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
        "platform": platform.platform(), "processor": platform.processor(),
        "logical_cpus": os.cpu_count(), "viewport": {"width": 1366, "height": 768},
        "data_rows": 252 if args.visual else 2520, "fixture_revision": "ohlc-v3-symbol-seeds", "measurements": {}, "errors": [],
        "synthetic_io_delay_seconds": args.io_delay,
        "legacy_theme_profile": args.legacy_theme,
        "warm_up_cycles": 2,
        "scope": "actual source desktop WebView2; synthetic data; not a real-provider or installed-build measurement"}
    child = None
    try:
        with (directory / "parent.log").open("w", encoding="utf-8") as log:
            started = time.perf_counter()
            child = subprocess.Popen([sys.executable, str(launcher)], cwd=source, env=environment,
                stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic() + 55
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise RuntimeError("desktop exited before ready; see parent.log")
                if probe.exists():
                    payload = json.loads(probe.read_text(encoding="utf-8"))
                    if payload.get("debug_port"):
                        break
                time.sleep(.1)
            else:
                raise TimeoutError("desktop probe unavailable")
            with sync_playwright() as playwright:
                deadline = time.monotonic() + 25
                while True:
                    try:
                        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{payload['debug_port']}", timeout=2000)
                        break
                    except Exception:
                        if time.monotonic() > deadline:
                            raise
                        time.sleep(.2)
                page = browser.contexts[0].pages[0]
                with capture_failure(page, directory):
                    page.on("pageerror", lambda error: report["errors"].append(str(error)))
                    page.get_by_text("市场数据实验室", exact=True).wait_for(timeout=45000)
                    settle(page)
                    if args.viewport:
                        width, height = (int(value) for value in args.viewport.split("x"))
                        page.set_viewport_size({"width": width, "height": height})
                        settle(page)
                    report["viewport"] = page.evaluate("({width:innerWidth,height:innerHeight})")
                    report["startup_ms"] = round((time.perf_counter()-started)*1000, 1)
                    assert page.url.startswith("http://127.0.0.1:")
                    assert page.title() == "Quant Lab CN/HK"
                    if args.comparison:
                        page.wait_for_timeout(500)
                        settle(page)
                        page.get_by_text("工作区预设",exact=True).click()
                        chooser=page.get_by_role("combobox",name="选择工作区预设",exact=True)
                        chooser.click();chooser.fill("多股票比较")
                        chooser.press("Enter")
                        page.get_by_role("button",name="应用预设",exact=True).click()
                        page.get_by_role("heading",name="多股票比较",exact=True).wait_for()
                        settle(page)
                        assert not page.locator('.st-key-manual_side_panel').count()
                        codes=",".join(f"6005{index:02}" for index in range(10))
                        page.get_by_label("比较股票代码（2–10只，逗号分隔）",exact=True).fill(codes)
                        date_node=page.get_by_label("比较开始日期",exact=True)
                        digits=re.findall(r"\d+",date_node.inner_text())
                        end_digits=re.findall(r"\d+",page.get_by_label("比较结束日期",exact=True).inner_text())
                        year=date_node.get_by_role("spinbutton").first
                        for _ in range(int(digits[0])-(int(end_digits[0])-10)):
                            year.press("ArrowDown")
                        year.press("Tab")
                        page.keyboard.press("Escape")
                        page.get_by_role("button",name="加载比较",exact=True).click()
                        page.get_by_role("heading",name="风险收益对比 · 共同覆盖区间",exact=True).wait_for(timeout=90000)
                        settle(page)
                        report["ten_stock_comparison"]=True
                        report["comparison_requested_start"]=date_node.inner_text()
                        page.get_by_test_id("stMain").evaluate("element=>{element.scrollTop=0}")
                        page.screenshot(path=str(directory/"comparison.png"))
                        page.get_by_text("进入现金持仓组合研究",exact=True).click()
                        page.get_by_role("button",name="运行现金持仓组合",exact=True).click()
                        page.get_by_text("等权是同成本基准",exact=False).wait_for(timeout=90000)
                        settle(page)
                        report["cash_portfolio_completed"]=True
                        page.screenshot(path=str(directory/"cash-portfolio.png"))
                        before_watch_tables=page.get_by_test_id("stDataFrame").count()
                        page.get_by_text("显示观察列表",exact=True).click()
                        assert page.get_by_role("switch",name="显示观察列表",exact=True).is_checked()
                        page.get_by_role("heading",name="自选股 · 最近历史日线收盘参考",exact=True).wait_for()
                        page.wait_for_function("count=>document.querySelectorAll('[data-testid=stDataFrame]').length>count",arg=before_watch_tables,timeout=30000)
                        settle(page)
                        page.screenshot(path=str(directory/"watchlist.png"))
                        report["watch_quality_visible"]=True
                        if not page.get_by_role("button",name="保存当前",exact=True).is_visible():
                            page.get_by_text("工作区预设",exact=True).click()
                        page.get_by_role("button",name="保存当前",exact=True).click()
                        settle(page)
                        report["workspace_saved"]=True
                        page.get_by_test_id("stSidebar").get_by_text("市场数据",exact=True).click()
                        settle(page)
                    if args.us_research:
                        page.get_by_test_id("stSidebar").get_by_text("美股研究",exact=True).click()
                        page.get_by_role("heading",name="美股研究",exact=True).wait_for()
                        settle(page)
                        assert page.get_by_text("以下为平台生成的固定教学样本，非真实美股行情。它用来核对拆股、分红应收/支付和结算现金。",exact=True).is_visible()
                        page.get_by_role("button",name="运行美元教学研究",exact=True).click()
                        page.get_by_text("教学策略累计收益",exact=True).wait_for(timeout=60000)
                        page.get_by_role("button",name="导出可复算美元教学实验",exact=True).wait_for()
                        settle(page)
                        page.screenshot(path=str(directory/"us-research.png"))
                        report["us_teaching_calculation"]=True
                        page.get_by_text("免费来源状态",exact=True).click()
                        settle(page)
                        assert page.get_by_role("button",name="运行真实美股回测",exact=True).is_disabled()
                        assert not page.get_by_text("教学策略累计收益",exact=True).count()
                        page.get_by_role("button",name="核验免费日线覆盖",exact=True).click()
                        page.get_by_text("隔离验收模拟上游超时；没有有效真实数据，未替换为教学行情。",exact=True).wait_for(timeout=30000)
                        settle(page)
                        page.screenshot(path=str(directory/"us-source-gate.png"))
                        report["us_live_gate_closed"]=True
                        report["us_source_failure_no_fallback"]=True
                        page.get_by_text("离线教学样本",exact=True).click()
                        page.get_by_text("教学策略累计收益",exact=True).wait_for()
                        settle(page)
                        report["us_teaching_state_restored"]=True
                        page.get_by_test_id("stSidebar").get_by_text("市场数据",exact=True).click()
                        settle(page)
                    if args.history_quality:
                        preset = page.get_by_role("combobox", name="快捷历史区间", exact=True)
                        preset.click()
                        preset.fill("10 年")
                        page.get_by_role("option", name="10 年", exact=True).click()
                        settle(page)
                        visible_date = "element => element.value || element.querySelector('input')?.value || element.innerText"
                        start_text = page.get_by_label("开始日期", exact=True).evaluate(visible_date)
                        end_text = page.get_by_label("结束日期", exact=True).evaluate(visible_date)
                        start_parts, end_parts = re.findall(r"\d+", start_text), re.findall(r"\d+", end_text)
                        assert len(start_parts) == len(end_parts) == 3
                        start_value, end_value = "-".join(start_parts), "-".join(end_parts)
                        assert int(start_value[:4]) == int(end_value[:4])-10
                        report["ten_year_preset"] = {"start": start_value, "end": end_value}
                    radio_markup = page.get_by_test_id("stSidebar").get_by_role("radio", name="市场数据", exact=True).evaluate("element => element.parentElement.parentElement.outerHTML")
                    (directory / "radio-control.html").write_text(radio_markup, encoding="utf-8")
                    page.get_by_role("button", name="使用手册", exact=True).click()
                    page.locator(".st-key-manual_side_panel").wait_for(state="hidden")
                    settle(page)
                    # The acceptance target is warm interaction latency. Keep
                    # font/widget initialization out of the timed sample.
                    for _ in range(2):
                        for destination in ("Quant Academy", "市场数据"):
                            page.get_by_test_id("stSidebar").get_by_text(destination, exact=True).click()
                            settle(page)
                    values = []
                    for i in range(args.repetitions):
                        name = "Quant Academy" if i % 2 == 0 else "市场数据"
                        before = time.perf_counter()
                        page.get_by_test_id("stSidebar").get_by_text(name, exact=True).click()
                        expected = "Quant Academy" if name == "Quant Academy" else "市场数据实验室"
                        page.get_by_role("heading", name=expected, exact=True).wait_for()
                        settle(page)
                        values.append((time.perf_counter()-before)*1000)
                    report["measurements"]["page_switch"] = summary(values)
                    page.get_by_test_id("stSidebar").get_by_text("Quant Academy", exact=True).click()
                    settle(page)
                    for _ in range(2):
                        lesson = page.get_by_role("combobox", name="选择课程", exact=True)
                        lesson.click()
                        lesson.press("ArrowDown")
                        lesson.press("Enter")
                        settle(page)
                        lesson.click()
                        lesson.press("ArrowUp")
                        lesson.press("Enter")
                        settle(page)
                    values = []
                    for i in range(args.repetitions):
                        before = time.perf_counter()
                        lesson = page.get_by_role("combobox", name="选择课程", exact=True)
                        lesson.click()
                        lesson.press("ArrowDown" if i % 2 == 0 else "ArrowUp")
                        lesson.press("Enter")
                        settle(page)
                        values.append((time.perf_counter()-before)*1000)
                    report["measurements"]["lesson_switch"] = summary(values)
                    values = []
                    for i in range(args.repetitions):
                        before = time.perf_counter()
                        slider = page.get_by_role("slider").first
                        slider.press("ArrowRight" if i % 2 == 0 else "ArrowLeft")
                        settle(page)
                        values.append((time.perf_counter()-before)*1000)
                    report["measurements"]["lesson_parameter"] = summary(values)
                    values = []
                    for i in range(args.repetitions):
                        before = time.perf_counter()
                        page.get_by_role("button", name="使用手册", exact=True).click()
                        page.locator(".st-key-manual_side_panel").wait_for(state="visible" if i % 2 == 0 else "hidden")
                        settle(page)
                        values.append((time.perf_counter()-before)*1000)
                    report["measurements"]["manual_toggle"] = summary(values)
                    if page.locator('.st-key-manual_side_panel').is_visible():
                        page.get_by_role("button", name="使用手册", exact=True).click()
                        page.locator('.st-key-manual_side_panel').wait_for(state='hidden')
                    if args.visual:
                        lesson = page.get_by_role("combobox", name="选择课程", exact=True)
                        lesson.click()
                        lesson.fill("最大回撤")
                        page.get_by_role("option", name="最大回撤", exact=True).click()
                        settle(page)
                        page.get_by_text("知识解释：最大回撤", exact=True).click()
                        page.get_by_role("button", name="向 AI 追问", exact=True).wait_for()
                        page.get_by_text("知识解释：最大回撤", exact=True).click()
                        page.get_by_role("button", name="向 AI 追问", exact=True).wait_for(state='detached')
                        report["lazy_explanation_open_close"] = True
                    page.mouse.move(5, 55)
                    page.get_by_test_id("stMain").evaluate("element => {element.scrollTop=0;}")
                    page.wait_for_timeout(100)
                    page.screenshot(path=str(directory / "academy.png"))
                    page.get_by_test_id("stSidebar").get_by_text("市场数据", exact=True).click()
                    settle(page)
                    before = time.perf_counter()
                    page.get_by_role("button", name="加载真实历史日线", exact=True).click()
                    if args.functional and args.io_delay:
                        page.get_by_test_id("stSidebar").get_by_text("Quant Academy", exact=True).click()
                        page.get_by_role("heading", name="Quant Academy", exact=True).wait_for()
                        report["page_switch_during_io"] = True
                        page.get_by_test_id("stSidebar").get_by_text("市场数据", exact=True).click()
                    page.get_by_text("已加载模拟/教学数据", exact=False).first.wait_for(timeout=45000)
                    settle(page)
                    report["measurements"][f"load_{report['data_rows']}_synthetic_rows_ms"] = round((time.perf_counter()-before)*1000, 1)
                    page.mouse.move(5, 55)
                    page.get_by_test_id("stMain").evaluate("element => {element.scrollTop=0;}")
                    page.wait_for_timeout(100)
                    report["layout"] = page.evaluate("""() => Object.fromEntries(['stSidebar','stSidebarHeader','stSidebarContent','stSidebarUserContent','stMainBlockContainer'].map(key => {const el=document.querySelector(`[data-testid=${key}]`); const style=el && getComputedStyle(el); const rect=el?.getBoundingClientRect(); return [key, el ? {x:rect.x,y:rect.y,width:rect.width,height:rect.height,padding:style.padding,font:style.fontFamily,background:style.backgroundColor}:null];}))""")
                    page.screenshot(path=str(directory / "market.png"))
                    if args.history_quality:
                        page.get_by_text("数据质量与覆盖", exact=True).click()
                        page.get_by_role("button", name="导出质量报告", exact=True).wait_for()
                        assert page.get_by_text("请求区间", exact=True).count() >= 1
                        assert page.get_by_text("平台生成的固定教学样本，可本地留存；不是市场行情。", exact=True).is_visible()
                        report["quality_panel"] = True
                        report["quality_retention_status"] = True
                        page.screenshot(path=str(directory / "history-quality.png"))
                        page.get_by_text("数据质量与覆盖", exact=True).click()
                    if args.visual:
                        radio_markup = page.get_by_test_id("stSidebar").get_by_role("radio", name="市场数据", exact=True).evaluate("element => element.parentElement.parentElement.outerHTML")
                        (directory / "radio-control.html").write_text(radio_markup, encoding="utf-8")
                        page.get_by_role("button", name="使用手册", exact=True).click()
                        settle(page)
                        page.mouse.move(5, 55)
                        page.get_by_test_id("stMain").evaluate("element => {element.scrollTop=0;}")
                        page.wait_for_timeout(300)
                        page.screenshot(path=str(directory / "market-with-manual.png"))
                        page.get_by_role("button", name="DeepSeek 助手", exact=True).click()
                        settle(page)
                        page.get_by_role("button", name="研究笔记", exact=True).click()
                        settle(page)
                        root = page.locator("html")
                        compact = root.get_attribute("data-ql-dock-compact") == "true"
                        report["compact_dock"] = compact
                        if compact:
                            assert page.locator('.st-key-notes_side_panel').is_visible()
                            assert not page.locator('.st-key-manual_side_panel').is_visible()
                            assert not page.locator('.st-key-deepseek_side_panel').is_visible()
                            assert page.get_by_test_id("stMain").bounding_box()["width"] >= 550
                        else:
                            assert all(page.locator(f'.st-key-{kind}_side_panel').is_visible() for kind in ('manual','deepseek','notes'))
                        note = page.locator('.st-key-notes_side_panel')
                        note.get_by_label("笔记标题", exact=True).fill("版式验收草稿")
                        note.get_by_label("笔记标题", exact=True).press("Tab")
                        settle(page)
                        note.get_by_label("Markdown 正文", exact=True).fill("这是一段隔离资料库中的桌面布局验收文字。")
                        note.get_by_label("Markdown 正文", exact=True).press("Tab")
                        settle(page)
                        assert note.get_by_label("笔记标题", exact=True).input_value() == "版式验收草稿"
                        report["notes_editable_in_dock"] = True
                        page.mouse.move(5, 55)
                        page.wait_for_timeout(300)
                        page.screenshot(path=str(directory / "dock-layout.png"))
                        page.get_by_role("button", name="使用手册", exact=True).click()
                        settle(page)
                        assert page.locator('.st-key-manual_side_panel').is_visible()
                        report["dock_switch"] = True
                        # Close all via their header controls, whose meaning stays
                        # unambiguous in both compact and side-by-side layouts.
                        for kind in ('manual','deepseek','notes'):
                            panel = page.locator(f'.st-key-{kind}_side_panel')
                            if not panel.is_visible():
                                label = {'manual':'使用手册','deepseek':'DeepSeek 助手','notes':'研究笔记'}[kind]
                                page.get_by_role("button", name=label, exact=True).click()
                                settle(page)
                            page.locator(f'.st-key-{kind}_panel_close').get_by_role('button').click()
                            page.locator(f'.st-key-{kind}_side_panel').wait_for(state='detached', timeout=10000)
                            settle(page)
                    if args.functional:
                        page.get_by_test_id("stSidebar").get_by_text("历史回测", exact=True).click()
                        settle(page)
                        page.get_by_role("button", name="运行历史回测", exact=True).click()
                        page.get_by_test_id("stSidebar").get_by_text("Quant Academy", exact=True).click()
                        page.get_by_role("heading", name="Quant Academy", exact=True).wait_for()
                        report["page_switch_during_cpu"] = True
                        page.get_by_test_id("stSidebar").get_by_text("历史回测", exact=True).click()
                        page.get_by_text("策略累计收益", exact=True).wait_for(timeout=60000)
                        settle(page)
                        report["actual_cpu_backtest_completed"] = True
                        if args.history_quality:
                            page.get_by_text("保存本次实验与研究笔记", exact=True).click()
                            assert page.get_by_role("button", name="保存实验", exact=True).is_enabled()
                            page.get_by_role("button", name="保存实验", exact=True).click()
                            page.get_by_text("实验 #1 已保存。可到“研究笔记”导出报告。", exact=True).wait_for()
                            report["teaching_archive_saved"] = True
                        page.screenshot(path=str(directory / "backtest.png"))
                        page.get_by_role("button", name="使用手册", exact=True).click()
                        panel = page.locator(".st-key-manual_side_panel")
                        panel.wait_for()
                        handle = panel.locator('.ql-resize-handle')
                        box, original_width = handle.bounding_box(), panel.bounding_box()["width"]
                        page.mouse.move(box["x"]+3, box["y"]+80)
                        page.mouse.down()
                        page.mouse.move(box["x"]-60, box["y"]+80, steps=12)
                        page.mouse.up()
                        page.wait_for_timeout(250)
                        assert panel.bounding_box()["width"] > original_width + 30
                        report["panel_drag"] = True
                        panel.get_by_role("button", name="⛶", exact=True).click()
                        settle(page)
                        page.locator('.ql-maximized-panel').wait_for(state='attached', timeout=10000)
                        settle(page)
                        if args.visual:
                            page.wait_for_timeout(100)
                            if args.diagnose_events:
                                debug = page.locator('.st-key-deepseek_panel_toggle button').evaluate("button => ({dataset:{...button.dataset},disabled:button.disabled,text:button.textContent,appState:document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')})")
                                (directory / "max-button-before.json").write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8")
                                page.evaluate("""() => {window.__qlClickEvents=[]; for(const type of ['pointerdown','pointerup','pointercancel','click']) window.addEventListener(type,event=>{const button=event.target.closest?.('button');const box=button?.getBoundingClientRect();const item={type,text:button?.textContent||event.target.tagName,targetClass:event.target.className,x:event.clientX,y:event.clientY,rect:box&&{x:box.x,y:box.y,width:box.width},dataset:button&&{...button.dataset}};window.__qlClickEvents.push(item);queueMicrotask(()=>{item.prevented=event.defaultPrevented;item.after=button&&{...button.dataset};}); if(button)requestAnimationFrame(()=>{const next=button.getBoundingClientRect();item.nextRect={x:next.x,y:next.y,width:next.width}; item.connected=button.isConnected;});},true);} """)
                            page.get_by_role("button", name="DeepSeek 助手", exact=True).click()
                            if args.diagnose_events:
                                page.wait_for_timeout(200)
                                (directory / "max-click-events.json").write_text(json.dumps(page.evaluate("window.__qlClickEvents"), ensure_ascii=False, indent=2), encoding="utf-8")
                            page.locator('.st-key-deepseek_side_panel').wait_for(state='visible')
                            page.locator('.ql-maximized-panel').wait_for(state='attached')
                            settle(page)
                            page.get_by_role("button", name="使用手册", exact=True).click()
                            page.locator('.st-key-manual_side_panel').wait_for(state='visible')
                            report["maximized_panel_switch"] = True
                        panel.get_by_role("button", name="⛶", exact=True).click()
                        settle(page)
                        page.get_by_role("button", name="使用手册", exact=True).click()
                        settle(page)
                        page.get_by_role("button", name="运行历史回测", exact=True).click()
                        page.locator('.st-key-cancel_job_backtest').get_by_role("button").wait_for(timeout=10000)
                        page.locator('.st-key-cancel_job_backtest').get_by_role("button").click()
                        settle(page)
                        report["cpu_cancel"] = True
                    assert page.get_by_test_id("stException").count() == 0
                    try:
                        page.evaluate("window.pywebview.api.close()")
                    except Exception as error:
                        if "closed" not in str(error).lower():
                            raise
                    child.wait(timeout=20)
        final = json.loads(probe.read_text(encoding="utf-8"))
        report["child_stopped"] = final.get("child_stopped", False)
        report["exit_code"] = child.returncode
        (directory / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"report": str(directory / "result.json"), **report}, ensure_ascii=False))
        assert report["child_stopped"] and child.returncode == 0
    except Exception as error:
        report["failure_type"] = type(error).__name__
        try:
            page.screenshot(path=str(directory / "failure.png"))
            (directory / "failure-dom.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
        except Exception:
            pass
        (directory / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"failed_report": str(directory / "result.json")}, ensure_ascii=False))
        raise
    finally:
        if child is not None and child.poll() is None:
            subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()


if __name__ == "__main__":
    main()
