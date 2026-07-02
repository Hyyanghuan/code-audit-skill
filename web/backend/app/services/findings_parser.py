"""从审计产物解析结构化问题（含文件位置与失败原因）。"""
from __future__ import annotations

import json
from pathlib import Path


def _load_json(path: Path, default=None):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _issue_row(raw: dict, index: int) -> dict:
    return {
        "id": raw.get("bug_id") or raw.get("id") or f"{raw.get('source', 'issue')}-{index}",
        "source": raw.get("source", ""),
        "module_label": raw.get("error_function") or raw.get("module_label") or raw.get("source", ""),
        "function_description": raw.get("function_description", ""),
        "severity": raw.get("severity", "medium"),
        "message": raw.get("error_reason") or raw.get("message", ""),
        "file_path": raw.get("file_path", ""),
        "line_number": raw.get("line_number", ""),
        "code_snippet": (raw.get("error_code") or raw.get("code_snippet") or "")[:4000],
        "fix_suggestion": raw.get("fix_suggestion", ""),
        "category": raw.get("category", ""),
        "kind": raw.get("kind", "bug"),
    }


def _dedupe_raw(items: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for item in items:
        key = (
            item.get("source", ""),
            item.get("file_path", ""),
            str(item.get("line_number", "")),
            (item.get("error_reason") or item.get("message") or "")[:120],
            (item.get("error_code") or item.get("code_snippet") or "")[:120],
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _bugs_from_step_pipeline(pipeline: dict) -> list[dict]:
    bugs: list[dict] = []
    for step in pipeline.get("steps") or []:
        if step.get("status") not in ("error", "failure"):
            continue
        detail = (
            step.get("error_detail")
            or step.get("stderr")
            or step.get("stdout")
            or ""
        )
        bugs.append({
            "id": f"step-{step.get('id')}",
            "source": step.get("id", "pipeline"),
            "error_function": step.get("label", step.get("id", "")),
            "function_description": "流水线步骤执行异常",
            "error_code": detail[:4000],
            "error_reason": step.get("message") or "步骤执行失败",
            "severity": "high" if step.get("status") == "error" else "medium",
            "file_path": "",
            "line_number": "",
            "category": step.get("status", ""),
            "fix_suggestion": "查看该步骤详情日志，修复后重新审计",
            "kind": "step_error",
        })
    return bugs


def _bugs_from_summary_modules(summary: dict) -> list[dict]:
    bugs: list[dict] = []
    for mod, data in (summary.get("modules") or {}).items():
        if not isinstance(data, dict):
            continue
        if data.get("status") not in ("failure", "error"):
            continue
        items = data.get("items") or []
        if items:
            for item in items:
                if not isinstance(item, dict):
                    continue
                bugs.append({
                    "source": mod,
                    "error_function": mod,
                    "function_description": data.get("message", ""),
                    "error_code": item.get("snippet") or item.get("code") or str(item)[:500],
                    "error_reason": item.get("message") or item.get("description") or data.get("message", ""),
                    "severity": item.get("severity", "medium"),
                    "file_path": item.get("file") or item.get("filename", ""),
                    "line_number": item.get("line") or item.get("line_number", ""),
                    "category": item.get("category") or mod,
                    "fix_suggestion": item.get("fix_suggestion", ""),
                    "kind": "module_item",
                })
        elif data.get("findings", 0) > 0 or data.get("message"):
            bugs.append({
                "source": mod,
                "error_function": mod,
                "function_description": "模块审计结果",
                "error_code": "(详见模块日志与报告)",
                "error_reason": data.get("message") or f"模块 {mod} 发现 {data.get('findings', 0)} 项问题",
                "severity": "high" if data.get("status") == "failure" else "medium",
                "file_path": "",
                "line_number": "",
                "category": mod,
                "fix_suggestion": "查看步骤详情与 artifacts 报告",
                "kind": "module_failure",
            })
    return bugs


def _bugs_from_artifact_reports(artifacts_dir: Path) -> list[dict]:
    """audit-bugs.json 缺失时，从各模块 report 文件兜底解析。"""
    bugs: list[dict] = []

    gitleaks = _load_json(artifacts_dir / "gitleaks-report.json", [])
    if isinstance(gitleaks, list):
        for item in gitleaks:
            bugs.append({
                "source": "gitleaks",
                "error_function": "Gitleaks 敏感密钥扫描",
                "function_description": "检测硬编码密钥泄露",
                "error_code": (item.get("Match") or item.get("Secret") or "")[:300],
                "error_reason": f"潜在密钥泄露: {item.get('Description', item.get('RuleID', 'secret'))}",
                "severity": "high",
                "file_path": item.get("File", ""),
                "line_number": item.get("StartLine", ""),
                "category": "hardcoded_secret",
                "fix_suggestion": "移除硬编码密钥，改用环境变量或密钥管理",
            })

    bandit = _load_json(artifacts_dir / "bandit-report.json", {})
    for item in (bandit.get("results") or []) if isinstance(bandit, dict) else []:
        sev = str(item.get("issue_severity", "MEDIUM")).lower()
        if sev == "low":
            continue
        bugs.append({
            "source": "bandit",
            "error_function": "Bandit Python 安全扫描",
            "function_description": "Python 安全问题",
            "error_code": (item.get("code") or "")[:300],
            "error_reason": item.get("issue_text", "Python 安全问题"),
            "severity": sev,
            "file_path": item.get("filename", ""),
            "line_number": item.get("line_number", ""),
            "category": item.get("test_id", "python_security"),
            "fix_suggestion": "按 Bandit 建议修复对应代码",
        })

    custom = _load_json(artifacts_dir / "custom-rules-report.json", {})
    for item in custom.get("findings", []) if isinstance(custom, dict) else []:
        bugs.append({
            "source": "custom_rules",
            "error_function": f"自定义规则 [{item.get('rule_id', '')}]",
            "function_description": "业务规则违规",
            "error_code": item.get("snippet", ""),
            "error_reason": item.get("message", "业务规则违规"),
            "severity": item.get("severity", "high"),
            "file_path": item.get("file", ""),
            "line_number": item.get("line", ""),
            "category": item.get("rule_id", "business_rule"),
            "fix_suggestion": "按规则说明修复代码",
        })

    return bugs


def parse_findings(artifacts_dir: Path, job_dir: Path | None = None) -> dict:
    bugs_data = _load_json(artifacts_dir / "audit-bugs.json", {})
    bug_list = bugs_data.get("bugs") or [] if isinstance(bugs_data, dict) else []
    if not isinstance(bug_list, list):
        bug_list = []

    pipeline = _load_json(job_dir / "pipeline.json", {}) if job_dir else {}
    summary = _load_json(artifacts_dir / "audit-summary.json", {})

    raw_bugs: list[dict] = [dict(b) for b in bug_list if isinstance(b, dict)]

    if not raw_bugs and artifacts_dir.is_dir():
        raw_bugs.extend(_bugs_from_artifact_reports(artifacts_dir))

    raw_bugs.extend(_bugs_from_summary_modules(summary))
    raw_bugs.extend(_bugs_from_step_pipeline(pipeline))
    raw_bugs = _dedupe_raw(raw_bugs)

    issues = [_issue_row(b, i) for i, b in enumerate(raw_bugs)]

    step_errors = []
    for step in pipeline.get("steps") or []:
        if step.get("status") in ("error", "failure"):
            step_errors.append({
                "step_id": step.get("id"),
                "step_label": step.get("label"),
                "status": step.get("status"),
                "message": step.get("message"),
                "error_detail": step.get("error_detail") or (step.get("stderr") or "")[:4000],
            })

    module_stats = []
    for mod, data in (summary.get("modules") or {}).items():
        if not isinstance(data, dict):
            continue
        module_stats.append({
            "module": mod,
            "status": data.get("status"),
            "findings": data.get("findings", 0),
            "message": data.get("message", ""),
        })

    return {
        "total": len(issues),
        "issues": issues,
        "step_errors": step_errors,
        "module_stats": module_stats,
        "audit_status": summary.get("audit_status"),
        "total_findings": summary.get("total_findings", 0) or len(issues),
    }


def get_step_detail(job_dir: Path, step_id: str) -> dict | None:
    pipeline = _load_json(job_dir / "pipeline.json")
    if not pipeline:
        return None
    artifacts = job_dir / "artifacts"
    findings = parse_findings(artifacts, job_dir)

    for step in pipeline.get("steps") or []:
        if step.get("id") != step_id:
            continue
        detail = dict(step)
        mod = step_id
        step_log = job_dir / "step-logs" / f"{step_id}.log"
        if step_log.is_file():
            detail["full_log"] = step_log.read_text(encoding="utf-8", errors="replace")
        log_path = detail.get("log_file")
        if log_path:
            lp = Path(log_path)
            if lp.is_file():
                detail["full_log"] = lp.read_text(encoding="utf-8", errors="replace")
        if not detail.get("full_log"):
            mod_log = artifacts / f"{mod}.log"
            if mod_log.is_file():
                detail["full_log"] = mod_log.read_text(encoding="utf-8", errors="replace")
        if not detail.get("full_log") and (detail.get("stdout") or detail.get("stderr")):
            parts = [detail.get("stdout") or "", detail.get("stderr") or ""]
            if detail.get("error_detail"):
                parts.append(detail["error_detail"])
            detail["full_log"] = "\n".join(p for p in parts if p).strip()
        for name in [f"{mod}-report.json", f"{mod.replace('_', '-')}-report.json"]:
            report = artifacts / name
            if report.exists():
                detail["report"] = _load_json(report)
                break
        summary = _load_json(artifacts / "audit-summary.json", {})
        modules = summary.get("modules") or {}
        if mod in modules:
            detail["module_result"] = modules[mod]
        detail["related_issues"] = [i for i in findings["issues"] if i["source"] == mod]
        return detail
    return None
