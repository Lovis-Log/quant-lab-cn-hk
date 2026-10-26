"""Concurrency tests use events, separate scopes, and actual spawned workers."""

from threading import Event
import time

import pandas as pd
import pytest

from quant_lab.jobs import JobManager, JobState, TERMINAL


def wait(manager, identifier, scope="one"):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        job = manager.get(identifier, scope)
        if job.state in TERMINAL:
            return job
        time.sleep(.01)
    pytest.fail("job did not finish")


def squared(value):
    return value * value


def forever():
    time.sleep(30)


def has_ui_module():
    import sys
    return "streamlit" in sys.modules


def test_scope_dedup_cancel_and_late_result_cannot_publish():
    manager = JobManager()
    gate, entered = Event(), Event()
    def slow():
        entered.set()
        gate.wait(4)
        return 42
    try:
        identifier = manager.submit("one", "history", "a", slow)
        assert entered.wait(2)
        assert manager.submit("one", "history", "a", slow) == identifier
        assert manager.get(identifier, "two") is None
        assert not manager.cancel(identifier, "two")
        assert manager.cancel(identifier, "one")
        gate.set()
        assert wait(manager, identifier).state == JobState.CANCELLED
        assert manager.get(identifier, "one").result is None
        assert manager.submit("one", "history", "a", lambda: 7) != identifier
        other = manager.submit("two", "history", "a", lambda: 8)
        assert wait(manager, other, "two").result == 8
    finally:
        gate.set()
        manager.close()


def test_inputs_are_copied_and_error_details_are_not_exposed():
    manager = JobManager(io_workers=1)
    gate = Event()
    try:
        first = manager.submit("one", "hold", "a", gate.wait, 3)
        frame = pd.DataFrame({"price": [10.]})
        identifier = manager.submit("one", "copy", "a", lambda data: float(data.price.iloc[0]), frame)
        frame.iloc[0, 0] = 999
        gate.set()
        assert wait(manager, identifier).result == 10
        def bad():
            raise RuntimeError("sk-SECRET cannot appear")
        failure = wait(manager, manager.submit("one", "bad", "a", bad))
        assert failure.state == JobState.FAILED
        assert "SECRET" not in failure.error
    finally:
        gate.set()
        manager.close()


def test_real_cpu_process_and_running_cancellation():
    manager = JobManager()
    try:
        result = wait(manager, manager.submit("one", "math", "x", squared, 9, cpu=True))
        assert result.result == 81 and result.state == JobState.SUCCEEDED
        assert wait(manager, manager.submit("one", "isolation", "x", has_ui_module, cpu=True)).result is False
        identifier = manager.submit("one", "math", "long", forever, cpu=True)
        deadline = time.monotonic() + 4
        while identifier not in manager._processes and time.monotonic() < deadline:
            time.sleep(.01)
        process = manager._processes[identifier]
        assert manager.cancel(identifier, "one")
        deadline = time.monotonic() + 4
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(.01)
        assert process.poll() is not None
        assert manager.get(identifier, "one").state == JobState.CANCELLED
    finally:
        manager.close()


def test_queue_bound_and_timeout_do_not_fake_success():
    manager = JobManager(io_workers=1, max_pending=1)
    gate = Event()
    try:
        identifier = manager.submit("one", "timeout", "a", gate.wait, 2, timeout=.02)
        with pytest.raises(ValueError, match="较多"):
            manager.submit("one", "timeout", "b", gate.wait, 2)
        time.sleep(.04)
        assert manager.get(identifier, "one").state == JobState.FAILED
        gate.set()
        assert manager.get(identifier, "one").result is None
    finally:
        gate.set()
        manager.close()


def test_windowless_python_worker_uses_owned_pipes():
    import os
    import pickle
    from pathlib import Path
    import subprocess
    import sys
    if os.name != "nt":
        pytest.skip("windowless Python is a Windows desktop entry")
    executable = Path(sys.executable).with_name("pythonw.exe")
    child = subprocess.run([str(executable), "-m", "quant_lab.cpu_worker"],
        input=pickle.dumps((sum, ([1, 2, 3],), {})), capture_output=True, timeout=15)
    assert child.returncode == 0
    assert pickle.loads(child.stdout) == (True, 6)
