from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import get_current_user
from app.config import settings
from app.database import get_job, list_job_branches, list_jobs_page
from app.schemas import (
    AuditJobListResponse,
    AuditJobResponse,
    AuditScanLogResponse,
    AuditStreamResponse,
    CreateAuditRequest,
    RerunAuditRequest,
    SendTelegramRequest,
)
from app.services.audit_runner import cancel_audit_job, start_audit_job
from app.services.bugs_archive import (
    get_bugs_bundle,
    get_execution_report,
    list_bugs_archive,
    list_execution_reports,
)
from app.services.document_export import export_document, list_documents, read_preview
from app.services.findings_parser import get_step_detail, parse_findings
from app.services.job_files import delete_audit_job
from app.services.pipeline_tracker import load_pipeline, read_stream
from app.services.scan_logs import build_all_scan_log, build_step_log, compute_progress
from app.services.telegram_client import send_audit_documents

router = APIRouter(prefix="/audits", tags=["audits"])


def _job_dir(job: dict) -> Path:
    return Path(settings.data_dir) / "jobs" / job["id"]


def _artifacts_path(job: dict) -> Path:
    p = job.get("artifacts_path")
    if p:
        return Path(p)
    return _job_dir(job) / "artifacts"


@router.get("", response_model=AuditJobListResponse)
def get_audits(
    page: int = 1,
    per_page: int = 20,
    branch: str | None = None,
    _: str = Depends(get_current_user),
):
    items, total = list_jobs_page(page=page, per_page=per_page, branch=branch or None)
    branches = list_job_branches()
    return {
        "items": items,
        "total": total,
        "page": max(1, page),
        "per_page": max(1, min(per_page, 100)),
        "branches": branches,
    }


@router.get("/bugs-archive")
def bugs_archive(
    page: int = 1,
    per_page: int = 30,
    _: str = Depends(get_current_user),
):
    items, total = list_bugs_archive(page=page, per_page=per_page)
    return {
        "items": items,
        "total": total,
        "page": max(1, page),
        "per_page": max(1, min(per_page, 100)),
    }


@router.get("/execution-reports")
def execution_reports(
    page: int = 1,
    per_page: int = 30,
    _: str = Depends(get_current_user),
):
    items, total = list_execution_reports(page=page, per_page=per_page)
    return {
        "items": items,
        "total": total,
        "page": max(1, page),
        "per_page": max(1, min(per_page, 100)),
    }


@router.get("/{job_id}/bugs-bundle")
def bugs_bundle(job_id: str, _: str = Depends(get_current_user)):
    data = get_bugs_bundle(job_id)
    if not data:
        raise HTTPException(404, "任务不存在")
    return data


@router.get("/{job_id}/execution-report")
def execution_report(job_id: str, _: str = Depends(get_current_user)):
    data = get_execution_report(job_id)
    if not data:
        raise HTTPException(404, "任务不存在")
    return data


