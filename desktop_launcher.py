"""Start Quant Lab in a private pywebview window on Windows.

The same entry point runs as a parent (desktop window) and as its own isolated
Streamlit child (``--serve``). This also works when sys.executable is a frozen
PyInstaller EXE, so no system Python installation is needed.
"""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import msvcrt
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from typing import Iterator
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


APP_TITLE = "Quant Lab CN/HK"
HOST = "127.0.0.1"
STARTUP_TIMEOUT_SECONDS = 35
WEBVIEW_TIMEOUT_SECONDS = 30
MAX_PORT_ATTEMPTS = 3
HEALTH_PATH = "/_stcore/health"
LOGGER = logging.getLogger("quant_lab.desktop")


class LaunchError(RuntimeError):
    """A recoverable desktop startup problem for the user to read."""


def resource_root() -> Path:
    """PyInstaller's bundled resource root, or the source checkout."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()


def user_data_dir() -> Path:
    from quant_lab.paths import user_data_dir as shared_user_data_dir

    return shared_user_data_dir()


def prepare_user_data(root: Path) -> None:
    """All mutable files live outside the read-only installation directory."""
    try:
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "webview").mkdir(parents=True, exist_ok=True)
        with (root / ".write-test").open("w", encoding="utf-8") as test_file:
            test_file.write("ok")
        (root / ".write-test").unlink()
        bundled_config = resource_root() / ".streamlit" / "config.toml"
        if not bundled_config.is_file():
            raise LaunchError(f"缺少 Streamlit 主题配置：{bundled_config}")
        user_config = root / ".streamlit" / "config.toml"
        user_config.parent.mkdir(exist_ok=True)
        if not user_config.exists():
            shutil.copyfile(bundled_config, user_config)
    except OSError as exc:
        raise LaunchError(f"无法写入用户数据目录：{root}\n{exc}") from exc


def configure_logging(root: Path) -> None:
    LOGGER.setLevel(logging.INFO)
    if not LOGGER.handlers:
        handler = RotatingFileHandler(
            root / "logs" / "launcher.log", maxBytes=1_000_000,
            backupCount=2, encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOGGER.addHandler(handler)
        # Capture WebView2 initialization and JS-bridge diagnostics, which were
        # absent from the earlier timeout probe's launcher log.
        renderer_logger = logging.getLogger("pywebview")
        renderer_logger.setLevel(logging.INFO)
        renderer_logger.addHandler(handler)


@contextmanager
def single_instance(root: Path) -> Iterator[None]:
    """A per-user byte lock prevents two desktop parents from starting servers."""
    lock_path = root / "instance.lock"
    with lock_path.open("a+b") as lock_file:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()
        lock_file.seek(0)
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise LaunchError("Quant Lab CN/HK 已在运行，请切换到已有窗口。") from exc
        try:
            yield
        finally:
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


def choose_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


def app_script() -> Path:
    path = resource_root() / "app.py"
    if not path.is_file():
        raise LaunchError(f"缺少应用入口文件：{path}")
    return path


def managed_attachment_path(relative_path: str, expected_sha256: str,
                            root: Path | None = None) -> Path:
    """Resolve and verify one managed attachment before handing it to Windows."""
    library = (root or user_data_dir()).resolve()
    target = (library / str(relative_path)).resolve()
    try:
        target.relative_to(library)
    except ValueError:
        raise LaunchError("附件路径不属于当前资料库。") from None
    if not target.is_file():
        raise LaunchError("附件文件不存在。")
    hasher = hashlib.sha256()
    with target.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    digest = hasher.hexdigest()
    if digest != str(expected_sha256):
        raise LaunchError("附件校验失败，文件可能已被外部修改。")
    return target


def save_managed_attachment_copy(relative_path: str, expected_sha256: str,
                                 destination: Path, root: Path | None = None) -> Path:
    """Copy a verified attachment to a selected path without leaving partial files."""
    source = managed_attachment_path(relative_path, expected_sha256, root)
    destination = Path(destination).resolve()
    if destination == source:
        raise LaunchError("不能覆盖资料库中的原附件。")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        hasher = hashlib.sha256()
        with os.fdopen(descriptor, "wb") as copy, source.open("rb") as original:
            for block in iter(lambda: original.read(1024 * 1024), b""):
                copy.write(block)
                hasher.update(block)
        if hasher.hexdigest() != expected_sha256:
            raise LaunchError("附件校验失败，文件可能已被外部修改。")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def child_command(port: int) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--serve", "--port", str(port)]
    return [sys.executable, str(Path(__file__).resolve()), "--serve", "--port", str(port)]


def serve_streamlit(port: int) -> int:
    """Use Streamlit's installed CLI in this dedicated child process."""
    root = user_data_dir()
    prepare_user_data(root)
    os.environ["QUANT_LAB_DATA_DIR"] = str(root)
    os.chdir(root)
    from streamlit.web import cli

    arguments = [
        "run", str(app_script()),
        "--global.developmentMode=false",
        f"--server.address={HOST}",
        f"--server.port={port}",
        "--server.headless=true",
        "--server.enableCORS=true",
        "--server.enableXsrfProtection=true",
        "--server.fileWatcherType=none",
        "--browser.serverAddress=127.0.0.1",
        "--browser.gatherUsageStats=false",
    ]
    cli.main(args=arguments, prog_name="streamlit", standalone_mode=False)
    return 0


