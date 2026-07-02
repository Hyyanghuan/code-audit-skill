import json
from pathlib import Path

import httpx

from app.database import get_setting, set_setting
from app.settings_catalog import (
    TELEGRAM_REPORT_FILES,
    get_default_send_report_files,
    get_default_telegram_settings,
    migrate_send_report_files,
)


def get_telegram_settings() -> dict:
    defaults = get_default_telegram_settings()
    stored = get_setting("telegram", {}) or {}
    merged = {**defaults, **stored}
    merged["send_report_files"] = migrate_send_report_files(merged)
    return merged


def save_telegram_settings(data: dict) -> dict:
    defaults = get_default_telegram_settings()
    clean = {**defaults, **{k: data[k] for k in defaults if k in data}}
    if "send_report_files" in data and isinstance(data["send_report_files"], dict):
        base = get_default_send_report_files()
        clean["send_report_files"] = {**base, **{k: bool(v) for k, v in data["send_report_files"].items()}}
    set_setting("telegram", clean)
    return get_telegram_settings()


def get_selected_report_filenames(cfg: dict | None = None) -> list[str]:
    cfg = cfg or get_telegram_settings()
    files_cfg = migrate_send_report_files(cfg)
    return [name for name, enabled in files_cfg.items() if enabled]


def _truncate_log(path: Path, max_kb: int) -> Path:
    if max_kb <= 0 or not path.is_file():
        return path
    size_kb = path.stat().st_size / 1024
    if size_kb <= max_kb:
        return path
    text = path.read_text(encoding="utf-8", errors="replace")
    limit = max_kb * 1024
    truncated = text[:limit] + f"\n\n... (已截断，原大小 {size_kb:.0f} KB，上限 {max_kb} KB)"
    tmp = path.parent / f".tg-trunc-{path.name}"
    tmp.write_text(truncated, encoding="utf-8")
    return tmp


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

    do_summary = cfg.get("send_summary_message", True) if send_summary is None else send_summary
    max_log_kb = int(cfg.get("max_log_size_kb") or 5000)

    results = []
    if do_summary:
        summary_path = artifacts_dir / "audit-summary.json"
        audit_status = "unknown"
        total = 0
        tc_stats = ""
        if summary_path.exists():
            s = json.loads(summary_path.read_text(encoding="utf-8"))
            audit_status = s.get("audit_status", "unknown")
            total = s.get("total_findings", 0)
            tc = s.get("test_cases") or {}
            if tc:
                tc_stats = f"\n测试用例: {tc.get('passed', 0)}/{tc.get('total', 0)} 通过"
        msg = (
            f"[Code Audit Web]\n"
            f"仓库: {repo_full_name}\n"
            f"Job: {job_id}\n"
            f"状态: {audit_status}\n"
            f"问题数: {total}{tc_stats}"
        )
        results.append({"file": "__summary__", **await send_message(token, chat_id, msg)})

    if filenames is None:
        selected = get_selected_report_filenames(cfg)
        filenames = [n for n in selected if (artifacts_dir / n).exists()]
    else:
        filenames = list(filenames)

    for name in filenames:
        path = artifacts_dir / name
        if not path.exists():
            results.append({"file": name, "ok": False, "error": "文件不存在"})
            continue
        send_path = path
        if name.endswith(".txt") or name.endswith(".log"):
            send_path = _truncate_log(path, max_log_kb)
        caption = f"{repo_full_name} | {name} | Job {job_id}"
        results.append({"file": name, **await send_file(token, chat_id, send_path, caption)})

    ok_count = sum(1 for r in results if r.get("ok"))
    return {"ok": ok_count > 0, "sent": ok_count, "total": len(results), "results": results}


def list_telegram_report_file_options() -> list[dict]:
    return TELEGRAM_REPORT_FILES
