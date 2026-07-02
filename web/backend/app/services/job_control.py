"""审计任务取消与进程控制。"""
from __future__ import annotations

import os
import signal
import subprocess
import threading
from pathlib import Path

from app.config import settings

_lock = threading.Lock()
_cancel_requested: set[str] = set()
_active_procs: dict[str, subprocess.Popen] = {}

CANCEL_DIR = Path(settings.data_dir) / "cancel_flags"


class AuditCancelled(Exception):
    """用户主动取消审计。"""


def _flag_path(job_id: str) -> Path:
    CANCEL_DIR.mkdir(parents=True, exist_ok=True)
    return CANCEL_DIR / f"{job_id}.flag"


def request_cancel(job_id: str) -> None:
    with _lock:
        _cancel_requested.add(job_id)
    _flag_path(job_id).write_text("1", encoding="utf-8")


def clear_cancel(job_id: str) -> None:
    with _lock:
        _cancel_requested.discard(job_id)
    flag = _flag_path(job_id)
    if flag.exists():
        flag.unlink(missing_ok=True)


def is_cancelled(job_id: str) -> bool:
    with _lock:
        if job_id in _cancel_requested:
            return True
    return _flag_path(job_id).exists()


def register_process(job_id: str, proc: subprocess.Popen) -> None:
    with _lock:
        _active_procs[job_id] = proc


def unregister_process(job_id: str) -> None:
    with _lock:
        _active_procs.pop(job_id, None)


def kill_job_process(job_id: str) -> None:
    with _lock:
        proc = _active_procs.get(job_id)
    if not proc or proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, OSError):
        try:
            proc.terminate()
        except OSError:
            pass


def ensure_not_cancelled(job_id: str) -> None:
    if is_cancelled(job_id):
        raise AuditCancelled("用户已取消审计")