def _health_ok(port: int) -> bool:
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(f"http://{HOST}:{port}{HEALTH_PATH}", timeout=0.6) as response:
            return response.status == 200 and response.read(32).strip() == b"ok"
    except (OSError, URLError):
        return False


def _recent_child_log(root: Path) -> str:
    try:
        lines = (root / "logs" / "streamlit.log").read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        return "\n".join(lines[-8:])[-1200:]
    except OSError:
        return ""


def start_service(root: Path, timeout: float = STARTUP_TIMEOUT_SECONDS) -> tuple[subprocess.Popen, int]:
    """Start only our own child; retry if another process wins a port race."""
    for attempt in range(MAX_PORT_ATTEMPTS):
        port = choose_loopback_port()
        environment = os.environ.copy()
        environment["QUANT_LAB_DATA_DIR"] = str(root)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with (root / "logs" / "streamlit.log").open("a", encoding="utf-8") as log_file:
            log_file.write(f"\n=== launch attempt {attempt + 1} port {port} ===\n")
            log_file.flush()
            child = subprocess.Popen(
                child_command(port), cwd=root, env=environment,
                stdin=subprocess.DEVNULL, stdout=log_file, stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )
        LOGGER.info("Started Streamlit child pid=%s port=%s", child.pid, port)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if child.poll() is not None:
                detail = _recent_child_log(root)
                LOGGER.error("Streamlit child exited early: %s", detail)
                break
            if _health_ok(port) and child.poll() is None:
                LOGGER.info("Streamlit health check passed on %s:%s", HOST, port)
                return child, port
            time.sleep(0.2)
        else:
            stop_service(child)
            raise LaunchError(
                f"本地服务在 {timeout:.0f} 秒内未就绪。请查看日志：{root / 'logs' / 'streamlit.log'}"
            )
        stop_service(child)
    raise LaunchError(
        "Streamlit 服务未能启动。请检查端口、防火墙和依赖；"
        f"详细日志：{root / 'logs' / 'streamlit.log'}"
    )


def stop_service(child: subprocess.Popen | None) -> None:
    """Terminate the exact Popen child this launcher created, never by name/port."""
    if child is None or child.poll() is not None:
        return
    LOGGER.info("Stopping Streamlit child pid=%s", child.pid)
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        LOGGER.warning("Child did not exit after terminate; killing pid=%s", child.pid)
        child.kill()
        child.wait(timeout=5)


def _write_probe_result(payload: dict[str, object]) -> None:
    target = os.environ.get("QUANT_LAB_SMOKE_RESULT")
    if target:
        Path(target).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def show_error(message: str) -> None:
    LOGGER.error(message)
    if os.environ.get("QUANT_LAB_SMOKE_RESULT"):
        _write_probe_result({"error": message})
        print(message, file=sys.stderr)
        return
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, 0x10)
    else:
        print(message, file=sys.stderr)


