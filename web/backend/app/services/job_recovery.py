"""启动时恢复因服务重启而中断的审计任务。"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.config import settings
from app.database import list_jobs, update_job
from app.services.job_control import clear_cancel, is_cancelled
from app.services.pipeline_tracker import load_pipeline, pipeline_path

INTERRUPT_MSG = "审计进程已中断（服务重启或异常退出），请重新执行审计"


def recover_stale_running_jobs() -> int:
    now = datetime.now(timezone.utc).isoformat()
    recovered = 0
    for job in list_jobs(limit=500):
        if job["status"] not in ("running", "queued"):
            continue
        job_id = job["id"]
        if is_cancelled(job_id):
            msg = "用户已取消审计（服务重启）"
            status = "cancelled"
        else:
            msg = INTERRUPT_MSG
            status = "failed"

        pipeline = load_pipeline(job_id, settings.data_dir)
        if pipeline:
            step_id = pipeline.get("current_step")
            for step in pipeline.get("steps") or []:
                if step.get("id") == step_id and step.get("status") == "running":
                    step["status"] = "error"
                    step["message"] = msg
                    step["finished_at"] = now
                    step["error_detail"] = msg
            pipeline["current_step"] = None
            pipeline["updated_at"] = now
            path = pipeline_path(job_id, settings.data_dir)
            path.write_text(json.dumps(pipeline, ensure_ascii=False, indent=2), encoding="utf-8")

        update_job(
            job_id,
            status=status,
            error_message=msg,
            finished_at=now,
        )
        clear_cancel(job_id)
        recovered += 1
        print(f"[startup] recovered stale job {job_id} -> {status}")
    return recovered
