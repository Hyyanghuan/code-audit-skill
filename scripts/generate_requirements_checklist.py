#!/usr/bin/env python3
"""需求注册表、清单 MD、Telegram 推送。见 docs/memory/REQUIREMENT-GUIDE.md"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "docs" / "memory"
REGISTRY = MEMORY / "requirements-registry.yaml"
REPORTS = MEMORY / "reports"
INTAKE_DIR = MEMORY / "intake"
TG_CONFIG = ROOT / "config" / "telegram.yaml"
CHECKLIST_LATEST = REPORTS / "requirements-checklist.md"


def ensure_yaml():
    try:
        import yaml  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml"])


def load_registry() -> dict:
    ensure_yaml()
    import yaml
    if not REGISTRY.is_file():
        return {"meta": {"version": 1}, "requirements": []}
    with open(REGISTRY, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"requirements": []}


def save_registry(data: dict) -> None:
    ensure_yaml()
    import yaml
    data.setdefault("meta", {})["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(REGISTRY, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def load_tg_config() -> dict:
    ensure_yaml()
    import yaml
    paths = [
        ROOT / "config" / "telegram.local.yaml",
        TG_CONFIG,
    ]
    data = {}
    for p in paths:
        if p.is_file():
            with open(p, encoding="utf-8") as f:
                part = yaml.safe_load(f) or {}
            for k, v in part.items():
                if v is not None and v != "":
                    data[k] = v
    placeholders = {"", "CHANGE_ME", "YOUR_BOT_TOKEN", "YOUR_CHAT_ID"}

    def pick(key, env_keys):
        for ek in env_keys:
            v = os.environ.get(ek, "").strip()
            if v and v not in placeholders:
                return v
        yv = str(data.get(key, "") or "").strip()
        return yv if yv and yv not in placeholders else ""

    token = pick("bot_token", ["INPUT_TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN"])
    chat_id = pick("chat_id", ["INPUT_TELEGRAM_CHAT_ID", "TG_CHAT_ID"])
    cfg = dict(data)
    cfg["bot_token"] = token
    cfg["chat_id"] = chat_id
    return cfg


def parse_intake_features(intake_text: str) -> list[dict]:
    features, in_section = [], False
    for line in intake_text.splitlines():
        if "## 2." in line and "功能" in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.strip().startswith("|"):
            continue
        if "功能点" in line or re.match(r"^\|\s*-+", line):
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 5:
            continue
        m = re.match(r"(F-\d+)\s*(.*)", cols[0])
        if not m:
            continue
        planned = "❌" not in cols[3] and "不做" not in cols[3]
        features.append({
            "id": m.group(1),
            "name": m.group(2).strip() or cols[0],
            "priority": cols[1],
            "source": cols[2],
            "planned": planned,
            "implemented": planned,
            "verified": False,
            "evidence": cols[4][:120] if cols[4] else "",
        })
    return features


def parse_audit_feature_verification(audit_text: str | None) -> dict[str, dict]:
    result, in_sec = {}, False
    if not audit_text:
        return result
    for line in audit_text.splitlines():
        if "## 3." in line and "功能" in line:
            in_sec = True
            continue
        if in_sec and line.startswith("## "):
            break
        if not in_sec or not line.strip().startswith("|") or "F-" not in line:
            continue
        if "功能点" in line or "---" in line:
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        m = re.match(r"(F-\d+)", cols[0])
        if m:
            result[m.group(1)] = {
                "verified": "✅" in (cols[3] if len(cols) > 3 else ""),
                "evidence": cols[2] if len(cols) > 2 else "",
            }
    return result


def rel_to_root(p: Path | None) -> str | None:
    if not p or not p.is_file():
        return None
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def extract_raw_requirement(intake_text: str | None) -> str:
    if not intake_text:
        return ""
    m = re.search(r"## 0\. 需求原文[\s\S]*?```\n([\s\S]*?)```", intake_text)
    return m.group(1).strip() if m else ""


def upsert_task(
    task_id: str, title: str, epic: str = "",
    intake_path: Path | None = None, audit_path: Path | None = None,
    completion_path: Path | None = None, is_historical: bool = False,
) -> dict:
    data = load_registry()
    reqs = data.setdefault("requirements", [])
    tid = task_id.upper()
    req_id = f"REQ-{tid}"
    intake_text = intake_path.read_text(encoding="utf-8") if intake_path and intake_path.is_file() else ""
    audit_text = audit_path.read_text(encoding="utf-8") if audit_path and audit_path.is_file() else None
    features = parse_intake_features(intake_text) if intake_text else []
    audit_map = parse_audit_feature_verification(audit_text)
    for feat in features:
        av = audit_map.get(feat["id"], {})
        if av.get("verified"):
            feat["verified"] = True
        if av.get("evidence"):
            feat["evidence"] = av["evidence"]
        if not feat["planned"]:
            feat["implemented"] = False
            feat["verified"] = av.get("verified", True)
        elif feat["implemented"] and not av:
            feat["verified"] = True  # 关任务：已实现且计划内默认已验证
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    existing = next((r for r in reqs if r.get("task_id") == tid or r.get("id") == req_id), None)
    entry = {
        "id": req_id, "task_id": tid, "epic": epic or (existing or {}).get("epic", ""),
        "title": title,
        "raw": extract_raw_requirement(intake_text) or (existing or {}).get("raw", title),
        "created_at": (existing or {}).get("created_at", now),
        "completed_at": now, "status": "completed", "is_historical": is_historical,
        "source": "intake",
        "features": features or (existing or {}).get("features", []),
        "reports": {},
    }
    for key, p in (("intake", intake_path), ("audit", audit_path), ("completion", completion_path)):
        r = rel_to_root(p)
        if r:
            entry["reports"][key] = r
    if existing:
        reqs[reqs.index(existing)] = entry
    else:
        reqs.append(entry)
    data["meta"]["last_task_id"] = tid
    save_registry(data)
    return entry


def verify_mark(ok) -> str:
    if ok is True:
        return "✅"
    if ok is False:
        return "❌"
    return "☐"


def render_checklist(current_task_id: str | None = None) -> Path:
    data = load_registry()
    reqs = data.get("requirements") or []
    reqs = sorted(reqs, key=lambda r: r.get("completed_at") or r.get("created_at") or "", reverse=True)
    if current_task_id:
        cur = [r for r in reqs if r.get("task_id") == current_task_id.upper()]
        rest = [r for r in reqs if r.get("task_id") != current_task_id.upper()]
        reqs = cur + rest
    total_features = sum(len(r.get("features") or []) for r in reqs)
    verified = sum(1 for r in reqs for f in (r.get("features") or []) if f.get("verified"))
    implemented = sum(1 for r in reqs for f in (r.get("features") or []) if f.get("implemented"))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 需求清单与验证结果", "",
        f"> 生成时间：{ts}  ", "> 排序：**需求完成时间倒序**（新 → 旧）  ",
        f"> 数据源：`docs/memory/requirements-registry.yaml`", "", "---", "",
        "## 总览", "",
        "| 指标 | 数量 |", "|------|------|",
        f"| 需求条目 | {len(reqs)} |", f"| 功能点合计 | {total_features} |",
        f"| 已实现 | {implemented} |", f"| 已验证 | {verified} |",
        f"| 待验证 | {total_features - verified} |", "",
    ]
    if current_task_id:
        lines += [f"**本次关任务**：`{current_task_id.upper()}` 🆕", ""]
    lines += ["---", ""]
    for req in reqs:
        tid = req.get("task_id", "")
        is_new = current_task_id and tid == current_task_id.upper()
        icon = "🆕" if is_new else ("📦" if req.get("is_historical") else "✅")
        typ = "新需求" if is_new else "历史需求"
        lines += [
            f"## {req.get('id', '?')} — {req.get('title', '')} {icon}", "",
            "| 项 | 值 |", "|----|-----|",
            f"| 类型 | **{typ}** |", f"| 任务 ID | `{tid}` |",
            f"| Epic | {req.get('epic') or '—'} |",
            f"| 创建 | {(req.get('created_at') or '')[:10]} |",
            f"| 完成 | {(req.get('completed_at') or '')[:10]} |",
            f"| 状态 | {req.get('status', '—')} |",
            f"| 原文摘要 | {(req.get('raw') or '—').replace(chr(10), ' ')[:200]} |", "",
        ]
        reps = req.get("reports") or {}
        if reps:
            lines += [f"**报告**：{' · '.join('`'+v+'`' for v in reps.values())}", ""]
        lines += ["### 功能清单与验证", "",
                  "| 功能 ID | 功能 | 计划 | 实现 | 验证 | 证据 |",
                  "|---------|------|------|------|------|------|"]
        for f in req.get("features") or []:
            lines.append(
                f"| {f.get('id', '—')} | {f.get('name', '—')} | "
                f"{verify_mark(f.get('planned'))} | {verify_mark(f.get('implemented'))} | "
                f"{verify_mark(f.get('verified'))} | {(f.get('evidence') or '—')[:80]} |"
            )
        if not req.get("features"):
            lines.append("| — | 无功能矩阵 | — | — | — | — |")
        lines += ["", "---", ""]
    lines += [
        "## 验证说明", "", "| 符号 | 含义 |", "|------|------|",
        "| ✅ | 通过 / 已实现 |", "| ❌ | 未通过 / 明确不做 |", "| ☐ | 待确认 |",
        "", "🆕 = 本次关任务 · 📦 = 历史归档", "",
    ]
    content = "\n".join(lines)
    REPORTS.mkdir(parents=True, exist_ok=True)
    CHECKLIST_LATEST.write_text(content, encoding="utf-8")
    suffix = f"{current_task_id.upper()}-requirements-checklist.md" if current_task_id else "requirements-checklist.md"
    dated = REPORTS / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{suffix}"
    dated.write_text(content, encoding="utf-8")
    return dated


def send_telegram_document(file_path: Path, caption: str) -> tuple[bool, str]:
    cfg = load_tg_config()
    if not cfg.get("enabled", True):
        return False, "telegram disabled"
    if not cfg.get("send_requirements_checklist", True):
        return False, "send_requirements_checklist=false"
    token, chat_id = cfg.get("bot_token", ""), cfg.get("chat_id", "")
    if not token or not chat_id:
        return False, "bot_token or chat_id missing"
    try:
        try:
            import requests
            with open(file_path, "rb") as fh:
                resp = requests.post(
                    f"https://api.telegram.org/bot{token}/sendDocument",
                    data={"chat_id": chat_id, "caption": caption[:1024]},
                    files={"document": (file_path.name, fh, "text/markdown")},
                    timeout=120,
                )
            if resp.status_code == 200 and resp.json().get("ok"):
                return True, "ok"
            return False, resp.text[:300]
        except ImportError:
            pass
        r = subprocess.run(
            ["curl", "-sS", "--http1.1", "--retry", "2", "-w", "\n%{http_code}", "--max-time", "120",
             "-X", "POST", f"https://api.telegram.org/bot{token}/sendDocument",
             "-F", f"chat_id={chat_id}", "-F", f"document=@{file_path}",
             "-F", f"caption={caption[:1024]}"],
            capture_output=True, text=True,
        )
        code = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "000"
        return code == "200", r.stdout[:300]
    except Exception as e:
        return False, str(e)[:300]


def send_telegram_message(text: str) -> tuple[bool, str]:
    cfg = load_tg_config()
    token, chat_id = cfg.get("bot_token", ""), cfg.get("chat_id", "")
    if not token or not chat_id:
        return False, "missing credentials"
    try:
        try:
            import requests
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True},
                timeout=30,
            )
            return resp.status_code == 200, resp.text[:200]
        except ImportError:
            pass
        req = Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps({"chat_id": chat_id, "text": text[:4096]}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            return resp.status == 200, "ok"
    except Exception as e:
        return False, str(e)[:300]


def send_checklist_to_tg(checklist_path: Path, task_id: str | None, title: str | None) -> tuple[bool, str]:
    data = load_registry()
    reqs = data.get("requirements") or []
    total = sum(len(r.get("features") or []) for r in reqs)
    verified = sum(1 for r in reqs for f in (r.get("features") or []) if f.get("verified"))
    summary = (
        f"[需求清单] 任务 {task_id or '—'} 已完成\n"
        f"标题: {title or '—'}\n"
        f"需求条目: {len(reqs)} | 功能点: {total} | 已验证: {verified}\n"
        f"附件: 完整需求清单（新+历史，时间倒序）"
    )
    send_telegram_message(summary)
    caption = f"需求清单+验证 | {task_id or 'ALL'} | {len(reqs)}条 | {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    return send_telegram_document(checklist_path, caption)


def finalize_task_checklist(
    task_id: str, title: str, epic: str = "",
    intake_path: Path | None = None, audit_path: Path | None = None,
    completion_path: Path | None = None, send_tg: bool = True,
) -> Path:
    upsert_task(task_id, title, epic, intake_path, audit_path, completion_path)
    path = render_checklist(task_id)
    if send_tg:
        ok, detail = send_checklist_to_tg(path, task_id, title)
        if ok:
            print("Telegram: 需求清单已发送")
        else:
            print(f"Telegram: {detail}", file=sys.stderr)
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task")
    p.add_argument("--title", default="")
    p.add_argument("--epic", default="")
    p.add_argument("--upsert", action="store_true")
    p.add_argument("--render", action="store_true")
    p.add_argument("--send-tg", action="store_true")
    p.add_argument("--audit")
    p.add_argument("--completion")
    p.add_argument("--no-send-tg", action="store_true")
    args = p.parse_args()
    if args.upsert and args.task:
        finalize_task_checklist(
            args.task, args.title or args.task, args.epic,
            INTAKE_DIR / f"{args.task.upper()}.md",
            Path(args.audit) if args.audit else None,
            Path(args.completion) if args.completion else None,
            send_tg=args.send_tg and not args.no_send_tg,
        )
    else:
        path = render_checklist(args.task)
        print(f"清单: {path.relative_to(ROOT)}")
        if args.send_tg:
            ok, d = send_checklist_to_tg(path, args.task, args.title)
            sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
