"""The frozen app uses its verified private browser, even with hostile overrides."""
import hashlib
import json
from types import SimpleNamespace
import pytest
import desktop_launcher as launcher


def package(tmp_path):
    runtime=tmp_path/'webview2';runtime.mkdir()
    for name in ('msedgewebview2.exe','msedge.dll','icudtl.dat','resources.pak','v8_context_snapshot.bin'):
        (runtime/name).write_bytes(b'test-fixture')
    manifest={'version':'test','exe_sha256':hashlib.sha256(b'test-fixture').hexdigest()}
    (tmp_path/'webview2-runtime.json').write_text(json.dumps(manifest),encoding='utf-8')
    return runtime


def test_frozen_selects_private_runtime_and_replaces_environment(tmp_path,monkeypatch):
    runtime=package(tmp_path)
    monkeypatch.setattr(launcher,'resource_root',lambda:tmp_path)
    monkeypatch.setattr(launcher.sys,'frozen',True,raising=False)
    monkeypatch.setenv('WEBVIEW2_BROWSER_EXECUTABLE_FOLDER','invalid-system-runtime')
    view=SimpleNamespace(settings={})
    assert launcher.configure_webview_runtime(view)==runtime
    assert view.settings['WEBVIEW2_RUNTIME_PATH']==str(runtime)
    assert launcher.os.environ['WEBVIEW2_BROWSER_EXECUTABLE_FOLDER']==str(runtime)


@pytest.mark.parametrize('damage',['missing','hash','resources'])
def test_frozen_runtime_damage_never_falls_back(tmp_path,monkeypatch,damage):
    runtime=package(tmp_path)
    if damage=='missing': (runtime/'msedgewebview2.exe').unlink()
    elif damage=='hash': (runtime/'msedgewebview2.exe').write_bytes(b'bad')
    else: (runtime/'msedge.dll').unlink()
    monkeypatch.setattr(launcher,'resource_root',lambda:tmp_path)
    monkeypatch.setattr(launcher.sys,'frozen',True,raising=False)
    with pytest.raises(launcher.LaunchError,match='重新安装'):
        launcher.configure_webview_runtime(SimpleNamespace(settings={}))


def test_source_without_private_runtime_keeps_system_mode(tmp_path,monkeypatch):
    monkeypatch.setattr(launcher,'resource_root',lambda:tmp_path)
    monkeypatch.delattr(launcher.sys,'frozen',raising=False)
    assert launcher.configure_webview_runtime(SimpleNamespace(settings={})) is None
