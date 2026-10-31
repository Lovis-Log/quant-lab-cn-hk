"""UI tests use offline securities names; no upstream API is needed."""

import pytest


@pytest.fixture(autouse=True)
def offline_ui_names(monkeypatch, tmp_path):
    # Tests must never migrate or modify the real user's research archive.
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path / "isolated-user-data"))
    from quant_lab import names
    from quant_lab import credentials
    monkeypatch.setattr(names, "security_name", lambda market, symbol, **kwargs: "测试证券")
    monkeypatch.setattr(names, "cached_security_name", lambda market, symbol, **kwargs: "测试证券")
    # Ordinary tests must not inspect the developer's real Windows vault.
    monkeypatch.setattr(credentials, "load_key", lambda: None)
    yield
    from quant_lab.jobs import shutdown_jobs
    shutdown_jobs()


def finish_background_jobs(app, timeout=15):
    """AppTest has no browser timer: explicitly pump real async job completion."""
    import time
    deadline = time.monotonic() + timeout
    while app.session_state["_task_tickets"]:
        assert not app.exception
        if time.monotonic() >= deadline:
            pytest.fail("background UI tasks did not settle")
        time.sleep(.02)
        app.run()
    return app


def navigate(app, page):
    """Exercise the visible compact navigation while retaining legacy test intent."""
    from quant_lab.navigation import navigation_values, RESEARCH
    values = navigation_values({"nav_page": page})
    app.sidebar.radio(key="nav_section").set_value(values["nav_section"]).run()
    if page == "美股研究":
        app.sidebar.selectbox(key="market_selection").set_value("美股").run()
    elif page in RESEARCH:
        app.radio(key="research_page").set_value(page).run()
    return app


def select_security(app, key, text):
    """AppTest cannot drive component JavaScript; DOM coverage uses real WebView2."""
    from quant_lab.ui_security_picker import commit_selection
    multiple = key == "compare_codes"
    market = app.session_state["compare_market"] if multiple else key.removeprefix("symbol_")
    app.session_state[key] = commit_selection(market, key, multiple, text.replace("，", ",").split(","))
    return app.run()
