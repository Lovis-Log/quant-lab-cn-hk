"""Bounded, session-scoped background jobs. This module never imports the UI.

I/O cancellation discards a late response; it cannot revoke an HTTP request
already sent. CPU jobs have an owned, cancellable spawned process. Workers
receive copies of inputs and never write Streamlit session state.
"""

from __future__ import annotations

import atexit
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, replace
from enum import Enum
import os
import pickle
import subprocess
import sys
from threading import Event, RLock
import time
from typing import Any, Callable
from uuid import uuid4
from quant_lab.security import redact


def _error_message(error):
    if isinstance(error, ValueError) or type(error).__module__.startswith("quant_lab."):
        return redact(str(error))[:350]
    return "任务失败；保留上次有效结果，请稍后重试。"


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL = {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}


@dataclass(frozen=True)
class JobSnapshot:
    id: str
    scope: str
    kind: str
    fingerprint: str
    state: JobState
    submitted_at: float
    started_at: float | None = None
    finished_at: float | None = None
    result: Any = None
    error: str | None = None


class JobManager:
    def __init__(self, io_workers=3, max_pending=16, retained=64):
        self._io = ThreadPoolExecutor(max_workers=io_workers, thread_name_prefix="quant-io")
        self._cpu = ThreadPoolExecutor(max_workers=1, thread_name_prefix="quant-cpu-supervisor")
        self._lock = RLock()
        self._jobs: dict[str, JobSnapshot] = {}
        self._cancel: dict[str, Event] = {}
        self._deadlines: dict[str, float] = {}
        self._futures = {}
        self._processes = {}
        self._max_pending, self._retained = max_pending, retained
        self._closed = False

    def submit(self, scope: str, kind: str, fingerprint: str, function: Callable,
               *args, cpu=False, timeout=180, **kwargs) -> str:
        if not scope or not kind or not fingerprint or timeout <= 0:
            raise ValueError("任务需要作用域、类型、输入指纹与有效超时。")
        with self._lock:
            if self._closed:
                raise RuntimeError("任务服务已关闭。")
            for job in self._jobs.values():
                if (job.scope, job.kind, job.fingerprint) == (scope, kind, fingerprint) and job.state not in TERMINAL:
                    return job.id
            if sum(j.state not in TERMINAL for j in self._jobs.values()) >= self._max_pending:
                raise ValueError("等待中的任务较多，请取消旧任务或稍后重试。")
            while len(self._jobs) >= self._retained:
                old = next((key for key, job in self._jobs.items() if job.state in TERMINAL), None)
                if old is None:
                    break
                for mapping in (self._jobs, self._cancel, self._deadlines, self._futures):
                    mapping.pop(old, None)
            frozen_args, frozen_kwargs = deepcopy(args), deepcopy(kwargs)
            identifier = uuid4().hex
            self._jobs[identifier] = JobSnapshot(identifier, scope, kind, fingerprint, JobState.QUEUED, time.monotonic())
            self._cancel[identifier] = Event()
            self._deadlines[identifier] = time.monotonic() + timeout
            # Snapshot the request before another render can change its inputs.
            executor = self._cpu if cpu else self._io
            self._futures[identifier] = executor.submit(self._run, identifier, function, frozen_args, frozen_kwargs, cpu)
            return identifier

    def _finish(self, identifier, state, result=None, error=None):
        with self._lock:
            job = self._jobs.get(identifier)
            if job and job.state not in TERMINAL:
                self._jobs[identifier] = replace(job, state=state, result=result, error=error, finished_at=time.monotonic())

    def _run(self, identifier, function, args, kwargs, cpu):
        with self._lock:
            job = self._jobs[identifier]
            if job.state in TERMINAL:
                return
            self._jobs[identifier] = replace(job, state=JobState.RUNNING, started_at=time.monotonic())
        try:
            if cpu:
                result = self._run_cpu(identifier, function, args, kwargs)
            else:
                result = function(*args, **kwargs)
            # Poll once before publishing so an expired request never succeeds.
            self.get(identifier, job.scope)
            self._finish(identifier, JobState.SUCCEEDED, result=result)
        except Exception as error:
            message = _error_message(error)
            self._finish(identifier, JobState.FAILED, error=message)

    def _run_cpu(self, identifier, function, args, kwargs):
        # A dedicated entry avoids multiprocessing replaying Streamlit's
        # temporary __main__ module (including AppTest's UI script).
        command = ([sys.executable, "--compute-worker"] if getattr(sys, "frozen", False)
                   else [sys.executable, "-m", "quant_lab.cpu_worker"])
        environment = {**os.environ, "PYTHONPATH": os.pathsep.join(str(p) for p in sys.path)}
        environment.update({name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
        process = None
        try:
            with self._lock:
                if self._cancel[identifier].is_set():
                    return None
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, env=environment,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                self._processes[identifier] = process
            payload = pickle.dumps((function, args, kwargs), protocol=pickle.HIGHEST_PROTOCOL)
            first = True
            while True:
                if self._cancel[identifier].is_set() or time.monotonic() >= self._deadlines[identifier]:
                    self._finish(identifier, JobState.FAILED, error="计算超时，请缩小研究范围后重试。")
                    return None
                try:
                    output, _ = process.communicate(input=payload if first else None, timeout=.05)
                    break
                except subprocess.TimeoutExpired:
                    first = False
            if process.returncode:
                raise RuntimeError("worker exited")
            ok, value = pickle.loads(output)
            if not ok:
                self._finish(identifier, JobState.FAILED, error=value)
                return None
            return value
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                process.communicate(timeout=3)
            with self._lock:
                self._processes.pop(identifier, None)

    def get(self, identifier: str, scope: str) -> JobSnapshot | None:
        with self._lock:
            job = self._jobs.get(identifier)
            if job is None or job.scope != scope:
                return None
            if job.state not in TERMINAL and time.monotonic() >= self._deadlines[identifier]:
                self._cancel[identifier].set()
                self._finish(identifier, JobState.FAILED, error="任务超时；上次有效结果仍保留。")
            return self._jobs[identifier]

    def cancel(self, identifier: str, scope: str) -> bool:
        with self._lock:
            job = self.get(identifier, scope)
            if job is None or job.state in TERMINAL:
                return False
            self._cancel[identifier].set()
            self._finish(identifier, JobState.CANCELLED)
            self._futures[identifier].cancel()
            process = self._processes.get(identifier)
            if process is not None and process.poll() is None:
                process.terminate()
            return True

    def pending(self, scope: str) -> tuple[JobSnapshot, ...]:
        with self._lock:
            return tuple(self.get(key, scope) for key, job in self._jobs.items()
                         if job.scope == scope and job.state not in TERMINAL)

    def close(self):
        with self._lock:
            self._closed = True
            for job in tuple(self._jobs.values()):
                self.cancel(job.id, job.scope)
            for process in self._processes.values():
                if process.poll() is None:
                    process.terminate()
        self._io.shutdown(wait=False, cancel_futures=True)
        self._cpu.shutdown(wait=True, cancel_futures=True)


_manager = None
_manager_lock = RLock()


def job_manager() -> JobManager:
    global _manager
    with _manager_lock:
        if _manager is None or _manager._closed:
            _manager = JobManager()
        return _manager


def shutdown_jobs():
    with _manager_lock:
        if _manager is not None:
            _manager.close()


atexit.register(shutdown_jobs)
