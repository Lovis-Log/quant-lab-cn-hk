"""Measure actual WebView2 DOM interactions in an isolated source copy.

Synthetic data is injected ONLY into the copy. No credentials, paid APIs, or
production user files are read. Reports live in the ignored .tools directory.
"""

from __future__ import annotations

import argparse
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
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def summary(values):
    ordered = sorted(values)
    return {"samples": len(values), "median_ms": round(ordered[len(ordered)//2], 1),
            "p95_ms": round(ordered[math.ceil(.95*len(ordered))-1], 1),
            "max_ms": round(ordered[-1], 1)}


def settle(page):
    page.wait_for_timeout(50)
    page.wait_for_function("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'", timeout=45000)


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--functional", action="store_true")
    parser.add_argument("--viewport", choices=("1366x768", "1920x1080"))
    parser.add_argument("--io-delay", type=float, default=0)
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
    app.write_bytes(f"import runpy\nrunpy.run_path({str(fixture)!r})\n".encode() + app.read_bytes())
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
        "QUANT_LAB_SMOKE_RESULT": str(probe), "PYTHONPATH": str(source)}
    report = {"label": args.label, "synthetic": True, "source_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)),
        "platform": platform.platform(), "processor": platform.processor(),
        "logical_cpus": os.cpu_count(), "viewport": {"width": 1366, "height": 768},
        "data_rows": 2520, "measurements": {}, "errors": [],
        "synthetic_io_delay_seconds": args.io_delay,
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
                page.get_by_role("button", name="使用手册", exact=True).click()
                page.locator(".st-key-manual_side_panel").wait_for(state="hidden")
                settle(page)
                values = []
                for i in range(args.repetitions):
                    name = "Quant Academy" if i % 2 == 0 else "市场数据"
                    before = time.perf_counter()
                    page.get_by_test_id("stSidebar").get_by_text(name, exact=True).click()
                    expected = "Quant Academy · 金融数学实验室" if name == "Quant Academy" else "市场数据实验室"
                    page.get_by_text(expected, exact=True).wait_for()
                    settle(page)
                    values.append((time.perf_counter()-before)*1000)
                report["measurements"]["page_switch"] = summary(values)
                page.get_by_test_id("stSidebar").get_by_text("Quant Academy", exact=True).click()
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
                page.screenshot(path=str(directory / "academy.png"))
                page.get_by_test_id("stSidebar").get_by_text("市场数据", exact=True).click()
                settle(page)
                before = time.perf_counter()
                page.get_by_role("button", name="加载真实历史日线", exact=True).click()
                if args.functional and args.io_delay:
                    page.get_by_test_id("stSidebar").get_by_text("Quant Academy", exact=True).click()
                    page.get_by_text("Quant Academy · 金融数学实验室", exact=True).wait_for()
                    report["page_switch_during_io"] = True
                    page.get_by_test_id("stSidebar").get_by_text("市场数据", exact=True).click()
                page.get_by_text("已加载模拟/教学数据", exact=False).wait_for(timeout=45000)
                settle(page)
                report["measurements"]["load_2520_synthetic_rows_ms"] = round((time.perf_counter()-before)*1000, 1)
                page.screenshot(path=str(directory / "market.png"))
                if args.functional:
                    page.get_by_test_id("stSidebar").get_by_text("历史回测", exact=True).click()
                    settle(page)
                    page.get_by_role("button", name="运行历史回测", exact=True).click()
                    page.get_by_test_id("stSidebar").get_by_text("Quant Academy", exact=True).click()
                    page.get_by_text("Quant Academy · 金融数学实验室", exact=True).wait_for()
                    report["page_switch_during_cpu"] = True
                    page.get_by_test_id("stSidebar").get_by_text("历史回测", exact=True).click()
                    page.get_by_text("策略累计收益", exact=True).wait_for(timeout=60000)
                    settle(page)
                    report["actual_cpu_backtest_completed"] = True
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
                    assert page.locator('.ql-maximized-panel').count() == 1
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
