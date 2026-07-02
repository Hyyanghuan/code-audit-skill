import json
from pathlib import Path

import httpx

from app.database import get_setting, set_setting
from app.settings_catalog import get_default_telegram_settings


def get_telegram_settings() -> dict:
    defaults = get_default_telegram_settings()
    stored = get_setting("telegram", {}) or {}
    return {**defaults, **stored}


def save_telegram_settings(data: dict) -> dict:
    defaults = get_default_telegram_settings()
    clean = {**defaults, **{k: data[k] for k in defaults if k in data}}
    set_setting("telegram", clean)
    return clean


def _tg_send_flags() -> dict:
    cfg = get_telegram_settings()
    return {
        "send_summary": cfg.get("send_summary_message", True),
        "send_md": cfg.get("send_test_cases_md", True),
        "send_bug": cfg.get("send_bug_report_md", True),
        "send_logs": cfg.get("send_audit_logs", True),
    }


async def send_file(token: str, chat_id: str, file_path: Path, caption: str = "") -> dict:
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    async with httpx.AsyncClient(timeout=120.0) as client:
        with file_path.open("rb") as fh:
            resp = await client.post(
                url,
                data={"chat_id": chat_id, "caption": caption[:1024]},
                files={"document": (file_path.name, fh)},
            )
    try:
        body = resp.json()
    except json.JSONDecodeError:
        body = {"ok": False, "description": resp.text[:500]}
    return {"ok": resp.status_code == 200 and body.get("ok"), "status_code": resp.status_code, "body": body}


async def send_message(token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        )
    try:
        body = resp.json()
    except json.JSONDecodeError:
        body = {"ok": False, "description": resp.text[:500]}
    return {"ok": resp.status_code == 200 and body.get("ok"), "status_code": resp.status_code, "body": body}


async def send_audit_documents(
    artifacts_dir: Path,
    repo_full_name: str,
    job_id: str,
    filenames: list[str] | None = None,
    send_summary: bool | None = None,
) -> dict:
    cfg = get_telegram_settings()
    if not cfg.get("enabled", True):
        return {"ok": False, "error": "Telegram 集成已关闭，请在系统配置中启用"}

    token = cfg.get("bot_token", "")
    chat_id = cfg.get("chat_id", "")
    if not token or not chat_id:
        return {"ok": False, "error": "Telegram 未配置 bot_token 或 chat_id"}

    flags = _tg_send_flags()
    do_summary = flags["send_summary"] if send_summary is None else send_summary

    results = []
    if do_summary:
        summary_path = artifacts_dir / "audit-summary.json"
        audit_status = "unknown"
        total = 0
        if summary_path.exists():
            s = json.loads(summary_path.read_text(encoding="utf-8"))
            audit_status = s.get("audit_status", "unknown")
            total = s.get("total_findings", 0)
        msg = (
            f"[Code Audit Web]\n"
            f"仓库: {repo_full_name}\n"
            f"Job: {job_id}\n"
            f"状态: {audit_status}\n"
            f"问题数: {total}"
        )
        results.append({"file": "__summary__", **await send_message(token, chat_id, msg)})

    if filenames is None:
        candidates = []
        if flags["send_md"]:
            candidates.extend(["test-cases.md", "manual-audit-checklist.md"])
        if flags["send_bug"]:
            candidates.append("audit-bugs.md")
        if flags["send_logs"]:
            candidates.append("audit-logs-combined.txt")
        candidates.append("audit-summary.json")
        filenames = [n for n in candidates if (artifacts_dir / n).exists()]
        if not filenames:
            filenames = [
                f.name
                for f in artifacts_dir.iterdir()
                if f.is_file() and f.suffix.lower() in {".md", ".json", ".txt"}
            ]

    for name in filenames:
        path = artifacts_dir / name
        if not path.exists():
            results.append({"file": name, "ok": False, "error": "文件不存在"})
            continue
        if name == "audit-bugs.md" and not flags["send_bug"]:
            continue
        if name in ("test-cases.md", "manual-audit-checklist.md") and not flags["send_md"]:
            continue
        if name == "audit-logs-combined.txt" and not flags["send_logs"]:
            continue
        caption = f"{repo_full_name} | {name} | Job {job_id}"
        results.append({"file": name, **await send_file(token, chat_id, path, caption)})

    ok_count = sum(1 for r in results if r.get("ok"))
    return {"ok": ok_count > 0, "sent": ok_count, "total": len(results), "results": results}
