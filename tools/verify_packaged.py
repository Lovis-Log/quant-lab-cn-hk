"""Optional real-browser smoke test for the built onedir EXE.

Requires Playwright Python and a locally installed Chrome. The application
bundle itself does not depend on either one.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "QuantLab" / "QuantLab.exe"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def chrome_path() -> Path:
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("Chrome is required only for this optional browser test.")


def wait_for_service(port: int, child: subprocess.Popen, timeout: float = 40) -> None:
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError(f"Packaged service exited with code {child.returncode}")
        try:
            with opener.open(f"http://127.0.0.1:{port}/_stcore/health", timeout=0.7) as response:
                if response.status == 200 and response.read().strip() == b"ok":
                    return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError("Packaged Streamlit service did not become healthy")


def main() -> None:
    if not EXE.is_file():
        raise FileNotFoundError(EXE)
    from playwright.sync_api import sync_playwright

    data_dir = Path(tempfile.mkdtemp(prefix="quantlab-packaged-"))
    env = os.environ.copy()
    env["QUANT_LAB_DATA_DIR"] = str(data_dir)
    port = free_port()
    log_path = data_dir / "packaged-child.log"
    child: subprocess.Popen | None = None
    offline = "--offline" in sys.argv[1:]
    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            child = subprocess.Popen(
                [str(EXE), "--serve", "--port", str(port)],
                cwd=data_dir, env=env, stdin=subprocess.DEVNULL,
                stdout=log_file, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            wait_for_service(port, child)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path=str(chrome_path()), headless=True,
                    args=["--no-sandbox", "--disable-gpu"],
                )
                try:
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded")
                    page.get_by_text("市场数据实验室").wait_for(timeout=30_000)
                    if offline:
                        page.get_by_role("button", name="暂停自动刷新").click()
                        page.get_by_role("button", name="加入自选").click()
                        page.get_by_text("已加入 A 股 600519").wait_for(timeout=10_000)
                        page.get_by_text("Quant Academy", exact=True).click()
                        page.get_by_text("金融数学实验室").wait_for(timeout=10_000)
                        course = page.get_by_role("combobox", name="选择课程")
                        course.click()
                        course.fill("夏普")
                        page.get_by_role("option", name="6. 夏普比率").click()
                        page.get_by_text("年化夏普示例").wait_for(timeout=10_000)
                        page.get_by_text("研究笔记", exact=True).click()
                        page.get_by_text("尚无已保存实验").wait_for(timeout=10_000)
                        database = data_dir / "research.sqlite3"
                        with sqlite3.connect(database) as db:
                            assert db.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0] == 1
                    else:
                        page.get_by_role("button", name="加载真实历史日线").click()
                        page.get_by_text("已加载真实历史数据").wait_for(timeout=30_000)
                        page.get_by_text("历史回测", exact=True).click()
                        page.get_by_role("button", name="运行历史回测").click()
                        page.get_by_text("策略累计收益").wait_for(timeout=30_000)
                    if page.locator('[data-testid="stException"]').count():
                        raise RuntimeError("Streamlit displayed an exception in the packaged app")
                finally:
                    browser.close()
        print(json.dumps({"service_ready": True, "browser_loaded": True,
                          "offline_mode": offline,
                          "real_history_loaded": not offline, "backtest_loaded": not offline,
                          "port": port, "data_dir": str(data_dir)}, ensure_ascii=False))
    except Exception:
        if log_path.exists():
            print("Child log tail:\n" + "\n".join(
                log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-15:]
            ))
        raise
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        print(json.dumps({"child_stopped": child is None or child.poll() is not None}))


if __name__ == "__main__":
    main()
