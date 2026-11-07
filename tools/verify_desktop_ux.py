"""One scoped real-data WebView2 check, without reading personal app data."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4

COMPLETION_ONLY = '--completion-only' in sys.argv
READING_ONLY = '--reading-only' in sys.argv
LIFECYCLE_ONLY = '--lifecycle-only' in sys.argv
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.benchmark_desktop import close_owned_native_window, settle
from playwright.sync_api import sync_playwright

directory = ROOT / '.tools' / ('desktop-ux-gui-' + uuid4().hex)
source = directory / 'source'
source.mkdir(parents=True)
for filename in ('app.py', 'desktop_launcher.py'):
    shutil.copy2(ROOT / filename, source / filename)
for folder in ('quant_lab', '.streamlit', 'docs', 'assets'):
    shutil.copytree(ROOT / folder, source / folder, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
app = source / 'app.py'
body = app.read_text(encoding='utf-8')
lines = body.splitlines(keepends=True)
tree = ast.parse(body)
position = tree.body[0].end_lineno if ast.get_docstring(tree) else 0
fixture = directory / 'fixture.py'
fixture.write_text((ROOT / 'tools/gui_api_fixture.py').read_text(encoding='utf-8') + r"""
from pathlib import Path
credentials.load_key = lambda **kwargs: 'sk-isolated-ux-test'
_original_request = request
def ux_request(self, method, endpoint, **kwargs):
    if method.upper() == 'POST':
        counter = Path(__file__).parent / 'post-count.txt'
        counter.write_text(str(int(counter.read_text()) + 1) if counter.exists() else '1')
        if kwargs.get('json', {}).get('messages', [{}])[-1].get('content', '').find('测试失败') >= 0:
            from quant_lab.deepseek import AIRequestError
            raise AIRequestError('模拟接口失败，仅用于隔离验收')
    return _original_request(self, method, endpoint, **kwargs)
def ux_lines(self, **kwargs):
    for i in range(30):
        yield 'data: ' + json.dumps({'model':'mock-a-actual','choices':[{'delta':{'content':f'第{i}段：模拟流式回复，检查上翻阅读不被拉走。' * 4 + '\\n\\n'}}]},ensure_ascii=False)
        time.sleep(.12)
    yield 'data: [DONE]'
