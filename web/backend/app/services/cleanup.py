import shutil
from datetime import datetime, timedelta, timezone

from app.database import delete_job, list_jobs
from app.services.audit_settings import get_effective_retention_hours
from app.services.job_files import remove_job_files


def cleanup_expired_jobs() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=get_effective_retention_hours())
    removed = 0
    for job in list_jobs(limit=500):
        created = datetime.fromisoformat(job["created_at"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created >= cutoff:
            continue
        job_id = job["id"]
        remove_job_files(job_id)
        delete_job(job_id)
        removed += 1
    return removed
