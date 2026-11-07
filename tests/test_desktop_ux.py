"""Behaviour regressions for desktop UX; all model requests are local doubles."""
from pathlib import Path
from threading import Event

from streamlit.testing.v1 import AppTest

from quant_lab.jobs import JobManager, JobState


def test_cancel_discards_late_response():
    started, release, returned = Event(), Event(), Event()
    def request():
        started.set()
        release.wait(5)
        returned.set()
        return 'late price must not replace valid data'
    manager = JobManager(io_workers=1)
    try:
        identifier = manager.submit('ux', 'history', 'one', request)
        assert started.wait(3)
        assert manager.cancel(identifier, 'ux')
        release.set()
        assert returned.wait(3)
        manager._futures[identifier].result(timeout=3)
        snapshot = manager.get(identifier, 'ux')
        assert snapshot.state == JobState.CANCELLED and snapshot.result is None
    finally:
        release.set()
        manager.close()


def test_request_gate_keeps_original_pending_and_rejects_busy(monkeypatch):
    from quant_lab import ui_deepseek
    state = {}
    monkeypatch.setattr(ui_deepseek.st, 'session_state', state)
    assert ui_deepseek._queue_request({'id':'original'})
    assert not ui_deepseek._queue_request({'id':'duplicate'})
    assert state['deepseek_pending_request'] == {'id':'original'}
    state.pop('deepseek_pending_request')
    state['deepseek_busy'] = True
    assert not ui_deepseek._queue_request({'id':'during-stream'})
    assert 'deepseek_pending_request' not in state


def test_panel_redraw_retains_draft_and_parameters_without_request(monkeypatch):
    calls = []
    monkeypatch.setattr('quant_lab.ui_deepseek.DeepSeekClient', lambda *a: calls.append(a))
    app = AppTest.from_file(Path(__file__).parents[1] / 'app.py', default_timeout=30).run()
    app.button(key='deepseek_panel_toggle').click().run()
    app.text_area(key='deepseek_prompt').input('尚未发送的中文研究草稿\n第二行').run()
    parameters = {key:app.session_state[key] for key in ('market_selection','history_preset')}
    app.button(key='manual_panel_toggle').click().run()
    app.button(key='deepseek_panel_close').click().run()
    app.button(key='deepseek_panel_toggle').click().run()
    app.run()
    assert not app.exception and not calls
    assert app.text_area(key='deepseek_prompt').value == '尚未发送的中文研究草稿\n第二行'
    assert {key:app.session_state[key] for key in parameters} == parameters


def test_empty_failed_stream_is_visible_and_does_not_resend(monkeypatch):
    from quant_lab.deepseek import Answer
    calls = []
    class Client:
        def __init__(self, key):
            pass
        def stream_with_recovery(self, *args, **kwargs):
            calls.append(args)
            answer = Answer("mock", error="模拟空回复失败")
            return answer, iter(())
    monkeypatch.setattr('quant_lab.ui_deepseek.DeepSeekClient', Client)
    app = AppTest.from_file(Path(__file__).parents[1] / 'app.py', default_timeout=30).run()
    app.session_state['deepseek_api_key'] = 'sk-local-test'
    app.session_state['ds_model_manual'] = 'mock'
    app.button(key='deepseek_panel_toggle').click().run()
    app.text_area(key='deepseek_prompt').input('失败也需要清楚反馈').run()
    app.button(key='deepseek_send').click().run()
    assert not app.exception
    assert any('模拟空回复失败' in error.value for error in app.error)
    assert len(calls) == 1
    app.run()
    assert len(calls) == 1