Response.iter_lines = ux_lines
DeepSeekClient._request = ux_request
""", encoding='utf-8')
lines.insert(position, f"import runpy\nrunpy.run_path({str(fixture)!r})\n")
app.write_text(''.join(lines), encoding='utf-8')
launcher = source / 'desktop_launcher.py'
code = launcher.read_text(encoding='utf-8')
marker = 'from __future__ import annotations'
code = code.replace(marker, marker + "\nimport ctypes\nctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('QuantLab.Validation.DesktopUX')", 1)
code = code.replace('"debug_port": probe_debug_port,', '"debug_port": probe_debug_port, "host_pid": os.getpid(),', 1)
launcher.write_text(code, encoding='utf-8')
probe = directory / 'probe.json'
env = {**os.environ, 'QUANT_LAB_DATA_DIR': str(directory / 'user'),
       'QUANT_LAB_CREDENTIAL_TARGET': 'QuantLab/Validation/' + uuid4().hex,
       'QUANT_LAB_GUI_PROBE': '1', 'QUANT_LAB_GUI_TEST_SECONDS': '360',
       'QUANT_LAB_SMOKE_RESULT': str(probe), 'PYTHONPATH': str(source)}
# Seed the saved learning preset that used to reopen Academy and the manual.
profile = directory / 'user' / 'workspace-presets.json'
profile.parent.mkdir(parents=True, exist_ok=True)
profile.write_text(json.dumps({'format':2,'active':'学习','profiles':{'学习':{
    'nav_page':'Quant Academy','manual_panel_open':True,'maximized_panel':'manual',
    'symbol_A 股':'000001'}}},ensure_ascii=False),encoding='utf-8')
report = {'completion_only': COMPLETION_ONLY, 'reading_only': READING_ONLY, 'lifecycle_only': LIFECYCLE_ONLY, 'mock_api': True, 'physical_ime_verified': False, 'browser_path': 'Actual owned WebView2 via project CDP; ego-browser cannot attach the native desktop WebView', 'checks': {}, 'page_errors': []}
child = None
page = None
try:
    with (directory / 'parent.log').open('w', encoding='utf-8') as log:
        child = subprocess.Popen([sys.executable, str(launcher)], cwd=source, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            if probe.exists():
                payload = json.loads(probe.read_text(encoding='utf-8'))
                if payload.get('debug_port'):
                    break
            if child.poll() is not None:
                raise RuntimeError('desktop stopped before ready')
            time.sleep(.2)
        else:
            raise TimeoutError('no desktop probe')
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
            page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
            page.get_by_test_id('stSidebar').wait_for(timeout=45000)
            settle(page)
            report['title'] = page.title()
            report['url'] = page.url
            from playwright.sync_api import expect
            from tools.benchmark_desktop import capture_failure
            with capture_failure(page, directory):
                def check(name):
                    report['checks'][name] = True
                    (directory / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                def post_count():
                    counter = directory / 'post-count.txt'
                    return int(counter.read_text()) if counter.exists() else 0
                page.set_viewport_size({'width':1366,'height':768})
                page.locator('.st-key-deepseek_panel_toggle button').click()
                settle(page)
                page.locator('.st-key-settings_toggle button').click()
                settle(page)
                page.get_by_role('tab', name='DeepSeek', exact=True).click()
                page.get_by_role('button', name='测试连接', exact=True).click()
                settle(page)
                page.locator('.st-key-settings_close button').click()
                settle(page)
                area = page.get_by_role('textbox', name='问题（确认后发送）', exact=True)
                area.fill('未发送草稿')
                area.press('Tab')
                settle(page)
                assert post_count() == 0
                check('redraw_without_request')
                audit_source = (Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'skills/desktop-agent-ui/scripts/clip-audit.js').read_text(encoding='utf-8')
                report['audits'] = {}
                if not COMPLETION_ONLY and not LIFECYCLE_ONLY:
                    if not READING_ONLY:
                        for width,height in ((1366,768),(1920,1080)):
                            page.set_viewport_size({'width':width,'height':height})
                            page.wait_for_timeout(300)
                            panel = page.locator('.st-key-deepseek_side_panel')
                            panel.scroll_into_view_if_needed()
                            handle = panel.locator('.ql-resize-handle')
                            before = panel.bounding_box()['width']
                            stored = page.evaluate("localStorage.getItem('quantlab.deepseek.panelWidth')")
                            box = handle.bounding_box()
                            page.mouse.move(box['x']+4,box['y']+140)
                            page.mouse.down(); page.mouse.move(box['x']-55,box['y']+140,steps=5)
                            page.wait_for_timeout(100)
                            assert abs(panel.bounding_box()['width']-before)>20
                            page.keyboard.press('Escape'); page.mouse.up()
                            assert abs(panel.bounding_box()['width']-before)<2
                            assert page.evaluate("localStorage.getItem('quantlab.deepseek.panelWidth')") == stored
                            assert page.locator('.is-dragging').count() == 0
                            handle.focus(); page.keyboard.press('ArrowLeft')
                            page.wait_for_timeout(100)
                            assert panel.bounding_box()['width']>before
                            check(f'{width}_resize_escape_and_keyboard')
                            # Pointer cancellation and focus loss roll back too.
                            for event in ('pointercancel','blur'):
                                before = panel.bounding_box()['width']
                                box=handle.bounding_box()
                                page.mouse.move(box['x']+4,box['y']+140);page.mouse.down()
                                page.mouse.move(box['x']-40,box['y']+140,steps=4)
                                page.wait_for_timeout(80)
                                page.evaluate('(event) => window.dispatchEvent(new Event(event))',event)
                                page.mouse.up()
                                assert abs(panel.bounding_box()['width']-before)<2
                            check(f'{width}_cancel_blur')
                            # Reorder previews must never persist until pointerup.
                            button = page.locator('.st-key-deepseek_panel_toggle button')
                            old_order=page.evaluate('document.documentElement.dataset.qlDockOrder')
                            old_saved=page.evaluate("localStorage.getItem('quantlab.dock.panelOrder')")
                            box=button.bounding_box(); other=page.locator('.st-key-manual_panel_toggle button').bounding_box()
                            page.mouse.move(box['x']+box['width']/2,box['y']+15);page.mouse.down()
                            page.mouse.move(other['x']-5,other['y']+15,steps=8)
                            page.wait_for_timeout(100)
                            assert page.evaluate("localStorage.getItem('quantlab.dock.panelOrder')") == old_saved
                            page.keyboard.press('Escape');page.mouse.up()
                            assert page.evaluate('document.documentElement.dataset.qlDockOrder') == old_order
                            check(f'{width}_reorder_escape')
                            panel.scroll_into_view_if_needed()
                            area.fill('多行输入内容\n'*25)
                            page.wait_for_timeout(120)
                            size=area.evaluate('(a)=>({height:a.clientHeight,scroll:a.scrollHeight})')
                            assert 92 <= size['height'] <= 240 and size['scroll']>size['height'], size
                            assert area.evaluate('(a)=>getComputedStyle(a).overflowY') == 'auto'
                            area.fill('中文选词')
                            area.focus()
                            area.dispatch_event('compositionstart', {'data':'中文'})
                            area.dispatch_event('keydown', {'key':'Enter','isComposing':True,'keyCode':229,'bubbles':True})
                            area.dispatch_event('compositionend', {'data':'中文'})
                            area.dispatch_event('keydown', {'key':'Enter','keyCode':229,'bubbles':True})
                            page.wait_for_timeout(350)
                            assert post_count()==0
                            area.press('Shift+Enter')
                            assert '\n' in area.input_value()
                            check(f'{width}_composition_events_and_shift_enter')
                            report['audits'][f'{width}_static']=page.evaluate(audit_source, {'root':'.st-key-workbench_scroller'})
                            handle.hover()
                            report['audits'][f'{width}_hover']=page.evaluate(audit_source, {'root':'.st-key-workbench_scroller'})
                            page.screenshot(path=str(directory/f'ux-{width}.png'))
                    # One physical Enter + repeat event: exactly one mock request.
                    area.fill('验证流式阅读')
                    area.press('Enter')
                    area.dispatch_event('keydown', {'key':'Enter','repeat':True,'bubbles':True})
                    messages=page.locator('.st-key-deepseek_messages')
                    page.wait_for_function("document.querySelector('.st-key-deepseek_messages')?.scrollHeight > 800",timeout=15000)
                    messages.evaluate('(p)=>{p.scrollTop=0;p.dispatchEvent(new Event("scroll"))}')
                    page.wait_for_timeout(650)
                    assert messages.evaluate('(p)=>p.scrollTop') < 10
                    latest=page.get_by_role('button', name='回到最新回复', exact=True)
                    expect(latest).to_be_visible()
                    settle(page)
                    assert messages.evaluate('(p)=>p.scrollTop') < 10
                    latest.click()
                    page.wait_for_timeout(250)
                    assert messages.evaluate('(p)=>p.scrollHeight-p.scrollTop-p.clientHeight') <= 80
                    settle(page)
                    assert post_count()==1
                    check('stream_reading_and_single_request')
                    # Preserve reading position across a real app rerun.
                    messages.evaluate('(p)=>{p.scrollTop=0;p.dispatchEvent(new Event("scroll"))}')
                    page.locator('.st-key-manual_panel_toggle button').click();settle(page)
                    assert messages.evaluate('(p)=>p.scrollTop') < 10
                    assert post_count()==1
                    check('reading_position_after_redraw')
                if not READING_ONLY and not LIFECYCLE_ONLY:
                    page.locator('.st-key-deepseek_side_panel').scroll_into_view_if_needed()
                    area.fill('测试失败');area.press('Enter');settle(page)
                    expect(page.get_by_text('模拟接口失败，仅用于隔离验收', exact=False)).to_be_visible(timeout=15000)
                    assert post_count()==(3 if COMPLETION_ONLY else 4)  # Existing bounded recovery: initial + 2 retries.
                    check('failed_request_visible')
                if LIFECYCLE_ONLY:
                    panel = page.locator('.st-key-deepseek_side_panel')
                    handle = panel.locator('.ql-resize-handle')
                    stored = page.evaluate("localStorage.getItem('quantlab.deepseek.panelWidth')")
                    box=handle.bounding_box()
                    page.mouse.move(box['x']+4,box['y']+140);page.mouse.down()
                    page.mouse.move(box['x']-30,box['y']+140,steps=3)
                    page.locator('.st-key-deepseek_panel_close button').dispatch_event('click')
                    settle(page);page.mouse.up()
                    assert page.evaluate('window.__quantLabCancelDrag === null')
                    assert page.locator('.is-dragging').count()==0
                    assert page.evaluate("localStorage.getItem('quantlab.deepseek.panelWidth')")==stored
                    page.locator('.st-key-deepseek_panel_toggle button').click();settle(page)
                    assert area.input_value()=='未发送草稿'
                    page.locator('.st-key-manual_panel_toggle button').click();settle(page)
                    page.locator('.st-key-notes_panel_toggle button').click();settle(page)
                    assert all(page.locator(f'.st-key-{kind}_side_panel').count()==1 for kind in ('manual','deepseek','notes'))
                    assert page.locator('.st-key-main_workspace').count()==1
                    assert post_count()==0
                    page.locator('.st-key-deepseek_side_panel').scroll_into_view_if_needed()
                    check('drag_node_removal_reopen_draft_and_four_columns')
                report['audits']['expanded']=page.evaluate(audit_source, {'root':'.st-key-workbench_scroller'})
                page.emulate_media(reduced_motion='reduce')
                report['audits']['final']=page.evaluate(audit_source, {'root':'.st-key-workbench_scroller'})
                page.screenshot(path=str(directory/'ux-final.png'))
                report['post_count'] = post_count()
                assert not page.get_by_test_id('stException').count()
                assert all(item.get('cut')==0 for item in report['audits'].values()),report['audits']
                check('clip_audit_all_states')
                close_owned_native_window(child.pid, payload.get('host_pid', child.pid))
                child.wait(timeout=20)
                report['checks']['desktop_exit'] = child.returncode == 0
except Exception as error:
    report['failure'] = repr(error)
    if page:
        try:
            report['failure_dom'] = page.locator('body').inner_text()[:18000]
            page.screenshot(path=str(directory / 'failure.png'))
        except Exception:
            pass
    raise
finally:
    if child and child.poll() is None:
        subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
    (directory / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(directory)
