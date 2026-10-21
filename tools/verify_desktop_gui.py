"""Interact with the actual WebView2 window through its isolated CDP probe.

No paid calls. --mock-ai is permitted only for an installed copy under .tools;
its app entry is temporarily instrumented with a mock transport and restored.
"""

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def settle(page):
    page.wait_for_timeout(250)
    page.wait_for_function("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'", timeout=45000)


def main():
    from playwright.sync_api import sync_playwright, Error, expect
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--mock-ai", action="store_true")
    parser.add_argument("--research-fixes", action="store_true")
    parser.add_argument("--learning-center", action="store_true")
    parser.add_argument("--resume-learning", action="store_true")
    args = parser.parse_args()
    directory = (args.data_dir or ROOT / ".tools" / ("desktop-validation-" + uuid4().hex)).resolve()
    directory.relative_to((ROOT / ".tools").resolve())
    directory.mkdir(parents=True, exist_ok=True)
    app_file, original = None, None
    vault_target = "QuantLabCNHK/Validation/" + uuid4().hex
    dummy_key = "sk-validation-" + uuid4().hex
    from quant_lab.credentials import remember_key, clear_key
    remember_key(dummy_key, target=vault_target)
    if args.mock_ai:
        if not args.exe:
            raise ValueError("Mock GUI mode requires an isolated installed EXE.")
        exe = args.exe.resolve()
        exe.relative_to((ROOT / ".tools").resolve())
        app_file = exe.parent / "_internal" / "app.py"
        original = app_file.read_bytes()
        fixture = str(ROOT / "tools" / "gui_api_fixture.py")
        app_file.write_bytes(f"import runpy\nrunpy.run_path({fixture!r})\n".encode("utf-8") + original)
    # The user data directory is reused to test restarts; the probe file must
    # belong to this launch, not the previous window's now-closed CDP endpoint.
    probe_file = directory / ("probe-" + uuid4().hex + ".json")
    env = {**os.environ, "QUANT_LAB_DATA_DIR": str(directory),
           "QUANT_LAB_GUI_TEST_SECONDS": "240", "QUANT_LAB_GUI_PROBE": "1",
           "QUANT_LAB_CREDENTIAL_TARGET": vault_target,
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
                console_errors = []
                page.on("console", lambda message: console_errors.append(message.text)
                        if message.type == "error" else None)
                page.get_by_text("市场数据实验室", exact=True).wait_for(timeout=30000)
                summary["actual_webview_dom_loaded"] = True
                welcome = page.get_by_role("button", name="跳过首次引导", exact=True)
                if welcome.count():
                    welcome.click()
                    settle(page)
                topbar = page.locator(".st-key-global_topbar")
                expect(topbar).to_be_visible(timeout=10000)
                dock_toggle = page.get_by_role("button", name="▥", exact=True)
                expect(dock_toggle).to_be_visible(timeout=10000)
                viewport_width = page.evaluate("window.innerWidth")
                topbar_box = topbar.bounding_box()
                assert topbar_box and topbar_box["x"] <= 1
                assert abs((topbar_box["x"] + topbar_box["width"]) - viewport_width) <= 3
                sidebar = page.get_by_test_id("stSidebar")
                assert sidebar.get_by_text("AI 研究助手", exact=True).count() == 0
                assert sidebar.get_by_text("新手使用指引", exact=True).count() == 0
                assert sidebar.get_by_text("研究笔记", exact=True).count() == 0
                main = page.get_by_test_id("stMain")
                main_before = main.bounding_box()
                page.get_by_role("button", name="新手使用指引", exact=True).click()
                settle(page)
                guide_panel = page.locator(".st-key-guide_side_panel")
                expect(guide_panel).to_be_visible(timeout=10000)
                page.get_by_role("button", name="DeepSeek 助手", exact=True).click()
                settle(page)
                panel = page.locator(".st-key-deepseek_side_panel")
                expect(panel).to_be_visible(timeout=10000)
                assert page.get_by_role("dialog").count() == 0
                page.get_by_role("button", name="⚙", exact=True).click()
                settle(page)
                settings_panel = page.locator(".st-key-settings_panel")
                expect(settings_panel).to_be_visible(timeout=10000)
                settings_panel.get_by_role("tab", name="DeepSeek", exact=True).click()
                settle(page)
                expect(settings_panel.get_by_label("DeepSeek API Key", exact=True)).to_have_value(dummy_key)
                settings_panel.get_by_role("button", name="×", exact=True).click()
                settle(page)
                guide_box = guide_panel.bounding_box()
                box = panel.bounding_box()
                main_after = main.bounding_box()
                workspace_after = page.get_by_test_id("stMainBlockContainer").bounding_box()
                page.screenshot(path=str(directory/"dual-side-panels.png"), full_page=False)
                assert box and abs((box["x"] + box["width"]) - viewport_width) <= 3, {
                    "panel_box": box, "viewport_width": viewport_width,
                }
                assert guide_box and guide_box["x"] < box["x"]
                padding_right = main.evaluate("element => getComputedStyle(element).paddingRight")
                assert main_before and main_after and workspace_after
                assert float(padding_right.removesuffix("px")) >= box["width"] + guide_box["width"] - 3, {
                    "main_before": main_before, "main_after": main_after,
                    "workspace_after": workspace_after, "panel_box": box, "guide_box": guide_box,
                    "padding_right": padding_right,
                }
                resize = panel.locator('.ql-resize-handle[data-panel="deepseek"]')
                assert resize.get_attribute("data-bound") == "1"
                resize_box = resize.bounding_box()
                assert resize_box
                hit_target = page.evaluate(
                    "([x,y]) => { const e=document.elementFromPoint(x,y); return {tag:e?.tagName, cls:e?.className, panel:e?.getAttribute('data-panel')}; }",
                    [resize_box["x"] + 3, resize_box["y"] + 100],
                )
                page.mouse.move(resize_box["x"] + 3, resize_box["y"] + 100)
                page.mouse.down()
                page.mouse.move(resize_box["x"] - 45, resize_box["y"] + 100, steps=5)
                page.mouse.up()
                page.wait_for_timeout(300)
                resized_box = panel.bounding_box()
                resize_state = page.evaluate(
                    "() => ({css:getComputedStyle(document.documentElement).getPropertyValue('--ql-deepseek-width'), stored:localStorage.getItem('quantlab.deepseek.panelWidth')})"
                )
                assert hit_target.get("panel") == "deepseek"
                assert resize_state.get("stored") == str(round(resized_box["width"]))
                assert resized_box and resized_box["width"] >= box["width"] + 35
                page.get_by_role("button", name="研究笔记", exact=True).click()
                settle(page)
                notes_panel = page.locator(".st-key-notes_side_panel")
                expect(notes_panel).to_be_visible(timeout=10000)
                notes_panel.get_by_label("笔记标题", exact=True).fill("GUI 附件笔记")
                notes_panel.get_by_label("Markdown 正文", exact=True).fill("# 图表记录\n\n本地托管附件验收。")
                png = base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Z2S8AAAAASUVORK5CYII="
                )
                notes_panel.get_by_label("添加附件", exact=True).locator('input[type="file"]').set_input_files([
                    {"name":"chart.png", "mimeType":"image/png", "buffer":png},
                    {"name":"evidence.pdf", "mimeType":"application/pdf", "buffer":b"%PDF-1.4\n%%EOF"},
                ])
                notes_panel.get_by_role("button", name="保存所选附件到草稿", exact=True).click()
                settle(page)
                page.locator(".st-key-notes_side_panel").get_by_role("button", name="插入", exact=True).click()
                settle(page)
                page.locator(".st-key-notes_side_panel").get_by_role("button", name="保存笔记", exact=True).click()
                settle(page)
                notes_panel = page.locator(".st-key-notes_side_panel")
                expect(notes_panel.get_by_role("combobox", name="选择内容", exact=True)).to_have_value(
                    "笔记 · GUI 附件笔记", timeout=10000
                )
                expect(notes_panel.get_by_role("button", name="下载 · evidence.pdf", exact=True)).to_have_count(
                    1, timeout=10000
                )
                sticky_headers = []
                for panel_name in ("guide", "deepseek", "notes"):
                    current_panel = page.locator(f".st-key-{panel_name}_side_panel")
                    current_header = current_panel.locator(f".st-key-{panel_name}_panel_header")
                    current_body = current_panel.locator(f".st-key-{panel_name}_panel_body")
                    expect(current_header).to_be_visible(timeout=10000)
                    expect(current_body).to_be_visible(timeout=10000)
                    current_body.evaluate("element => { element.scrollTop = element.scrollHeight; }")
                    page.wait_for_timeout(120)
                    panel_scroll = current_body.evaluate("element => element.scrollTop")
                    header_box = current_header.bounding_box()
                    panel_box = current_panel.bounding_box()
                    assert header_box and panel_box
                    assert abs(header_box["y"] - panel_box["y"]) <= 2, {
                        "panel": panel_name, "header_box": header_box, "panel_box": panel_box,
                    }
                    expect(current_header.get_by_role("button", name="⛶", exact=True)).to_be_visible()
                    sticky_headers.append({"panel": panel_name, "scroll_top": panel_scroll,
                                           "header_y": header_box["y"]})
                    current_body.evaluate("element => { element.scrollTop = 0; }")
                assert any(item["scroll_top"] > 0 for item in sticky_headers)

                dock_toggle.click()
                settle(page)
                expect(page.locator(".st-key-guide_side_panel")).not_to_be_visible(timeout=10000)
                expect(page.locator(".st-key-deepseek_side_panel")).not_to_be_visible(timeout=10000)
                expect(page.locator(".st-key-notes_side_panel")).not_to_be_visible(timeout=10000)
                page.wait_for_function("""() => {
                  const main = document.querySelector('[data-testid="stMain"]');
                  return main && parseFloat(getComputedStyle(main).paddingRight) < 1;
                }""", timeout=3000)
                hidden_padding = main.evaluate("element => getComputedStyle(element).paddingRight")
                assert float(hidden_padding.removesuffix("px")) < 1
                dock_toggle.click()
                settle(page)
                expect(page.locator(".st-key-guide_side_panel")).to_be_visible(timeout=10000)
                expect(page.locator(".st-key-deepseek_side_panel")).to_be_visible(timeout=10000)
                expect(page.locator(".st-key-notes_side_panel")).to_be_visible(timeout=10000)
                notes_panel = page.locator(".st-key-notes_side_panel")
                page.screenshot(path=str(directory/"triple-side-panels.png"), full_page=False)
                guide_button = page.get_by_role("button", name="新手使用指引", exact=True)
                deepseek_button = page.get_by_role("button", name="DeepSeek 助手", exact=True)
                notes_button = page.get_by_role("button", name="研究笔记", exact=True)
                guide_button_box = guide_button.bounding_box()
                deepseek_button_box = deepseek_button.bounding_box()
                assert guide_button_box and deepseek_button_box
                assert guide_button.get_attribute("data-reorder-bound") == "1"
                assert deepseek_button.get_attribute("data-reorder-bound") == "1"
                assert guide_button_box["x"] < deepseek_button_box["x"]
                page.mouse.move(
                    deepseek_button_box["x"] + deepseek_button_box["width"] / 2,
                    deepseek_button_box["y"] + deepseek_button_box["height"] / 2,
                )
                page.mouse.down()
                page.mouse.move(
                    guide_button_box["x"] + guide_button_box["width"] / 3,
                    guide_button_box["y"] + guide_button_box["height"] / 2,
                    steps=8,
                )
                page.mouse.up()
                page.wait_for_timeout(350)
                stored_order = page.evaluate("JSON.parse(localStorage.getItem('quantlab.dock.panelOrder'))")
                assert stored_order[0] == "deepseek" and set(stored_order) == {"guide","deepseek","notes"}
                guide_panel = page.locator(".st-key-guide_side_panel")
                panel = page.locator(".st-key-deepseek_side_panel")
                reordered_guide_button_box = guide_button.bounding_box()
                reordered_deepseek_button_box = deepseek_button.bounding_box()
                swapped_guide_box = guide_panel.bounding_box()
                swapped_deepseek_box = panel.bounding_box()
                assert reordered_guide_button_box and reordered_deepseek_button_box
                assert reordered_deepseek_button_box["x"] < reordered_guide_button_box["x"]
                assert swapped_guide_box and swapped_deepseek_box
                assert swapped_deepseek_box["x"] < swapped_guide_box["x"]
                page.screenshot(path=str(directory/"dual-side-panels-swapped.png"), full_page=False)
                notes_panel.get_by_role("button", name="⛶", exact=True).click()
                settle(page)
                notes_panel = page.locator(".st-key-notes_side_panel")
                maximized_box = notes_panel.bounding_box()
                assert maximized_box and maximized_box["width"] >= viewport_width - 3
                maximized_header_box = notes_panel.locator(".st-key-notes_panel_header").bounding_box()
                current_topbar_box = topbar.bounding_box()
                assert maximized_header_box and current_topbar_box
                assert abs(maximized_box["y"] - (current_topbar_box["y"] + current_topbar_box["height"])) <= 2
                assert abs(maximized_header_box["y"] - maximized_box["y"]) <= 2
                expect(topbar).to_be_visible()
                expect(dock_toggle).to_be_visible()
                assert main.evaluate("element => getComputedStyle(element).paddingRight") == "0px"
                page.keyboard.press("Escape")
                settle(page)
                expect(page.locator(".st-key-guide_side_panel")).to_be_visible(timeout=10000)
                expect(page.locator(".st-key-deepseek_side_panel")).to_be_visible(timeout=10000)
                summary.update({"global_topbar_dom": True, "topbar_pages_removed_from_sidebar": True,
                                "deepseek_global_launcher": True, "learning_global_launcher": True,
                                "notes_global_launcher": True, "triple_panels_open": True,
                                "right_dock_launcher": True, "sticky_panel_headers": sticky_headers,
                                "topbar_preserved_during_maximize": True,
                                "markdown_note_with_attachments": True,
                                "panels_reordered_by_drag": True, "panel_maximize_restore": True,
                                "panel_drag_resize": True, "workspace_resized_for_panel": True,
                                "panel_width_before": box["width"],
                                "panel_width_after": resized_box["width"],
                                "remembered_key_restored_on_start": True})
                page.locator(".st-key-notes_side_panel").get_by_role("button", name="×", exact=True).click()
                settle(page)
                guide_panel.get_by_role("button", name="×", exact=True).click()
                settle(page)
                panel = page.locator(".st-key-deepseek_side_panel")
                panel.get_by_role("button", name="×", exact=True).click()
                settle(page)
                expect(panel).not_to_be_visible(timeout=10000)
                pause = page.get_by_role("button", name="暂停自动刷新", exact=True)
                if pause.count():
                    pause.click()
                    settle(page)
                    page.get_by_role("button", name="恢复自动刷新", exact=True).wait_for(timeout=10000)
                if args.research_fixes:
                    picker = page.get_by_role("combobox", name="股票（代码 / 名称）", exact=True)
                    picker.click()
                    settle(page)
                    picker.fill("平安银行")
                    page.get_by_role("option", name="000001 · 平安银行", exact=True).click()
                    settle(page)
                    expect(page.get_by_test_id("stSidebar")).to_contain_text("当前选择：A 股 000001", timeout=15000)
                    market = page.get_by_role("combobox", name="市场", exact=True)
                    market.click()
                    market.fill("港股")
                    print({"market_options": page.get_by_role("option").all_inner_texts()}, flush=True)
                    settle(page)
                    page.get_by_role("option", name="港股", exact=True).click()
                    settle(page)
                    picker = page.get_by_role("combobox", name="股票（代码 / 名称）", exact=True)
                    picker.click()
                    settle(page)
                    picker.fill("中国移动")
                    page.get_by_role("option", name="00941 · 中国移动", exact=True).click()
                    settle(page)
                    expect(page.get_by_test_id("stSidebar")).to_contain_text("当前选择：港股 00941", timeout=15000)
                    assert page.get_by_test_id("stSidebar").get_by_role("textbox").count() == 0
                    picker.click()
                    picker.fill("HK09988")
                    settle(page)
                    page.get_by_role("option", name="Add: HK09988", exact=True).click()
                    settle(page)
                    expect(page.get_by_test_id("stSidebar")).to_contain_text("当前选择：港股 09988", timeout=15000)
                    picker.click()
                    picker.fill("NOTACODE")
                    settle(page)
                    page.get_by_role("option", name="Add: NOTACODE", exact=True).click()
                    settle(page)
                    expect(page.get_by_role("button", name="加载真实历史日线", exact=True)).to_be_disabled()
                    picker.click()
                    picker.fill("00941")
                    page.get_by_role("option", name="00941 · 中国移动", exact=True).click()
                    settle(page)
                    summary["single_picker_custom_code_and_validation"] = True
                    page.get_by_text("统计与机器学习", exact=True).click()
                    settle(page)
                    page.get_by_text("这个页面怎么用", exact=True).wait_for(timeout=10000)
                    assert "训练比例先保留 70%" in page.inner_text("body")
                    summary.update({"a_candidate_name_search": True, "hk_red_chip_search": True,
                                    "candidate_populates_code": True, "statistics_usage_help": True})
                    page.get_by_text("市场数据", exact=True).click()
                    settle(page)
                    page.get_by_role("button", name="加载真实历史日线", exact=True).click()
                    settle(page)
                    body_text = page.inner_text("body")
                    hk_source = next((source for source in (
                        "东方财富 · AKShare", "新浪财经 · AKShare（东方财富请求失败后回退）"
                    ) if source in body_text), None)
                    assert hk_source and "港股 00941" in body_text and "真实历史数据" in body_text
                    summary.update({"hk_history_loaded": True, "hk_history_source": hk_source})
                if args.learning_center:
                    sidebar = page.get_by_test_id("stSidebar")
                    page.get_by_role("button", name="新手使用指引", exact=True).click()
                    settle(page)
                    page.get_by_role("radiogroup", name="学习中心分区", exact=True).get_by_text("课程与练习", exact=True).click()
                    settle(page)
                    course = page.get_by_role("combobox", name="选择交互课程", exact=True)
                    course.click()
                    settle(page)
                    course.fill("最大回撤")
                    page.get_by_role("option", name="最大回撤", exact=True).click()
                    settle(page)
                    page.get_by_text("最大回撤 · 七层学习", exact=True).wait_for(timeout=10000)
                    slider = page.get_by_test_id("stSlider").filter(has_text="低点净值").get_by_role("slider")
                    slider.press("ArrowLeft")
                    settle(page)
                    page.get_by_role("button", name="保存交互实验记录", exact=True).click()
                    settle(page)
                    page.get_by_label("你的数值答案", exact=True).fill("-20")
                    page.get_by_role("button", name="提交课程测验", exact=True).click()
                    settle(page)
                    page.get_by_text("答对了。", exact=False).wait_for(timeout=10000)
                    page.get_by_role("button", name="使用 DeepSeek 辅导这节课", exact=True).click()
                    settle(page)
                    expect(page.get_by_role("radio", name="教学辅导模式", exact=True)).to_be_checked(timeout=10000)
                    assert "不要直接给出" in page.get_by_label("问题（确认后发送）", exact=True).input_value()
                    page.locator(".st-key-deepseek_side_panel").get_by_role(
                        "button", name="×", exact=True
                    ).click()
                    settle(page)
                    page.get_by_role("radiogroup", name="学习中心分区", exact=True).get_by_text("学习进度", exact=True).click()
                    settle(page)
                    page.get_by_label("当前学习目标", exact=True).fill("桌面验收：掌握回撤后理解样本外")
                    page.get_by_role("button", name="保存学习目标", exact=True).click()
                    settle(page)
                    page.get_by_text("学习目标已保存；不会自动发送给 AI。", exact=True).wait_for(timeout=10000)
                    page.get_by_label("学习笔记标题", exact=True).fill("桌面学习验收")
                    page.get_by_label("学习笔记内容", exact=True).fill("峰值只能使用当前及更早数据；教学样本不是行情。")
                    page.get_by_role("button", name="保存学习笔记", exact=True).click()
                    settle(page)
                    page.get_by_text("学习笔记已保存。", exact=True).wait_for(timeout=10000)
                    sidebar.get_by_text("统计与机器学习", exact=True).click()
                    settle(page)
                    page.get_by_role("button", name="查看本页使用指南", exact=True).click()
                    settle(page)
                    page.get_by_text("统计与机器学习 · 使用指南", exact=True).wait_for(timeout=10000)
                    page.get_by_role("button", name="返回研究任务 · 统计与机器学习", exact=True).click()
                    settle(page)
                    page.get_by_text("统计学与机器学习", exact=True).wait_for(timeout=10000)
                    sidebar.get_by_text("市场数据", exact=True).click()
                    settle(page)
                    summary.update({"learning_center_dom":True,"interactive_lesson":True,"quiz_submission":True,
                        "learning_goal_and_note":True,"help_return_navigation":True,"teaching_draft_without_send":True})
                if args.resume_learning:
                    sidebar = page.get_by_test_id("stSidebar")
                    page.get_by_role("button", name="新手使用指引", exact=True).click()
                    settle(page)
                    page.get_by_text("最大回撤 · 七层学习", exact=True).wait_for(timeout=15000)
                    page.get_by_role("radiogroup", name="学习中心分区", exact=True).get_by_text("学习进度", exact=True).click()
                    settle(page)
                    expect(page.get_by_label("当前学习目标", exact=True)).to_have_value("桌面验收：掌握回撤后理解样本外", timeout=15000)
                    page.get_by_role("button", name="⚙", exact=True).click()
                    settle(page)
                    page.get_by_text("新手模式（关闭为专业模式）", exact=True).click()
                    settle(page)
                    page.get_by_text("新手模式（关闭为专业模式）", exact=True).click()
                    settle(page)
                    page.locator(".st-key-settings_panel").get_by_role("button", name="×", exact=True).click()
                    settle(page)
                    sidebar.get_by_text("市场数据", exact=True).click()
                    settle(page)
                    summary.update({"learning_resumed_in_actual_dom":True,"goal_restored_in_actual_dom":True,
                                    "professional_mode_control":True})
                sidebar = page.get_by_test_id("stSidebar")
                assert sidebar.get_by_text("DeepSeek AI 助手", exact=True).count() == 0
                assert sidebar.get_by_text("AI 研究助手", exact=True).count() == 0
                assert sidebar.get_by_text("新手使用指引", exact=True).count() == 0
                page.get_by_role("button", name="DeepSeek 助手", exact=True).click()
                settle(page)
                page.get_by_role("radiogroup", name="AI 工作区", exact=True).get_by_text("对话与辅导", exact=True).click()
                settle(page)
                assert sidebar.get_by_label("DeepSeek API Key", exact=True).count() == 0
                summary["deepseek_in_right_panel"] = True
                deepseek_panel = page.locator(".st-key-deepseek_side_panel")
                page.get_by_role("button", name="⚙", exact=True).click()
                settle(page)
                settings_panel = page.locator(".st-key-settings_panel")
                settings_panel.get_by_role("tab", name="DeepSeek", exact=True).click()
                settle(page)
                key = settings_panel.get_by_label("DeepSeek API Key", exact=True)
                assert key.get_attribute("type") == "password"
                assert key.input_value() == dummy_key
                if args.mock_ai:
                    expect(page.get_by_role("button", name="测试连接", exact=True)).to_be_enabled(timeout=10000)
                    page.get_by_role("button", name="测试连接", exact=True).click()
                    settle(page)
                    page.get_by_text("连接成功；已取得官方可用模型列表。", exact=True).wait_for(timeout=10000)
                    picker = settings_panel.get_by_role("combobox", name="DeepSeek 模型", exact=True)
                    picker.click()
                    settle(page)
                    page.screenshot(path=str(directory/"model-picker.png"), full_page=True)
                    print(json.dumps({"model_options": page.get_by_role("option").all_inner_texts()}, ensure_ascii=False), flush=True)
                    # Native keyboard selection avoids depending on the popup's
                    # DOM representation in a particular WebView2 runtime.
                    picker.fill("mock-b")
                    picker.press("Enter")
                    settle(page)
                    page.locator(".st-key-settings_panel").get_by_role("button", name="×", exact=True).click()
                    settle(page)
                    page.get_by_label("问题（确认后发送）", exact=True).fill("解释最大回撤并给出手算例子")
                    page.get_by_role("button", name="发送到 DeepSeek", exact=True).click()
                    settle(page)
                    page.get_by_text("实际模型：mock-b-actual", exact=True).wait_for(timeout=20000)
                    assert "STREAM_DONE" in page.inner_text("body")
                    page.get_by_role("button", name="保存选定回答到学习笔记", exact=True).click()
                    settle(page)
                    page.get_by_text("学习笔记 #", exact=False).wait_for(timeout=10000)
                    summary.update({"model_switch": True, "streamed_answer": True, "answer_saved": True})
                    if args.research_fixes:
                        page.get_by_role("button", name="加载真实历史日线", exact=True).click()
                        settle(page)
                        page.get_by_role("radiogroup", name="AI 工作区", exact=True).get_by_text("研究实验", exact=True).click()
                        settle(page)
                        page.get_by_text("DeepSeek 量化研究助手", exact=True).wait_for(timeout=10000)
                        assert "OPENAI_API_KEY" not in page.inner_text("body")
                        page.get_by_role("button", name="生成 AI 假设", exact=True).click()
                        settle(page)
                        page.get_by_text("假设实际模型：mock-b-actual", exact=True).wait_for(timeout=15000)
                        page.get_by_role("button", name="运行受控实验（内置策略）", exact=True).click()
                        settle(page)
                        page.get_by_role("button", name="让 AI 审阅实验", exact=True).click()
                        settle(page)
                        page.get_by_text("审阅实际模型：mock-b-actual", exact=True).wait_for(timeout=15000)
                        page.get_by_role("button", name="下载可复核研究报告", exact=True).wait_for(timeout=10000)
                        summary.update({"research_shared_connection": True, "research_json_hypothesis": True,
                                        "local_controlled_experiment": True, "research_json_report": True})
                    page.get_by_role("button", name="⚙", exact=True).click()
                    settle(page)
                    page.locator(".st-key-settings_panel").get_by_role("button", name="清除密钥", exact=True).click()
                    settle(page)
                    expect(page.get_by_label("DeepSeek API Key", exact=True)).to_have_value("", timeout=10000)
                    summary["key_cleared"] = True
                else:
                    manual = settings_panel.get_by_label("手动模型 ID", exact=True)
                    import sqlite3
                    database = directory / "research.sqlite3"
                    if database.exists():
                        with sqlite3.connect(database) as db:
                            previous_model = db.execute("SELECT value_json FROM settings WHERE key='deepseek_model'").fetchone()
                        if previous_model:
                            assert manual.input_value() == json.loads(previous_model[0])
                            summary["model_preference_restored"] = True
                    manual.fill("manual-model-validation")
                    manual.press("Tab")
                    settle(page)
                    summary["password_and_model_controls"] = True
                page.screenshot(path=str(directory/"webview.png"), full_page=True)
                assert not page.locator('[data-testid="stException"]').count()
                assert not console_errors, console_errors
                summary["console_errors"] = []
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
    except Exception:
        try:
            page.screenshot(path=str(directory/"gui-failure.png"), full_page=True)
            print(json.dumps({"gui_failure_record": str(directory/"gui-failure.png"),
                              "password_field_length": len(page.get_by_label("DeepSeek API Key", exact=True).input_value())}))
        except Exception:
            pass
        raise
    finally:
        if child is not None and child.poll() is None:
            # Only this freshly created process tree; never a process-name kill.
            subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
            child.wait(timeout=10)
        if app_file is not None and original is not None:
            app_file.write_bytes(original)
        clear_key(target=vault_target)


if __name__ == "__main__":
    main()