@router.post("/{job_id}/cancel", response_model=AuditJobResponse)
def cancel_audit(job_id: str, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if job["status"] not in ("running", "queued"):
        raise HTTPException(400, "仅运行中或排队中的任务可取消")
    if not cancel_audit_job(job_id):
        raise HTTPException(400, "无法取消该任务")
    job = get_job(job_id)
    return job


@router.delete("/{job_id}")
def remove_audit(job_id: str, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if job["status"] in ("running", "queued"):
        raise HTTPException(400, "运行中的任务请先取消，再删除")
    if not delete_audit_job(job_id):
        raise HTTPException(404, "任务不存在")
    return {"ok": True, "id": job_id}


def _build_stream_from_pipeline(pipeline: dict) -> str:
    lines = []
    for step in pipeline.get("steps") or []:
        label = step.get("label") or step.get("id")
        status = step.get("status", "pending")
        msg = step.get("message") or ""
        lines.append(f">>> [{label}] {status.upper()} — {msg}")
        if step.get("stdout"):
            lines.append(step["stdout"].rstrip())
        if step.get("stderr"):
            lines.append(step["stderr"].rstrip())
    return "\n".join(lines) + ("\n" if lines else "")


@router.get("/{job_id}/logs/scan", response_model=AuditScanLogResponse)
def get_scan_logs(job_id: str, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    job_dir = _job_dir(job)
    pipeline = load_pipeline(job_id, settings.data_dir)
    running = job["status"] in ("running", "queued")
    content = build_all_scan_log(job_id, settings.data_dir, job_dir)
    progress = compute_progress(pipeline, job)
    return {
        "content": content,
        "running": running,
        "progress": progress,
    }


@router.get("/{job_id}/stream", response_model=AuditStreamResponse)
def get_stream(
    job_id: str,
    offset: int = 0,
    _: str = Depends(get_current_user),
):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    chunk, new_offset = read_stream(job_id, settings.data_dir, max(0, offset))
    pipeline = load_pipeline(job_id, settings.data_dir)
    if not chunk and offset == 0 and pipeline:
        full = _build_stream_from_pipeline(pipeline)
        chunk = full
        new_offset = len(full)
    current = pipeline.get("current_step") if pipeline else None
    running = job["status"] in ("running", "queued")
    return {
        "content": chunk,
        "offset": new_offset,
        "running": running,
        "current_step": current,
    }


@router.post("", response_model=AuditJobResponse)
async def create_audit(body: CreateAuditRequest, _: str = Depends(get_current_user)):
    job_id = start_audit_job(body.token, body.repo_full_name, body.branch)
    job = get_job(job_id)
    return job


@router.get("/{job_id}", response_model=AuditJobResponse)
def get_audit(job_id: str, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    return job


@router.post("/{job_id}/rerun", response_model=AuditJobResponse)
async def rerun_audit(job_id: str, body: RerunAuditRequest, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    branch = (body.branch or job["branch"] or "main").strip()
    new_id = start_audit_job(body.token, job["repo_full_name"], branch)
    new_job = get_job(new_id)
    return new_job


@router.get("/{job_id}/pipeline")
def get_pipeline(job_id: str, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    pipeline = load_pipeline(job_id, settings.data_dir)
    if not pipeline:
        return {"job_id": job_id, "steps": [], "current_step": None}
    return pipeline


@router.get("/{job_id}/pipeline/{step_id}")
def get_pipeline_step(job_id: str, step_id: str, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    detail = get_step_detail(_job_dir(job), step_id)
    if not detail:
        raise HTTPException(404, "步骤不存在")
    detail["log_content"] = build_step_log(
        _job_dir(job), step_id, job_id=job_id, data_dir=settings.data_dir,
    )
    return detail


@router.get("/{job_id}/findings")
def get_findings(job_id: str, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    art = _artifacts_path(job)
    if not art.exists():
        return parse_findings(art, _job_dir(job))
    return parse_findings(art, _job_dir(job))


@router.get("/{job_id}/documents")
def get_documents(job_id: str, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    return list_documents(_artifacts_path(job))


@router.get("/{job_id}/documents/{filename}/preview")
def preview_document(job_id: str, filename: str, _: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    try:
        content = read_preview(_artifacts_path(job), filename)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"filename": filename, "content": content}


@router.get("/{job_id}/documents/{filename}/download")
def download_document(
    job_id: str,
    filename: str,
    format: str = "md",
    _: str = Depends(get_current_user),
):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    try:
        data, out_name, media_type = export_document(
            _artifacts_path(job), filename, format
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )


@router.post("/{job_id}/telegram/send")
async def send_telegram(
    job_id: str,
    body: SendTelegramRequest,
    _: str = Depends(get_current_user),
):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if job["status"] != "completed":
        raise HTTPException(400, "任务尚未完成，无法发送")
    result = await send_audit_documents(
        _artifacts_path(job),
        job["repo_full_name"],
        job_id,
        body.filenames,
        body.send_summary,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "发送失败"))
    return result


@router.post("/{job_id}/telegram/send/{filename}")
async def send_single_document(
    job_id: str,
    filename: str,
    _: str = Depends(get_current_user),
):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if job["status"] != "completed":
        raise HTTPException(400, "任务尚未完成")
    result = await send_audit_documents(
        _artifacts_path(job),
        job["repo_full_name"],
        job_id,
        [filename],
        send_summary=False,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "发送失败"))
    return result
