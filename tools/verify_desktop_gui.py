"""Interact with the actual WebView2 window through its isolated CDP probe.

No paid calls. --mock-ai is permitted only for an installed copy under .tools;
its app entry is temporarily instrumented with a mock transport and restored.
"""

import argparse
import base64
import json
import os
from pathlib import Path
import sqlite3
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
    parser.add_argument("--manual-reading", action="store_true")
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
                console_warnings = []
                ignored_scheme_errors = []
                def record_console(message):
                    if message.type == "warning":
                        console_warnings.append(message.text)
                        return
                    if message.type != "error":
                        return
                    if message.text == "Failed to load resource: net::ERR_UNKNOWN_URL_SCHEME":
                        ignored_scheme_errors.append(message.location)
                    else:
                        console_errors.append(message.text)
                page.on("console", record_console)
                page.get_by_text("市场数据实验室", exact=True).wait_for(timeout=30000)
                assert page.url.startswith("http://127.0.0.1:")
                expect(page).to_have_title("Quant Lab CN/HK", timeout=10000)
                summary.update({"actual_webview_dom_loaded": True,
                                "page_identity": {"url": page.url, "title": page.title()}})
                topbar = page.locator(".st-key-global_topbar")
                expect(topbar).to_be_visible(timeout=10000)
                sidebar_toggle = page.get_by_role("button", name="▥", exact=True)
                expect(sidebar_toggle).to_be_visible(timeout=10000)
                viewport_width = page.evaluate("window.innerWidth")
                topbar_box = topbar.bounding_box()
                assert topbar_box and topbar_box["x"] <= 1
                assert abs((topbar_box["x"] + topbar_box["width"]) - viewport_width) <= 3
                sidebar = page.get_by_test_id("stSidebar")
                assert sidebar.get_by_text("AI 研究助手", exact=True).count() == 0
                assert sidebar.get_by_text("新手使用指引", exact=True).count() == 0
                assert sidebar.get_by_text("研究笔记", exact=True).count() == 0
                assert sidebar.get_by_text("使用手册", exact=True).count() == 0
                assert page.get_by_role("button", name="新手使用指引", exact=True).count() == 0
                main = page.get_by_test_id("stMain")
                main_before = main.bounding_box()
                manual_button = page.get_by_role("button", name="使用手册", exact=True)
                expect(manual_button).to_be_visible(timeout=10000)
                manual_panel = page.locator(".st-key-manual_side_panel")
                expect(manual_panel).to_be_visible(timeout=10000)
                summary["manual_open_by_default"] = True
                if args.manual_reading:
                    manual_panel.get_by_text(
                        "快速开始：从资料库到第一份可复现实验", exact=True
                    ).wait_for(timeout=10000)
                    manual_navigation = manual_panel.get_by_role(
                        "combobox", name="当前分区", exact=True
                    )
                    manual_navigation.click()
                    manual_navigation.fill("功能说明")
                    manual_navigation.press("Enter")
                    settle(page)
                    manual_panel.get_by_role(
                        "button", name="市场数据：代码、名称、区间、复权、来源与缓存", exact=True
                    ).click()
                    settle(page)
                    manual_panel.get_by_text("加载真实历史日线", exact=False).first.wait_for(timeout=10000)
                    manual_navigation = manual_panel.get_by_role(
                        "combobox", name="当前分区", exact=True
                    )
                    manual_navigation.click()
                    manual_navigation.fill("专业知识库")
                    manual_navigation.press("Enter")
                    settle(page)
                    manual_panel.get_by_role("button", name="开高低收与成交量 / OHLCV", exact=True).click()
                    settle(page)
                    manual_panel.get_by_text("软件状态：软件已实现", exact=True).wait_for(timeout=10000)
                    manual_search = manual_panel.get_by_label("搜索手册与专业知识", exact=True)
                    manual_search.fill("复权")
                    manual_search.press("Enter")
                    settle(page)
                    toolbar = manual_panel.locator(".st-key-manual_sticky_toolbar")
                    toolbar_back = toolbar.get_by_role("button", name="← 返回", exact=True)
                    toolbar_boxes = [
                        manual_navigation.bounding_box(), manual_search.bounding_box(),
                        toolbar_back.bounding_box(),
                    ]
                    assert all(toolbar_boxes)
                    assert max(box["y"] for box in toolbar_boxes) - min(
                        box["y"] for box in toolbar_boxes
                    ) <= 4
                    search_cards = manual_panel.locator('[class*="st-key-manual_search_card_"]')
                    assert search_cards.count() == 12
                    first_card = search_cards.nth(0).bounding_box()
                    second_card = search_cards.nth(1).bounding_box()
                    assert first_card and second_card
                    assert abs(first_card["y"] - second_card["y"]) <= 3
                    assert abs(first_card["width"] - second_card["width"]) <= 3
                    panel_body = manual_panel.locator(".st-key-manual_panel_body")
                    panel_body.evaluate("element => { element.scrollTop = 700; }")
                    toolbar_box = manual_panel.locator(".st-key-manual_sticky_toolbar").bounding_box()
                    body_box = panel_body.bounding_box()
                    assert toolbar_box and body_box and toolbar_box["y"] < body_box["y"] + 4
                    assert toolbar_box["y"] + toolbar_box["height"] > body_box["y"]
                    panel_body.evaluate("element => { element.scrollTop = 0; }")
                    manual_search = manual_panel.get_by_label("搜索手册与专业知识", exact=True)
                    manual_search.fill("Next-Open Execution")
                    manual_search.press("Enter")
                    settle(page)
                    search_result = manual_panel.get_by_role(
                        "button", name="下一交易日开盘成交 / Next-Open Execution", exact=True
                    )
                    search_result.wait_for(state="attached", timeout=10000)
                    search_result.scroll_into_view_if_needed()
                    expect(search_result).to_be_visible(timeout=10000)
                    assert manual_panel.locator(".st-key-manual_panel_body").evaluate(
                        "element => element.scrollTop"
                    ) < 20
                    page.screenshot(path=str(directory/"manual-reading-search.png"), full_page=False)
                    manual_search = manual_panel.get_by_label("搜索手册与专业知识", exact=True)
                    manual_search.fill("Python Functions")
                    manual_search.press("Enter")
                    settle(page)
                    manual_panel.get_by_role(
                        "button", name="Python 函数 / Python Functions", exact=True
                    ).click()
                    settle(page)
                    expect(manual_panel.locator("pre code").first).to_be_visible(timeout=10000)
                    page.screenshot(path=str(directory/"manual-reading-code.png"), full_page=False)
                    summary.update({"manual_reading_dom": True,
                                    "manual_three_entries": True,
                                    "manual_function_directory": True,
                                    "manual_article_and_status": True,
                                    "manual_local_search": True,
                                    "manual_toolbar_single_row": True,
                                    "manual_code_block_rendered": True,
                                    "beginner_guidance_removed": True})
                page.get_by_role("button", name="DeepSeek 助手", exact=True).click()
                settle(page)
                panel = page.locator(".st-key-deepseek_side_panel")
                expect(panel).to_be_visible(timeout=10000)
                expect(panel.get_by_label("问题（确认后发送）", exact=True)).to_be_visible(timeout=10000)
                expect(panel.get_by_role("button", name="⚙ 设置", exact=True)).to_be_visible(timeout=10000)
                assert panel.get_by_text(
                    "连接与模型设置位于左上角 ⚙ → DeepSeek。", exact=True
                ).count() == 0
                manual_box = manual_panel.bounding_box()
                deepseek_box = panel.bounding_box()
                assert manual_box and deepseek_box and manual_box["x"] < deepseek_box["x"]
                page.screenshot(path=str(directory/"manual-reading-coexist.png"), full_page=False)
                summary["manual_coexists_with_panels"] = True
                assert page.get_by_role("dialog").count() == 0
                page.get_by_role("button", name="⚙", exact=True).click()
                settle(page)
                settings_panel = page.locator(".st-key-settings_panel")
                expect(settings_panel).to_be_visible(timeout=10000)
                settings_panel.get_by_role("tab", name="偏好设置", exact=True).click()
                settle(page)
                expect(settings_panel.get_by_text("显示详细解释提示", exact=True)).to_be_visible(timeout=10000)
                assert settings_panel.get_by_text("新手模式（关闭为专业模式）", exact=True).count() == 0
                settings_panel.get_by_role("tab", name="DeepSeek", exact=True).click()
                settle(page)
                initial_key = settings_panel.get_by_label("DeepSeek API Key", exact=True)
                if args.mock_ai:
                    expect(initial_key).to_have_value("")
                    initial_key.fill(dummy_key)
                    settings_panel.get_by_role("button", name="应用密钥", exact=True).click()
                    settle(page)
                    settings_panel = page.locator(".st-key-settings_panel")
                    expect(settings_panel.get_by_label("DeepSeek API Key", exact=True)).to_have_value(dummy_key)
                else:
                    expect(initial_key).to_have_value(dummy_key)
                settings_panel.get_by_role("button", name="×", exact=True).click()
                settle(page)
                manual_box = manual_panel.bounding_box()
                box = panel.bounding_box()
                main_after = main.bounding_box()
                workspace_after = page.get_by_test_id("stMainBlockContainer").bounding_box()
                page.screenshot(path=str(directory/"dual-side-panels.png"), full_page=False)
                assert box and abs((box["x"] + box["width"]) - viewport_width) <= 3, {
                    "panel_box": box, "viewport_width": viewport_width,
                }
                assert manual_box and manual_box["x"] < box["x"]
                padding_right = main.evaluate("element => getComputedStyle(element).paddingRight")
                assert main_before and main_after and workspace_after
                assert float(padding_right.removesuffix("px")) >= box["width"] + manual_box["width"] - 3, {
                    "main_before": main_before, "main_after": main_after,
                    "workspace_after": workspace_after, "panel_box": box, "manual_box": manual_box,
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
                resize_limits = page.evaluate(
                    """() => {
                      const sidebar = document.querySelector('[data-testid="stSidebar"]');
                      const otherWidth = ['manual','notes']
                        .map(kind => document.querySelector(`.st-key-${kind}_side_panel`))
                        .reduce((total, item) => total + (item ? item.getBoundingClientRect().width : 0), 0);
                      const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 0;
                      return {minimum:240, maximum:Math.max(240, window.innerWidth-sidebarWidth-otherWidth-360)};
                    }"""
                )
                grow_panel = resize_limits["maximum"] >= box["width"] + 35
                drag_delta = -45 if grow_panel else 45
                page.mouse.move(resize_box["x"] + 3, resize_box["y"] + 100)
                page.mouse.down()
                page.mouse.move(resize_box["x"] + drag_delta, resize_box["y"] + 100, steps=5)
                page.mouse.up()
                page.wait_for_timeout(300)
                resized_box = panel.bounding_box()
                resize_state = page.evaluate(
                    "() => ({css:getComputedStyle(document.documentElement).getPropertyValue('--ql-deepseek-width'), stored:localStorage.getItem('quantlab.deepseek.panelWidth')})"
                )
                assert hit_target.get("panel") == "deepseek"
                assert resize_state.get("stored") == str(round(resized_box["width"]))
                assert resized_box and abs(resized_box["width"] - box["width"]) >= 35
                page.get_by_role("button", name="研究笔记", exact=True).click()
                settle(page)
                notes_panel = page.locator(".st-key-notes_side_panel")
                expect(notes_panel).to_be_visible(timeout=10000)
                notes_body = notes_panel.locator(".st-key-notes_panel_body")
                notes_body_box = notes_body.bounding_box()
                first_screen_controls = [
                    notes_panel.get_by_label("笔记标题", exact=True),
                    notes_panel.get_by_label("Markdown 正文", exact=True),
                    notes_panel.get_by_role("button", name="保存笔记", exact=True),
                    notes_panel.get_by_role("button", name="新建笔记", exact=True),
                ]
                control_boxes = [control.bounding_box() for control in first_screen_controls]
                assert notes_body_box and all(control_boxes)
                assert max(box["y"] + box["height"] for box in control_boxes) <= (
                    notes_body_box["y"] + notes_body_box["height"] + 2
                )
                notes_panel.get_by_label("笔记标题", exact=True).fill("GUI 保留草稿")
                notes_panel.get_by_label("Markdown 正文", exact=True).fill("新建前应自动保存。")
                notes_panel.get_by_role("button", name="新建笔记", exact=True).click()
                settle(page)
                notes_panel = page.locator(".st-key-notes_side_panel")
                expect(notes_panel.get_by_label("笔记标题", exact=True)).to_have_value("")
                with sqlite3.connect(directory / "research.sqlite3") as db:
                    assert db.execute(
                        "SELECT COUNT(*) FROM note_drafts WHERE title=? AND content=?",
                        ("GUI 保留草稿", "新建前应自动保存。"),
                    ).fetchone()[0] == 1
                notes_panel.get_by_label("笔记标题", exact=True).fill("GUI 附件笔记")
                notes_panel.get_by_label("Markdown 正文", exact=True).fill("# 图表记录\n\n本地托管附件验收。")
                notes_panel.get_by_text("笔记选项与附件", exact=True).click()
                png = base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Z2S8AAAAASUVORK5CYII="
                )
                notes_panel.get_by_label("添加附件", exact=True).locator('input[type="file"]').set_input_files([
                    {"name":"chart.png", "mimeType":"image/png", "buffer":png},
                    {"name":"evidence.pdf", "mimeType":"application/pdf", "buffer":b"%PDF-1.4\n%%EOF"},
                ])
                notes_panel.get_by_role("button", name="保存所选附件到草稿", exact=True).click()
                settle(page)
                notes_panel = page.locator(".st-key-notes_side_panel")
                insert = notes_panel.get_by_role("button", name="插入", exact=True)
                if not insert.is_visible():
                    notes_panel.get_by_text("笔记选项与附件", exact=True).click()
                insert.click()
                settle(page)
                page.locator(".st-key-notes_side_panel").get_by_role("button", name="保存笔记", exact=True).click()
                settle(page)
                with sqlite3.connect(directory / "research.sqlite3") as db:
                    saved_note = db.execute(
                        "SELECT id,content FROM learning_notes WHERE title=? ORDER BY id DESC LIMIT 1",
                        ("GUI 附件笔记",),
                    ).fetchone()
                    assert saved_note and "attachment://" in saved_note[1]
                    assert db.execute(
                        "SELECT COUNT(*) FROM note_attachments WHERE note_id=?", (saved_note[0],)
                    ).fetchone()[0] == 2
                notes_panel = page.locator(".st-key-notes_side_panel")
                notes_panel.get_by_text("浏览笔记与实验", exact=True).click()
                notes_body = notes_panel.locator(".st-key-notes_panel_body")
                notes_body.evaluate("element => { element.scrollTop = element.scrollHeight; }")
                notes_panel.get_by_role("button", name="编辑", exact=True).click()
                settle(page)
                notes_panel = page.locator(".st-key-notes_side_panel")
                expect(notes_panel.get_by_label("笔记标题", exact=True)).to_have_value("GUI 附件笔记")
                assert notes_panel.locator(".st-key-notes_panel_body").evaluate(
                    "element => element.scrollTop"
                ) < 20
                sticky_headers = []
                for panel_name in ("manual", "deepseek", "notes"):
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

                sidebar_toggle.click()
                settle(page)
                expect(sidebar).not_to_be_visible(timeout=10000)
                expect(page.locator(".ql-left-sidebar-hidden")).to_be_attached(timeout=10000)
                expect(page.locator(".st-key-manual_side_panel")).to_be_visible(timeout=10000)
                expect(page.locator(".st-key-deepseek_side_panel")).to_be_visible(timeout=10000)
                expect(page.locator(".st-key-notes_side_panel")).to_be_visible(timeout=10000)
                workspace_without_sidebar = page.get_by_test_id("stMainBlockContainer").bounding_box()
                assert workspace_without_sidebar and workspace_after
                assert workspace_without_sidebar["x"] < workspace_after["x"] - 100, {
                    "with_sidebar": workspace_after, "without_sidebar": workspace_without_sidebar,
                }
                sidebar_toggle.click()
                settle(page)
                expect(sidebar).to_be_visible(timeout=10000)
                expect(page.locator(".st-key-manual_side_panel")).to_be_visible(timeout=10000)
                expect(page.locator(".st-key-deepseek_side_panel")).to_be_visible(timeout=10000)
                expect(page.locator(".st-key-notes_side_panel")).to_be_visible(timeout=10000)
                notes_panel = page.locator(".st-key-notes_side_panel")
                page.screenshot(path=str(directory/"triple-side-panels.png"), full_page=False)
                manual_button = page.get_by_role("button", name="使用手册", exact=True)
                deepseek_button = page.get_by_role("button", name="DeepSeek 助手", exact=True)
                notes_button = page.get_by_role("button", name="研究笔记", exact=True)
                manual_button_box = manual_button.bounding_box()
                deepseek_button_box = deepseek_button.bounding_box()
                assert manual_button_box and deepseek_button_box
                assert manual_button.get_attribute("data-reorder-bound") == "1"
                assert deepseek_button.get_attribute("data-reorder-bound") == "1"
                assert manual_button_box["x"] < deepseek_button_box["x"]
                page.mouse.move(
                    deepseek_button_box["x"] + deepseek_button_box["width"] / 2,
                    deepseek_button_box["y"] + deepseek_button_box["height"] / 2,
                )
                page.mouse.down()
                page.mouse.move(
                    manual_button_box["x"] + manual_button_box["width"] / 3,
                    manual_button_box["y"] + manual_button_box["height"] / 2,
                    steps=8,
                )
                page.mouse.up()
                page.wait_for_timeout(350)
                stored_order = page.evaluate("JSON.parse(localStorage.getItem('quantlab.dock.panelOrder'))")
                assert stored_order[0] == "deepseek" and set(stored_order) == {"manual","deepseek","notes"}
                manual_panel = page.locator(".st-key-manual_side_panel")
                panel = page.locator(".st-key-deepseek_side_panel")
                reordered_manual_button_box = manual_button.bounding_box()
                reordered_deepseek_button_box = deepseek_button.bounding_box()
                swapped_manual_box = manual_panel.bounding_box()
                swapped_deepseek_box = panel.bounding_box()
                assert reordered_manual_button_box and reordered_deepseek_button_box
                assert reordered_deepseek_button_box["x"] < reordered_manual_button_box["x"]
                assert swapped_manual_box and swapped_deepseek_box
                assert swapped_deepseek_box["x"] < swapped_manual_box["x"]
                page.screenshot(path=str(directory/"dual-side-panels-swapped.png"), full_page=False)
                notes_panel.get_by_role("button", name="⛶", exact=True).click()
                settle(page)
                notes_panel = page.locator(".st-key-notes_side_panel")
                maximized_box = notes_panel.bounding_box()
                sidebar_box = sidebar.bounding_box()
                assert maximized_box and sidebar_box
                assert abs(maximized_box["x"] - (sidebar_box["x"] + sidebar_box["width"])) <= 3, {
                    "maximized": maximized_box, "sidebar": sidebar_box,
                }
                assert abs((maximized_box["x"] + maximized_box["width"]) - viewport_width) <= 3
                maximized_header_box = notes_panel.locator(".st-key-notes_panel_header").bounding_box()
                current_topbar_box = topbar.bounding_box()
                assert maximized_header_box and current_topbar_box
                assert abs(maximized_box["y"] - (current_topbar_box["y"] + current_topbar_box["height"])) <= 2
                assert abs(maximized_header_box["y"] - maximized_box["y"]) <= 2
                expect(topbar).to_be_visible()
                expect(sidebar_toggle).to_be_visible()
                assert main.evaluate("element => getComputedStyle(element).paddingRight") == "0px"
                page.screenshot(path=str(directory/"maximized-with-sidebar.png"), full_page=False)

                sidebar_toggle.click()
                settle(page)
                expect(sidebar).not_to_be_visible(timeout=10000)
                notes_panel = page.locator(".st-key-notes_side_panel")
                app_maximized_box = notes_panel.bounding_box()
                assert app_maximized_box and app_maximized_box["x"] <= 2
                assert app_maximized_box["width"] >= viewport_width - 3
                page.screenshot(path=str(directory/"maximized-without-sidebar.png"), full_page=False)

                sidebar_toggle.click()
                settle(page)
                expect(sidebar).to_be_visible(timeout=10000)
                notes_panel = page.locator(".st-key-notes_side_panel")
                restored_maximized_box = notes_panel.bounding_box()
                restored_sidebar_box = sidebar.bounding_box()
                assert restored_maximized_box and restored_sidebar_box
                assert abs(restored_maximized_box["x"] - restored_sidebar_box["width"]) <= 3
                page.keyboard.press("Escape")
                settle(page)
                expect(page.locator(".st-key-manual_side_panel")).to_be_visible(timeout=10000)
                expect(page.locator(".st-key-deepseek_side_panel")).to_be_visible(timeout=10000)
                summary.update({"global_topbar_dom": True, "topbar_pages_removed_from_sidebar": True,
                                "deepseek_global_launcher": True, "manual_global_launcher": True,
                                "notes_global_launcher": True, "triple_panels_open": True,
                                "left_sidebar_launcher": True, "sticky_panel_headers": sticky_headers,
                                "topbar_preserved_during_maximize": True,
                                "maximize_respects_visible_sidebar": True,
                                "maximize_fills_app_without_sidebar": True,
                                "markdown_note_with_attachments": True,
                                "notes_editor_first_screen": True,
                                "notes_new_preserves_draft": True,
                                "notes_library_edit_scrolls_to_editor": True,
                                "panels_reordered_by_drag": True, "panel_maximize_restore": True,
                                "panel_drag_resize": True, "workspace_resized_for_panel": True,
                                "panel_width_before": box["width"],
                                "panel_width_after": resized_box["width"],
                                "remembered_key_restored_on_start": not args.mock_ai})
                page.locator(".st-key-notes_side_panel").get_by_role("button", name="×", exact=True).click()
                settle(page)
                manual_panel.get_by_role("button", name="×", exact=True).click()
                settle(page)
                panel = page.locator(".st-key-deepseek_side_panel")
                panel.get_by_role("button", name="×", exact=True).click()
                settle(page)
                expect(panel).not_to_be_visible(timeout=10000)
                if args.manual_reading:
                    page.get_by_role("button", name="使用手册", exact=True).click()
                    settle(page)
                    manual_panel = page.locator(".st-key-manual_side_panel")
                    expect(manual_panel).to_be_visible(timeout=10000)
                    manual_resize = manual_panel.locator('.ql-resize-handle[data-panel="manual"]')
                    assert manual_resize.get_attribute("data-bound") == "1"
                    manual_before = manual_panel.bounding_box()
                    manual_resize_box = manual_resize.bounding_box()
                    assert manual_before and manual_resize_box
                    page.mouse.move(manual_resize_box["x"] + 3, manual_resize_box["y"] + 100)
                    page.mouse.down()
                    page.mouse.move(manual_resize_box["x"] - 45, manual_resize_box["y"] + 100, steps=5)
                    page.mouse.up()
                    page.wait_for_timeout(300)
                    manual_after = manual_panel.bounding_box()
                    stored_manual_width = page.evaluate(
                        "localStorage.getItem('quantlab.manual.panelWidth')"
                    )
                    assert manual_after and manual_after["width"] >= manual_before["width"] + 35
                    assert stored_manual_width == str(round(manual_after["width"]))
                    manual_panel.get_by_role("button", name="⛶", exact=True).click()
                    settle(page)
                    manual_panel = page.locator(".st-key-manual_side_panel")
                    manual_maximized = manual_panel.bounding_box()
                    current_sidebar = sidebar.bounding_box()
                    assert manual_maximized and current_sidebar
                    assert abs(manual_maximized["x"] - (current_sidebar["x"] + current_sidebar["width"])) <= 3
                    expect(topbar).to_be_visible()
                    page.screenshot(path=str(directory/"manual-reading-maximized.png"), full_page=False)
                    manual_panel.get_by_role("button", name="⛶", exact=True).click()
                    settle(page)
                    manual_panel = page.locator(".st-key-manual_side_panel")
                    manual_panel.get_by_role("button", name="×", exact=True).click()
                    settle(page)
                    summary.update({"manual_reading_resize": True,
                                    "manual_reading_maximize_restore": True,
                                    "manual_reading_close": True})
                    sidebar.get_by_text("Quant Academy", exact=True).click()
                    settle(page)
                    lesson_picker = page.get_by_role("combobox", name="选择课程", exact=True)
                    lesson_picker.click()
                    lesson_picker.fill("回测偏差与过拟合")
                    page.get_by_role("option", name="8. 回测偏差与过拟合", exact=True).click()
                    settle(page)
                    body_text = page.inner_text("body")
                    assert "本课没有单一的‘偏差值’" in body_text
                    assert "当前没有足够的有效计算值" not in body_text
                    assert page.get_by_role("button", name="保存交互实验记录", exact=True).count() == 0
                    assert page.get_by_role("button", name="提交课程测验", exact=True).count() == 0
                    page.screenshot(path=str(directory/"academy-lesson-8-explanation.png"), full_page=False)
                    sidebar.get_by_text("市场数据", exact=True).click()
                    settle(page)
                    summary.update({"academy_no_progress_actions": True,
                                    "academy_lesson_8_current_explanation": True,
                                    "detailed_explanation_label": True})
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
                    if args.mock_ai:
                        assert "模拟API验收日线（非真实行情）" in body_text and "港股 00941" in body_text
                        summary.update({"mock_history_loaded": True,
                                        "mock_history_not_labeled_real": "已加载真实历史数据" not in body_text})
                    else:
                        hk_source = next((source for source in (
                            "东方财富 · AKShare", "新浪财经 · AKShare（东方财富请求失败后回退）"
                        ) if source in body_text), None)
                        assert hk_source and "港股 00941" in body_text and "真实历史数据" in body_text
                        summary.update({"hk_history_loaded": True, "hk_history_source": hk_source})
                    sidebar.get_by_text("历史回测", exact=True).click()
                    settle(page)
                    page.get_by_role("button", name="运行历史回测", exact=True).click()
                    settle(page)
                    explanation = page.get_by_test_id("stExpander").filter(
                        has_text="知识解释："
                    )
                    assert explanation.count() == 2
                    page.get_by_role("button", name="显示更多（剩余 6 项）", exact=True).click()
                    settle(page)
                    assert page.get_by_test_id("stExpander").filter(
                        has_text="知识解释："
                    ).count() == 8
                    page.get_by_role("button", name="收起详细解释", exact=True).click()
                    settle(page)
                    assert page.get_by_test_id("stExpander").filter(
                        has_text="知识解释："
                    ).count() == 2
                    page.get_by_role("button", name="显示更多（剩余 6 项）", exact=True).click()
                    settle(page)
                    page.get_by_role("button", name="⚙", exact=True).click()
                    settle(page)
                    settings_panel = page.locator(".st-key-settings_panel")
                    settings_panel.get_by_role("tab", name="偏好设置", exact=True).click()
                    settings_panel.get_by_text("显示详细解释提示", exact=True).click()
                    settle(page)
                    expect(page.locator(".st-key-settings_panel")).to_be_visible(timeout=10000)
                    assert not page.locator(".st-key-settings_panel").get_by_label(
                        "显示详细解释提示", exact=True
                    ).is_checked()
                    assert page.get_by_test_id("stExpander").filter(
                        has_text="知识解释："
                    ).count() == 0
                    page.locator(".st-key-settings_panel").get_by_text(
                        "显示详细解释提示", exact=True
                    ).click()
                    settle(page)
                    assert page.locator(".st-key-settings_panel").get_by_label(
                        "显示详细解释提示", exact=True
                    ).is_checked()
                    assert page.get_by_test_id("stExpander").filter(
                        has_text="知识解释："
                    ).count() == 2
                    page.locator(".st-key-settings_panel").get_by_role(
                        "button", name="×", exact=True
                    ).click()
                    settle(page)
                    page.get_by_role("button", name="显示更多（剩余 6 项）", exact=True).click()
                    settle(page)
                    assert page.get_by_test_id("stExpander").filter(
                        has_text="知识解释："
                    ).count() == 8
                    page.get_by_role("button", name="⚙", exact=True).click()
                    settle(page)
                    settings_panel = page.locator(".st-key-settings_panel")
                    settings_panel.get_by_role("tab", name="偏好设置", exact=True).click()
                    settings_panel.get_by_role("button", name="刷新整页", exact=True).click()
                    settle(page)
                    expect(page.locator(".st-key-settings_panel")).to_be_visible(timeout=10000)
                    assert page.get_by_test_id("stExpander").filter(
                        has_text="知识解释："
                    ).count() == 2
                    page.locator(".st-key-settings_panel").get_by_role(
                        "button", name="×", exact=True
                    ).click()
                    settle(page)
                    summary.update({"knowledge_group_pagination": True,
                                    "learning_mode_immediate_app_rerun": True,
                                    "learning_mode_manual_refresh": True})
                sidebar = page.get_by_test_id("stSidebar")
                assert sidebar.get_by_text("DeepSeek AI 助手", exact=True).count() == 0
                assert sidebar.get_by_text("AI 研究助手", exact=True).count() == 0
                assert sidebar.get_by_text("新手使用指引", exact=True).count() == 0
                page.get_by_role("button", name="DeepSeek 助手", exact=True).click()
                settle(page)
                assert sidebar.get_by_label("DeepSeek API Key", exact=True).count() == 0
                summary["deepseek_in_right_panel"] = True
                deepseek_panel = page.locator(".st-key-deepseek_side_panel")
                expect(deepseek_panel.get_by_label("问题（确认后发送）", exact=True)).to_be_visible(timeout=10000)
                expect(deepseek_panel.get_by_role("button", name="⚙ 设置", exact=True)).to_be_visible(timeout=10000)
                expect(deepseek_panel.get_by_role("button", name="研究实验", exact=True)).to_be_visible(timeout=10000)
                assert deepseek_panel.get_by_role("radiogroup", name="AI 工作区", exact=True).count() == 0
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
                    deepseek_panel.get_by_role("button", name="⚙ 设置", exact=True).click()
                    settle(page)
                    page.get_by_role("button", name="保存选定回答到研究笔记", exact=True).click()
                    settle(page)
                    page.get_by_text("研究笔记 #", exact=False).wait_for(timeout=10000)
                    summary.update({"model_switch": True, "streamed_answer": True, "answer_saved": True})
                    if args.research_fixes:
                        page.get_by_role("button", name="加载真实历史日线", exact=True).click()
                        settle(page)
                        deepseek_panel.get_by_role("button", name="研究实验", exact=True).click()
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
                    settings_panel = page.locator(".st-key-settings_panel")
                    settings_panel.get_by_role("tab", name="DeepSeek", exact=True).click()
                    settle(page)
                    page.locator(".st-key-settings_panel").get_by_role("button", name="清除密钥", exact=True).click()
                    settle(page)
                    expect(page.get_by_label("DeepSeek API Key", exact=True)).to_have_value("", timeout=10000)
                    summary["key_cleared"] = True
                else:
                    manual = settings_panel.get_by_label("手动模型 ID", exact=True)
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
                assert not console_warnings, console_warnings
                summary["console_errors"] = []
                summary["console_warnings"] = []
                summary["framework_overlay_absent"] = True
                summary["ignored_webview_scheme_warnings"] = len(ignored_scheme_errors)
                try:
                    page.evaluate("() => { window.pywebview.api.close(); return true; }")
                except Error as exc:
                    if "closed" not in str(exc).lower():
                        raise
                child.wait(timeout=15)
        probe = json.loads(probe_file.read_text(encoding="utf-8"))
        assert child.returncode == 0 and probe.get("webview_loaded") and probe.get("child_stopped")
        parent_log = (directory / "parent.log").read_text(encoding="utf-8", errors="replace")
        assert 'The widget with key "deepseek_attach" was created with a default value' not in parent_log
        summary.update({"loaded_event": True, "child_stopped": True, "exit_code": child.returncode,
                        "streamlit_widget_state_warning": False})
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
