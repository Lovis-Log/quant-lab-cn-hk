"""Focused regressions for compact navigation, selection, and the startup handshake."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import navigate, finish_background_jobs
from conftest import select_security
from quant_lab.desktop_loading import StartupOverlay
from quant_lab.navigation import navigation_values, comparison_selection, SECTIONS
from quant_lab.workspaces import WorkspaceStore, restore_values

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_v1_workspace_is_read_without_write_then_backed_up_on_first_v2_save(tmp_path):
    target = tmp_path / "workspace-presets.json"
    original = json.dumps({"format":1, "active":"单股票研究", "profiles":{
        "单股票研究":{"nav_page":"研究实验台", "market_selection":"港股"}}}, ensure_ascii=False)
    target.write_text(original, encoding="utf-8")
    store = WorkspaceStore(target)
    values = restore_values(store.load()["profiles"]["单股票研究"])
    assert values["nav_section"] == "研究工作台" and values["research_page"] == "研究实验台"
    assert values["market_selection"] == values["compare_market"] == "港股"
    assert target.read_text(encoding="utf-8") == original
    store.save("单股票研究", {**values, "market_selection":"美股", "compare_market":"美股"})
    assert target.with_name(target.name + ".v1.bak").read_text(encoding="utf-8") == original
    assert store.load()["format"] == 2
    store.save("学习", {})
    assert target.with_name(target.name + ".v1.bak").read_text(encoding="utf-8") == original
    assert navigation_values({"nav_page":"美股研究"})["market_selection"] == "美股"


def test_selection_normalizes_deduplicates_and_enforces_draft_limit():
    assert comparison_selection("港股", "700，941", ("00700", "00005")) == ("00700", "00941", "00005")
    assert comparison_selection("A 股", "") == ()
    assert comparison_selection("A 股", "600519") == ("600519",)
    with pytest.raises(ValueError, match="最多"):
        comparison_selection("A 股", ",".join(f"6000{i:02}" for i in range(11)))
    with pytest.raises(ValueError):
        comparison_selection("美股", "AAPL,MSFT")


def test_startup_overlay_requires_meaningful_view_and_is_idempotent(monkeypatch):
    overlay = StartupOverlay()
    hidden = []
    monkeypatch.setattr(overlay, "_hide", lambda: hidden.append(True))
    assert not overlay.mark_ready("health_ok") and not overlay.ready.is_set()
    assert overlay.mark_ready("library_setup") and overlay.ready.is_set()
    timestamp = overlay.ready_at
    assert overlay.mark_ready("workspace") and overlay.ready_at == timestamp
    assert overlay.view == "library_setup" and hidden == [True]


def test_candidate_edit_market_drafts_and_us_gate_do_not_load_prices(monkeypatch):
    calls = []
    monkeypatch.setattr("quant_lab.comparison.fetch_history_cached", lambda *args, **kwargs: calls.append(args))
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert app.sidebar.radio(key="nav_section").options == list(SECTIONS)
    assert not any(item.label == "工作区方案" for item in app.expander)
    navigate(app, "多股票比较")
    select_security(app, "compare_codes", "600519,600036,000001")
    assert app.session_state["compare_codes"] == "600519,600036,000001"
    assert not app.get("dialog")
    app.sidebar.selectbox(key="compare_market").set_value("港股").run()
    select_security(app, "compare_codes", "00700,00005")
    app.sidebar.selectbox(key="compare_market").set_value("A 股").run()
    assert app.session_state["compare_codes"] == "600519,600036,000001"
    app.sidebar.selectbox(key="compare_market").set_value("美股").run()
    assert not app.exception and not calls
    assert any("显式加载后比较真实美股日线" in message.value for message in app.info)
    assert app.session_state["_current_ai_context"]["currency"] == "USD"
    assert "data_fingerprint" not in app.session_state["_current_ai_context"]


def test_history_fullscreen_reuses_all_rows_and_never_fetches_again(monkeypatch):
    from test_workspaces import sample_bundle
    calls = []
    def fetch(*args, **kwargs):
        calls.append(args)
        return sample_bundle()
    monkeypatch.setattr("quant_lab.ui.fetch_history", fetch)
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.sidebar.button[0].click().run()
    finish_background_jobs(app)
    app.button(key="history_fullscreen_open").click().run()
    assert app.session_state["history_table_fullscreen"] is True
    assert len(app.dataframe[0].value) == 100
    app.button(key="history_fullscreen_close").click().run()
    assert not app.session_state["history_table_fullscreen"] and len(calls) == 1
    assert not app.exception


def test_refresh_preference_reregisters_market_fragment_without_fetch(monkeypatch):
    calls = []
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *args, **kwargs: calls.append(args))
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.button(key="settings_toggle").click().run()
    app.toggle(key="refresh_enabled").set_value(False).run()
    assert app.button(key="refresh_pause").label == "恢复自动刷新"
    app.selectbox(key="refresh_interval_seconds").set_value(600).run()
    assert app.session_state["refresh_interval_seconds"] == 600
    assert not app.exception and not calls


def test_inline_picker_rejects_bad_client_values_and_keeps_canonical_codes():
    from quant_lab.ui_security_picker import commit_selection
    assert commit_selection("港股", "compare_codes", True, ["700", "00700", "941"]) == "00700,00941"
    assert commit_selection("A 股", "symbol_A 股", False, ["SH600519"]) == "600519"
    for payload in ("600519", [None], ["600519", "000001"]):
        with pytest.raises(ValueError):
            commit_selection("A 股", "symbol_A 股", False, payload)


def test_research_parameters_are_collapsed_without_losing_selection():
    app = AppTest.from_file(APP, default_timeout=30).run()
    select_security(app, "symbol_A 股", "000001")
    for page in ("策略实验室", "Quant Academy", "市场数据"):
        navigate(app, page)
        assert next(item for item in app.expander if item.label == "研究参数").proto.expanded is False
        assert app.session_state["symbol_A 股"] == "000001"
        assert not app.exception
