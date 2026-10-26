"""Windows desktop shell invariants without opening a GUI in pytest."""

import os
from pathlib import Path
import socket
import hashlib

import pytest


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows desktop launcher")

if os.name == "nt":
    from desktop_launcher import (LaunchError, choose_loopback_port, managed_attachment_path,
                                  prepare_user_data, save_managed_attachment_copy,
                                  single_instance)


def test_user_files_live_in_writable_profile_and_config_is_preserved(tmp_path: Path) -> None:
    prepare_user_data(tmp_path)
    user_config = tmp_path / ".streamlit" / "config.toml"
    assert user_config.is_file()
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "webview").is_dir()
    user_config.write_text("# user setting\n", encoding="utf-8")
    prepare_user_data(tmp_path)
    assert user_config.read_text(encoding="utf-8") == "# user setting\n"


def test_instance_lock_prevents_second_desktop_parent(tmp_path: Path) -> None:
    with single_instance(tmp_path):
        with pytest.raises(LaunchError, match="已在运行"):
            with single_instance(tmp_path):
                pytest.fail("second instance obtained the same lock")
    with single_instance(tmp_path):
        pass


def test_random_port_is_not_the_fixed_web_port() -> None:
    ports = {choose_loopback_port() for _ in range(3)}
    assert all(0 < port < 65536 for port in ports)


def test_shutdown_handshake_stops_owned_running_cpu_process(tmp_path):
    import time
    from desktop_launcher import start_shutdown_listener
    from quant_lab.jobs import job_manager, JobState
    runtime = tmp_path / "cache" / "runtime"
    runtime.mkdir(parents=True)
    signal = runtime / "test.stop"
    manager = job_manager()
    identifier = manager.submit("desktop-test", "long", "one", time.sleep, 30, cpu=True)
    deadline = time.monotonic() + 4
    while identifier not in manager._processes and time.monotonic() < deadline:
        time.sleep(.01)
    process = manager._processes[identifier]
    listener = start_shutdown_listener(signal, tmp_path)
    signal.write_text("shutdown", encoding="ascii")
    listener.join(timeout=6)
    assert not listener.is_alive()
    assert signal.with_suffix(".done").read_text(encoding="ascii") == "workers-stopped"
    assert process.poll() is not None
    assert manager.get(identifier, "desktop-test").state == JobState.CANCELLED
    with pytest.raises(ValueError):
        start_shutdown_listener(tmp_path / "outside.stop", tmp_path)


def test_existing_8501_listener_keeps_its_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as existing:
        try:
            existing.bind(("127.0.0.1", 8501))
            existing.listen()
        except OSError:
            # Another application is already proving that 8501 is occupied.
            pass
        assert choose_loopback_port() != 8501


def test_managed_attachment_path_stays_in_library_and_checks_hash(tmp_path: Path) -> None:
    attachment = tmp_path / "notes" / "attachments" / "one.pdf"
    attachment.parent.mkdir(parents=True)
    attachment.write_bytes(b"%PDF-1.4\n%%EOF")
    digest = hashlib.sha256(attachment.read_bytes()).hexdigest()

    assert managed_attachment_path("notes/attachments/one.pdf", digest, tmp_path) == attachment
    with pytest.raises(LaunchError, match="校验失败"):
        managed_attachment_path("notes/attachments/one.pdf", "0" * 64, tmp_path)
    with pytest.raises(LaunchError, match="不属于"):
        managed_attachment_path("../outside.pdf", digest, tmp_path)


def test_save_managed_attachment_copy_preserves_source_and_verifies_bytes(tmp_path: Path) -> None:
    attachment = tmp_path / "library" / "notes" / "attachments" / "one.pdf"
    attachment.parent.mkdir(parents=True)
    data = b"%PDF-1.4\nsource data\n%%EOF"
    attachment.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    destination = tmp_path / "export" / "copy.pdf"
    destination.parent.mkdir()

    assert save_managed_attachment_copy(
        "notes/attachments/one.pdf", digest, destination, tmp_path / "library"
    ) == destination
    assert destination.read_bytes() == data and attachment.read_bytes() == data
    with pytest.raises(LaunchError, match="校验失败"):
        save_managed_attachment_copy(
            "notes/attachments/one.pdf", "0" * 64, destination, tmp_path / "library"
        )
    assert destination.read_bytes() == data
    with pytest.raises(LaunchError, match="不能覆盖"):
        save_managed_attachment_copy(
            "notes/attachments/one.pdf", digest, attachment, tmp_path / "library"
        )
