"""聚合全部扫描步骤的完整执行日志与进度。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.findings_parser import get_step_detail
from app.services.pipeline_tracker import load_pipeline, read_stream, step_log_path

DONE_STATUSES = frozenset({"success", "failure", "error", "skipped"})
MAX_SECTION_CHARS = 1_000_000

STATUS_LABEL = {
    "pending": "等待",
    "running": "执行中",
    "success": "成功",
    "failure": "发现问题",
    "error": "错误",
    "skipped": "已跳过",
}


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _format_step_block(detail: dict) -> str:
    label = detail.get("label") or detail.get("id", "")
    status = STATUS_LABEL.get(detail.get("status", ""), detail.get("status", ""))
    lines = [f">>> [{label}] {status}"]
    if detail.get("message"):
        lines[0] += f" — {detail['message']}"
    if detail.get("started_at"):
        lines.append(f"# 开始 {detail['started_at']}")
    if detail.get("finished_at"):
        lines.append(f"# 结束 {detail['finished_at']}")
    if detail.get("findings"):
        lines.append(f"# 发现 {detail['findings']} 项")
    body = detail.get("full_log")
    if not body:
        parts = [detail.get("stdout") or "", detail.get("stderr") or ""]
        if detail.get("error_detail"):
            parts.append(detail["error_detail"])
        body = "\n".join(p for p in parts if p).strip()
    if body:
        lines.append(body)
    lines.append(f"<<< [{label}] 结束\n")
    return "\n".join(lines)


def build_steps_scan_log(
    job_dir: Path,
    pipeline: dict,
    *,
    job_id: str | None = None,
    data_dir: str | None = None,
) -> str:
    parts: list[str] = []
    for step in pipeline.get("steps") or []:
        if step.get("status") == "pending":
            continue
        if job_id and data_dir:
            parts.append(build_step_log(job_dir, step["id"], job_id=job_id, data_dir=data_dir))
            continue
        detail = get_step_detail(job_dir, step["id"])
        if detail:
            parts.append(_format_step_block(detail))
    return "\n\n".join(parts)


def compute_progress(pipeline: dict | None, job: dict | None) -> dict:
    steps = (pipeline or {}).get("steps") or []
    total = len(steps)
    if not total:
        return {
            "percent": 0,
            "eta_seconds": None,
            "completed": 0,
            "total": 0,
            "current_step": None,
            "current_label": "",
        }

    completed = 0
    total_duration_ms = 0
    duration_count = 0
    running_step = None
    now = datetime.now(timezone.utc)

    for step in steps:
        st = step.get("status", "pending")
        if st == "running":
            running_step = step
        if st in DONE_STATUSES:
            completed += 1
            start = _parse_ts(step.get("started_at"))
            end = _parse_ts(step.get("finished_at"))
            if start and end:
                ms = (end - start).total_seconds() * 1000
                if ms > 0:
                    total_duration_ms += ms
                    duration_count += 1

    percent = int(completed / total * 100)
    if running_step:
        percent = min(99, int((completed + 0.5) / total * 100))
    if completed >= total:
        percent = 100

    eta_seconds: int | None = None
    remaining = total - completed - (1 if running_step else 0)
    if duration_count > 0 and (remaining > 0 or running_step):
        avg_ms = total_duration_ms / duration_count
        eta_ms = avg_ms * max(0, remaining)
        if running_step:
            start = _parse_ts(running_step.get("started_at"))
            if start:
                running_ms = (now - start).total_seconds() * 1000
                eta_ms += max(0, avg_ms - running_ms)
        eta_seconds = max(0, int(eta_ms / 1000))
    elif job and completed < total:
        created = _parse_ts(job.get("created_at"))
        if created:
            elapsed = (now - created).total_seconds()
            frac = max(completed / total, 0.05)
            eta_seconds = max(0, int(elapsed / frac - elapsed))

    current_id = (pipeline or {}).get("current_step")
    current_label = ""
    if current_id:
        for s in steps:
            if s.get("id") == current_id:
                current_label = s.get("label") or current_id
                break
    elif running_step:
        current_id = running_step.get("id")
        current_label = running_step.get("label") or current_id

    return {
        "percent": percent,
        "eta_seconds": eta_seconds,
        "completed": completed,
        "total": total,
        "current_step": current_id,
        "current_label": current_label,
    }


def _read_file_section(title: str, path: Path) -> str:
    if not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace")
    if len(content) > MAX_SECTION_CHARS:
        content = content[:MAX_SECTION_CHARS] + f"\n\n... (已截断，共 {len(content)} 字符)"
    return f"{'=' * 42}\n[{title}]\n{path}\n{'=' * 42}\n{content.rstrip()}"


def _extract_stream_section(stream: str, label: str) -> str:
    if not stream.strip() or not label:
        return ""
    lines = stream.splitlines()
    buf: list[str] = []
    collecting = False
    for line in lines:
        if line.startswith(">>> [") and label in line:
            collecting = True
            buf = [line]
            continue
        if not collecting:
            continue
        buf.append(line)
        if line.startswith("<<< [") and label in line:
            break
    return "\n".join(buf)


def _step_header(detail: dict) -> str:
    label = detail.get("label") or detail.get("id", "")
    status = STATUS_LABEL.get(detail.get("status", ""), detail.get("status", ""))
    lines = [f">>> [{label}] {status}"]
    if detail.get("message"):
        lines[0] += f" — {detail['message']}"
    if detail.get("started_at"):
        lines.append(f"# 开始 {detail['started_at']}")
    if detail.get("finished_at"):
        lines.append(f"# 结束 {detail['finished_at']}")
    if detail.get("findings"):
        lines.append(f"# 发现 {detail['findings']} 项")
    return "\n".join(lines)


def _module_result_paths(data_dir: str, job_id: str, step_id: str) -> list[Path]:
    base = Path(data_dir) / "tmp" / f"code-audit-{job_id}" / "results"
    names = [step_id, step_id.replace("_", "-")]
    return [base / f"{name}.json" for name in names]


def build_step_log(
    job_dir: Path,
    step_id: str,
    *,
    job_id: str | None = None,
    data_dir: str | None = None,
) -> str:
    detail = get_step_detail(job_dir, step_id)
    if not detail:
        return "步骤不存在"
    label = detail.get("label") or step_id
    if detail.get("status") == "pending":
        return f">>> [{label}] 等待\n尚未执行，请等待流水线到达此步骤。"

    sections: list[str] = [_step_header(detail)]

    if job_id and data_dir:
        step_log = step_log_path(job_id, data_dir, step_id)
        if step_log.is_file():
            section = _read_file_section("步骤执行输出（完整 stdout/stderr）", step_log)
            if section:
                sections.append(section)
        if detail.get("status") == "running" or not step_log.is_file():
            stream, _ = read_stream(job_id, data_dir, 0)
            stream_part = _extract_stream_section(stream, label)
            if stream_part:
                sections.append(f"{'=' * 42}\n[实时流输出]\n{'=' * 42}\n{stream_part}")

    log_file = detail.get("log_file")
    if log_file:
        section = _read_file_section("模块日志文件", Path(log_file))
        if section:
            sections.append(section)

    artifacts = job_dir / "artifacts"
    for name in [f"{step_id}.log", f"{step_id.replace('_', '-')}.log"]:
        section = _read_file_section("Artifacts 日志", artifacts / name)
        if section:
            sections.append(section)
            break

    if job_id and data_dir:
        for result_path in _module_result_paths(data_dir, job_id, step_id):
            section = _read_file_section("模块结果 JSON", result_path)
            if section:
                sections.append(section)
                break

    if detail.get("report"):
        report_text = json.dumps(detail["report"], indent=2, ensure_ascii=False)
        if len(report_text) > MAX_SECTION_CHARS:
            report_text = report_text[:MAX_SECTION_CHARS] + "\n... (已截断)"
        sections.append(f"{'=' * 42}\n[报告 JSON]\n{'=' * 42}\n{report_text}")

    if detail.get("module_result"):
        module_text = json.dumps(detail["module_result"], indent=2, ensure_ascii=False)
        if len(module_text) > MAX_SECTION_CHARS:
            module_text = module_text[:MAX_SECTION_CHARS] + "\n... (已截断)"
        sections.append(f"{'=' * 42}\n[模块汇总]\n{'=' * 42}\n{module_text}")

    if not any("步骤执行输出" in s or "实时流" in s or "Artifacts" in s or "模块日志" in s for s in sections[1:]):
        body = detail.get("full_log")
        if not body:
            parts = [detail.get("stdout") or "", detail.get("stderr") or ""]
            if detail.get("error_detail"):
                parts.append(detail["error_detail"])
            body = "\n".join(p for p in parts if p).strip()
        if body:
            sections.append(body)

    sections.append(f"<<< [{label}] 结束")
    return "\n\n".join(sections)


def build_full_audit_flow_log(job_id: str, data_dir: str, job_dir: Path) -> str:
    """合并实时流 + 各步骤完整日志，供右侧审计流程面板展示。"""
    pipeline = load_pipeline(job_id, data_dir)
    stream, _ = read_stream(job_id, data_dir, 0)
    sections: list[str] = []

    if stream.strip():
        sections.append(
            f"{'=' * 42}\n[实时流输出]\n{'=' * 42}\n{stream.rstrip()}"
        )

    if pipeline:
        steps_log = build_steps_scan_log(job_dir, pipeline, job_id=job_id, data_dir=data_dir)
        if steps_log.strip():
            sections.append(
                f"{'=' * 42}\n[步骤完整日志]\n{'=' * 42}\n{steps_log.rstrip()}"
            )

    if sections:
        return "\n\n".join(sections)

    if stream.strip():
        return stream
    return "暂无审计流程日志，等待审计启动…"


def build_all_scan_log(job_id: str, data_dir: str, job_dir: Path) -> str:
    return build_full_audit_flow_log(job_id, data_dir, job_dir)