def run_desktop(smoke_test: bool = False) -> int:
    root = user_data_dir()
    prepare_user_data(root)
    configure_logging(root)
    child: subprocess.Popen | None = None
    port: int | None = None
    loaded = threading.Event()
    shown = threading.Event()
    before_load = threading.Event()
    closed = threading.Event()
    webview_timed_out = threading.Event()
    test_seconds = os.environ.get("QUANT_LAB_GUI_TEST_SECONDS")
    with single_instance(root):
        try:
            child, port = start_service(root)
            if smoke_test:
                LOGGER.info("Headless service smoke test passed")
                return 0
            import webview

            probe_debug_port = None
            if os.environ.get("QUANT_LAB_GUI_PROBE") == "1":
                probe_debug_port = choose_loopback_port()
                webview.settings["REMOTE_DEBUGGING_PORT"] = probe_debug_port
                _write_probe_result({"ready": True, "port": port, "debug_port": probe_debug_port,
                                     "state": "starting", "data_dir": str(root)})

            class DesktopAPI:
                _window = None
                def close(self):
                    if self._window:
                        threading.Thread(target=self._window.destroy, daemon=True).start()
                def choose_data_folder(self):
                    if not self._window:
                        return None
                    result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
                    return str(result[0]) if result else None
                def open_managed_attachment(self, relative_path, expected_sha256):
                    target = managed_attachment_path(relative_path, expected_sha256)
                    if os.environ.get("QUANT_LAB_GUI_PROBE") != "1":
                        os.startfile(target)
                    return True
                def save_managed_attachment(self, relative_path, expected_sha256, original_name):
                    if not self._window:
                        raise LaunchError("桌面窗口尚未就绪。")
                    name = Path(str(original_name)).name
                    if not name or name in {".", ".."}:
                        raise LaunchError("附件名称无效。")
                    if os.environ.get("QUANT_LAB_GUI_PROBE") == "1":
                        destination = user_data_dir() / "validation-export" / name
                        destination.parent.mkdir(parents=True, exist_ok=True)
                    else:
                        selected = self._window.create_file_dialog(
                            webview.FileDialog.SAVE, save_filename=name,
                        )
                        if not selected:
                            return {"status": "cancelled"}
                        destination = Path(selected[0])
                    saved = save_managed_attachment_copy(
                        relative_path, expected_sha256, destination,
                    )
                    return {"status": "saved", "name": saved.name}
            probe_api = DesktopAPI()

            url = f"http://{HOST}:{port}"
            window = webview.create_window(
                APP_TITLE, url, width=1440, height=900,
                min_size=(1100, 700), background_color="#090D16",
                js_api=probe_api,
            )
            probe_api._window = window
            window.events.shown += shown.set
            window.events.before_load += before_load.set
            window.events.loaded += loaded.set
            window.events.closed += closed.set

            def monitor_webview() -> None:
                if not loaded.wait(WEBVIEW_TIMEOUT_SECONDS) and not closed.is_set():
                    webview_timed_out.set()
                    LOGGER.error("WebView2 did not load the local page within %s seconds", WEBVIEW_TIMEOUT_SECONDS)
                    window.destroy()

            monitor = threading.Thread(target=monitor_webview, daemon=True)
            monitor.start()
            if test_seconds:
                timer = threading.Timer(float(test_seconds), window.destroy)
                timer.daemon = True
                timer.start()
            icon = resource_root() / "assets" / "quantlab.ico"
            try:
                webview.start(
                    gui="edgechromium", private_mode=False,
                    storage_path=str(root / "webview"),
                    icon=str(icon) if icon.is_file() else None,
                )
            except Exception as exc:
                raise LaunchError(
                    "无法创建桌面窗口。请确认已安装 Microsoft Edge WebView2 Runtime。"
                    f"\n详细原因：{exc}"
                ) from exc
            LOGGER.info(
                "Webview loop ended; shown=%s before_load=%s loaded=%s",
                shown.is_set(), before_load.is_set(), loaded.is_set(),
            )
            if webview_timed_out.is_set():
                raise LaunchError(
                    "桌面窗口未能加载本地页面。请确认 Microsoft Edge WebView2 Runtime 可用，"
                    f"并查看日志：{root / 'logs' / 'launcher.log'}"
                )
            return 0
        finally:
            stop_service(child)
            if smoke_test or test_seconds:
                _write_probe_result({
                    "ready": bool(port), "port": port,
                    "child_stopped": child is None or child.poll() is not None,
                    "app_path": str(app_script()),
                    "data_dir": str(root), "frozen": bool(getattr(sys, "frozen", False)),
                    "webview_shown": shown.is_set(),
                    "webview_before_load": before_load.is_set(),
                    "webview_loaded": loaded.is_set(),
                    "debug_port": locals().get("probe_debug_port"),
                })


def main() -> int:
    if os.name != "nt":
        raise LaunchError("桌面启动器目前只支持 Windows。")
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--serve":
        if len(arguments) != 3 or arguments[1] != "--port":
            raise LaunchError("服务启动参数无效。")
        return serve_streamlit(int(arguments[2]))
    return run_desktop(smoke_test=arguments == ["--smoke-test"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        is_service_child = sys.argv[1:2] == ["--serve"]
        try:
            root = user_data_dir()
            root.mkdir(parents=True, exist_ok=True)
            configure_logging(root)
            LOGGER.exception("Desktop launch failed")
        except OSError:
            pass
        if is_service_child:
            print(f"Streamlit child failed: {error}", file=sys.stderr)
        else:
            show_error(str(error) if isinstance(error, LaunchError) else f"启动失败：{error}")
        sys.exit(1)
