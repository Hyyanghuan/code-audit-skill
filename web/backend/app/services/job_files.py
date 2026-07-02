"""审计任务关联文件清理。"""
from __future__ import annotations

import shutil
from pathlib import Path

from app.config import settings
from app.database import delete_job, get_job


def remove_job_files(job_id: str) -> None:
    job_dir = Path(settings.data_dir) / "jobs" / job_id
    clone_dir = Path(settings.data_dir) / "clones" / job_id
    tmp_dir = Path(settings.data_dir) / "tmp" / f"code-audit-{job_id}"
    scripts_dir = Path(settings.data_dir) / "tmp" / f"scripts-run-{job_id}"
    shutil.rmtree(job_dir, ignore_errors=True)
    shutil.rmtree(clone_dir, ignore_errors=True)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    shutil.rmtree(scripts_dir, ignore_errors=True)


def delete_audit_job(job_id: str) -> bool:
    job = get_job(job_id)
    if not job:
        return False
    remove_job_files(job_id)
    delete_job(job_id)
    return True
