"""Interact with the actual WebView2 window through its isolated CDP probe.

No paid calls. --mock-ai is permitted only for an installed copy under .tools;
its app entry is temporarily instrumented with a mock transport and restored.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


def main():
    from playwright.sync_api import sync_playwright, Error
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--mock-ai", action="store_true")
    args = parser.parse_args()
    directory = (args.data_dir or ROOT / ".tools" / ("desktop-validation-" + uuid4().hex)).resolve()
    directory.relative_to((ROOT / ".tools").resolve())
    directory.mkdir(parents=True, exist_ok=True)
    app_file, original = None, None
    if args.mock_ai:
        if not args.exe:
            raise ValueError("Mock GUI mode requires an isolated installed EXE.")
        exe = args.exe.resolve()
        exe.relative_to((ROOT / ".tools").resolve())
        app_file = exe.parent / "_internal" / "app.py"
        original = app_file.read_text(encoding="utf-8")
        fixture = str(ROOT / "tools" / "gui_api_fixture.py")
        app_file.write_text(f"import runpy\nrunpy.run_path({fixture!r})\n" + original, encoding="utf-8")
    probe_file = directory / "probe.json"
    env = {**os.environ, "QUANT_LAB_DATA_DIR": str(directory),
           "QUANT_LAB_GUI_TEST_SECONDS": "120", "QUANT_LAB_GUI_PROBE": "1",
           "QUANT_LAB_SMOKE_RESULT": str(probe_file)}
    command = [str(args.exe.resolve())] if args.exe else [str(ROOT/".venv/Scripts/python.exe"), str(ROOT/"desktop_launcher.py")]
    child = None
    summary = {"mock_api": args.mock_ai, "data_dir": str(directory)}
    try:
        with (directory/"parent.log").open("w", encoding="utf-8") as log:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic()+45
            while time.monotonic()<deadline:
                if child.poll() is not None:
                    raise RuntimeError("Desktop exited before probe became ready.")
                if probe_file.exists():
                    try:
                        probe = json.loads(probe_file.read_text(encoding="utf-8"))
                        if probe.get("debug_port"):
                            break
                    except ValueError:
                        pass
                time.sleep(.2)
            else:
                raise TimeoutError("No desktop probe endpoint.")
            with sync_playwright() as playwright:
                deadline = time.monotonic()+25
                while True:
                    try:
                        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{probe['debug_port']}", timeout=3000)
                        break
                    except Exception:
                        if time.monotonic()>deadline:
                            raise
                        time.sleep(.3)
                page = browser.contexts[0].pages[0]
                page.get_by_text("市场数据实验室", exact=True).wait_for(timeout=30000)
                summary["actual_webview_dom_loaded"] = True
                pause = page.get_by_role("button", name="暂停自动刷新", exact=True)
                if pause.count():
                    pause.click()
                page.get_by_text("DeepSeek AI 助手", exact=True).click()
                key = page.get_by_label("DeepSeek API Key", exact=True)
                assert key.get_attribute("type") == "password"
                assert key.input_value() == ""  # Session-only keys must not return after restart.
                key.fill("sk-isolated-ui-dummy-key")
                key.press("Tab")
                if args.mock_ai:
                    page.get_by_role("button", name="测试连接", exact=True).click()
                    page.get_by_text("连接成功；已取得官方可用模型列表。", exact=True).wait_for(timeout=10000)
                    page.get_by_role("combobox", name="DeepSeek 模型", exact=True).click()
                    page.get_by_role("option", name="模拟模型 B · mock-b", exact=True).click()
                    page.get_by_label("问题（确认后发送）", exact=True).fill("解释最大回撤并给出手算例子")
                    page.get_by_role("button", name="发送到 DeepSeek", exact=True).click()
                    page.get_by_text("实际模型：mock-b-actual", exact=True).wait_for(timeout=20000)
                    assert "STREAM_DONE" in page.inner_text("body")
                    page.get_by_role("button", name="保存选定回答到学习笔记", exact=True).click()
                    page.get_by_text("学习笔记 #", exact=False).wait_for(timeout=10000)
                    summary.update({"model_switch": True, "streamed_answer": True, "answer_saved": True})
                    page.get_by_role("button", name="清除密钥", exact=True).click()
                    assert page.get_by_label("DeepSeek API Key", exact=True).input_value() == ""
                    summary["key_cleared"] = True
                else:
                    manual = page.get_by_label("手动模型 ID", exact=True)
                    manual.fill("manual-model-validation")
                    manual.press("Tab")
                    summary["password_and_model_controls"] = True
                page.screenshot(path=str(directory/"webview.png"), full_page=True)
                assert not page.locator('[data-testid="stException"]').count()
                try:
                    page.evaluate("() => { window.pywebview.api.close(); return true; }")
                except Error as exc:
                    if "closed" not in str(exc).lower():
                        raise
                child.wait(timeout=15)
        probe = json.loads(probe_file.read_text(encoding="utf-8"))
        assert child.returncode == 0 and probe.get("webview_loaded") and probe.get("child_stopped")
        summary.update({"loaded_event": True, "child_stopped": True, "exit_code": child.returncode})
        (directory/"gui-result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False))
    finally:
        if child is not None and child.poll() is None:
            # Only this freshly created process tree; never a process-name kill.
            subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
            child.wait(timeout=10)
        if app_file is not None and original is not None:
            app_file.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    main()
