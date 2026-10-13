"""A Release must stay unpublished when an uploaded asset fails verification."""

import hashlib
import json
import sys

import pytest

from tools import publish_release


@pytest.mark.parametrize("valid_digest", [True, False])
def test_release_is_published_only_after_asset_verification(tmp_path, monkeypatch, valid_digest):
    artifact = tmp_path / "installer.exe"
    artifact.write_bytes(b"small release test artifact")
    notes = tmp_path / "notes.md"
    notes.write_text("Test release notes", encoding="utf-8")
    sha = "a" * 40
    calls = []

    def fake_git(*args):
        if args[0] == "remote":
            return "https://github.com/example/quant-lab.git"
        return "" if args[0] == "status" else sha

    class Response:
        ok = True

        def __init__(self, value):
            self.value = value

        def json(self):
            return self.value

    class Session:
        headers = {}

        def request(self, method, url, **kwargs):
            calls.append((method, kwargs.get("json")))
            if url.endswith("/git/ref/tags/v1.0.0"):
                return Response({"object": {"type": "commit", "sha": sha}})
            if method == "GET" and url.endswith("/release/1"):
                return Response({"url": url, "draft": False, "tag_name": "v1.0.0", "prerelease": True,
                                 "html_url": "https://github.com/example/releases/tag/v1.0.0",
                                 "assets": [{"name": artifact.name, "size": artifact.stat().st_size,
                                             "digest": f"sha256:{hashlib.sha256(artifact.read_bytes()).hexdigest()}",
                                             "browser_download_url": "https://github.com/example/releases/download/v1.0.0/installer.exe"}]})
            if method == "GET":
                return Response([])
            if "uploads.github.com" in url:
                digest = hashlib.sha256(artifact.read_bytes()).hexdigest() if valid_digest else "wrong"
                return Response({"size": artifact.stat().st_size, "digest": f"sha256:{digest}",
                                 "browser_download_url": "https://github.com/example/asset"})
            return Response({"assets": [], "upload_url": "https://uploads.github.com/example{?name}",
                             "url": "https://api.github.com/example/release/1", "prerelease": True,
                             "html_url": "https://github.com/example/releases/tag/v1.0.0"})

    monkeypatch.setattr(publish_release, "git", fake_git)
    monkeypatch.setattr(publish_release, "credentials", lambda: "test-placeholder")
    monkeypatch.setattr(publish_release.requests, "Session", Session)
    monkeypatch.setattr(sys, "argv", ["publish_release.py", "--tag", "v1.0.0",
                                     "--notes", str(notes), "--assets", str(artifact), "--prerelease",
                                     "--receipt", str(tmp_path / "receipt.json")])
    if valid_digest:
        publish_release.main()
        receipt = json.loads((tmp_path / "receipt.json").read_text(encoding="utf-8"))
        assert "/download/v1.0.0/" in receipt["assets"][0]["url"]
    else:
        with pytest.raises(RuntimeError, match="SHA-256"):
            publish_release.main()
    publish_calls = [payload for method, payload in calls
                     if method == "PATCH" and payload == {"draft": False}]
    assert len(publish_calls) == int(valid_digest)
