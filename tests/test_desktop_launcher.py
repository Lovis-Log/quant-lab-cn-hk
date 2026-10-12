"""Windows desktop shell invariants without opening a GUI in pytest."""

import os
from pathlib import Path
import socket

import pytest


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows desktop launcher")

if os.name == "nt":
    from desktop_launcher import LaunchError, choose_loopback_port, prepare_user_data, single_instance


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


def test_existing_8501_listener_keeps_its_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as existing:
        try:
            existing.bind(("127.0.0.1", 8501))
            existing.listen()
        except OSError:
            # Another application is already proving that 8501 is occupied.
            pass
        assert choose_loopback_port() != 8501
