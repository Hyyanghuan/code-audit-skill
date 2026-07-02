"""审计执行报告归档 — Bug、测试用例、功能清单、模块结果等。"""
from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.database import get_job, list_jobs_page
from app.services.scan_logs import build_step_log

MODULE_LABELS = {
    "gitleaks": "Gitleaks 敏感密钥扫描",
    "super_linter": "Super-Linter 规范检查",
    "bandit": "Bandit Python 安全扫描",
    "dependency_scan": "Trivy 依赖漏洞扫描",
    "custom_rules": "自定义业务规则扫描",
    "sast_patterns": "SAST 词法/语法扫描",
    "taint_analysis": "SAST 污点分析",
    "control_flow": "SAST 控制流分析",
    "config_audit": "配置文件审计",
    "specialized_security": "专项安全审计",
    "diff_audit": "版本差分审计",
    "coverage_audit": "覆盖率驱动审计",
    "runtime_audit": "DAST/IAST 运行时建议",
    "manual_checklist": "人工深度审计清单",
}


def _artifacts_path(job: dict) -> Path:
    p = job.get("artifacts_path")
    if p:
        return Path(p)
    return Path(settings.data_dir) / "jobs" / job["id"] / "artifacts"


def _job_dir(job_id: str) -> Path:
    return Path(settings.data_dir) / "jobs" / job_id


def _read_text(path: Path, limit: int = 2_000_000) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > limit:
        return text[:limit] + f"\n\n... (已截断，共 {len(text)} 字符)"
    return text


def _load_json(path: Path, default=None):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _step_log(job_dir: Path, job_id: str, step_id: str) -> str:
    log = build_step_log(job_dir, step_id, job_id=job_id, data_dir=settings.data_dir)
    if log.strip() in ("步骤不存在", "尚未执行，请等待流水线到达此步骤。"):
        return ""
    return log


def _bug_count(artifacts: Path) -> int:
    data = _load_json(artifacts / "audit-bugs.json", {})
    bugs = data.get("bugs") or [] if isinstance(data, dict) else []
    return len(bugs) if isinstance(bugs, list) else 0


def _test_case_count(artifacts: Path) -> int:
    data = _load_json(artifacts / "test-cases.json", {})
    cases = data.get("test_cases") or [] if isinstance(data, dict) else []
    return len(cases) if isinstance(cases, list) else 0


def _build_test_cases_md_from_json(data: dict, title: str = "验收测试用例") -> str:
    cases = data.get("test_cases") or []
    if not cases:
        return ""
    lines = [
        f"# {title}",
        "",
        f"- 用例总数: {len(cases)}",
        f"- 已执行: {'是' if data.get('executed') else '否'}",
        "",
        "| TC-ID | 设计方法 | 场景 | 测试功能 | 功能描述 | 预期结果 | 测试结果 | 通过 |",
        "|-------|----------|------|----------|----------|----------|----------|------|",
    ]
    for c in cases:
        passed = c.get("passed")
        ps = "是" if passed is True else ("否" if passed is False else "待执行")
        lines.append(
            f"| {c.get('tc_id', '')} | {c.get('design_method', '')} | {c.get('scenario_category', '')} "
            f"| {c.get('test_function', '')} | {c.get('function_description', '')} "
            f"| {c.get('expected_result', '')} | {c.get('test_result', '待执行')} | {ps} |"
        )
    return "\n".join(lines)


def _filter_cases_by_category(data: dict | None, category: str) -> list:
    cases = (data or {}).get("test_cases") or []
    return [c for c in cases if c.get("case_category", "audit") == category]


def _build_category_test_md(cases: list, title: str, stats: dict | None = None) -> str:
    if not cases:
        return ""
    lines = [f"# {title}", ""]
    if stats:
        lines.append(
            f"- 总数: {stats.get('total', len(cases))} · "
            f"通过: {stats.get('passed', 0)} · 失败: {stats.get('failed', 0)}"
        )
        lines.append("")
    lines.extend([
        "| TC-ID | 设计方法 | 场景 | 测试功能 | 功能描述 | 预期结果 | 测试结果 | 通过 |",
        "|-------|----------|------|----------|----------|----------|----------|------|",
    ])
    for c in cases:
        passed = c.get("passed")
        ps = "是" if passed is True else ("否" if passed is False else "待执行")
        lines.append(
            f"| {c.get('tc_id', '')} | {c.get('design_method', '')} | {c.get('scenario_category', '')} "
            f"| {c.get('test_function', '')} | {c.get('function_description', '')} "
            f"| {c.get('expected_result', '')} | {c.get('test_result', '待执行')} | {ps} |"
        )
    return "\n".join(lines)


def _build_category_results_md(title: str, report: dict | None, cases: list) -> str:
    if not report and not cases:
        return ""
    parts = [f"# {title}", ""]
    stats = (report or {}).get("stats")
    if stats:
        parts.append(
            f"- 总数: {stats.get('total', 0)} · 通过: {stats.get('passed', 0)} · 失败: {stats.get('failed', 0)}"
        )
        parts.append("")
    subset = (report or {}).get("test_cases") or cases
    if subset:
        parts.extend(["## 执行明细", "", "| TC-ID | 测试功能 | 测试结果 | 通过 |", "|-------|----------|----------|------|"])
        for c in subset:
            ps = "是" if c.get("passed") is True else ("否" if c.get("passed") is False else "待执行")
            parts.append(
                f"| {c.get('tc_id', '')} | {c.get('test_function', '')} "
                f"| {c.get('test_result', '')} | {ps} |"
            )
    return "\n".join(parts)


def _build_test_results_md(artifacts: Path, cases_data: dict | None, report: dict | None, exec_log: str) -> str:
    parts: list[str] = ["# 测试用例执行结果", ""]
    stats = (cases_data or {}).get("execution_stats") or (report or {}).get("stats")
    if stats:
        parts.append(
            f"- 总数: {stats.get('total', 0)} · 通过: {stats.get('passed', 0)} · 失败: {stats.get('failed', 0)}"
        )
        parts.append("")
    if report and report.get("test_cases"):
        parts.append("## 用例执行明细")
        parts.append("")
        parts.append("| TC-ID | 测试功能 | 测试结果 | 通过 |")
        parts.append("|-------|----------|----------|------|")
        for c in report["test_cases"]:
            ps = "是" if c.get("passed") is True else ("否" if c.get("passed") is False else "待执行")
            parts.append(
                f"| {c.get('tc_id', '')} | {c.get('test_function', '')} "
                f"| {c.get('test_result', '')} | {ps} |"
            )
        parts.append("")
    if exec_log.strip():
        parts.extend(["## 执行日志", "", "```", exec_log.rstrip(), "```"])
    return "\n".join(parts) if len(parts) > 2 else ""


def _build_features_md(checklist_md: str, cases_data: dict | None) -> str:
    parts: list[str] = []
    if checklist_md.strip():
        parts.append(checklist_md.rstrip())
    cases = (cases_data or {}).get("test_cases") or []
    funcs: dict[str, str] = {}
    for c in cases:
        fn = (c.get("test_function") or "").strip()
        if fn and fn not in funcs:
            funcs[fn] = c.get("function_description") or ""
    if funcs:
        if parts:
            parts.extend(["", "---", ""])
        parts.append("# 检测功能清单（来自测试用例）")
        parts.append("")
        parts.append("| 功能 | 功能描述 |")
        parts.append("|------|----------|")
        for fn, desc in sorted(funcs.items()):
            parts.append(f"| {fn} | {desc} |")
    return "\n".join(parts)


def _build_modules_md(summary: dict, pipeline: dict | None) -> str:
    modules = summary.get("modules") or {}
    if not modules and not pipeline:
        return ""
    lines = [
        "# 审计模块功能实现结果",
        "",
        f"- 审计状态: {summary.get('audit_status', '-')}",
        f"- 问题总数: {summary.get('total_findings', 0)}",
        "",
        "## 模块执行汇总",
        "",
        "| 模块 | 名称 | 状态 | 发现数 | 说明 |",
        "|------|------|------|--------|------|",
    ]
    for mod, data in modules.items():
        if not isinstance(data, dict):
            continue
        label = MODULE_LABELS.get(mod, mod)
        lines.append(
            f"| {mod} | {label} | {data.get('status', '-')} | {data.get('findings', 0)} "
            f"| {(data.get('message') or '')[:120]} |"
        )
    if pipeline:
        lines.extend(["", "## 流水线步骤状态", ""])
        for step in pipeline.get("steps") or []:
            if step.get("status") == "pending":
                continue
            label = step.get("label") or step.get("id")
            lines.append(
                f"- **{label}** — {step.get('status')} "
                f"({step.get('findings', 0)} 项) {step.get('message') or ''}"
            )
    return "\n".join(lines)


def list_execution_reports(page: int = 1, per_page: int = 30) -> tuple[list[dict], int]:
    items, total = list_jobs_page(page=page, per_page=per_page)
    rows: list[dict] = []
    for job in items:
        art = _artifacts_path(job)
        count = _bug_count(art) or int(job.get("total_findings") or 0)
        tc_count = _test_case_count(art)
        func_count = len(_filter_cases_by_category(_load_json(art / "test-cases.json"), "functional"))
        api_count = len(_filter_cases_by_category(_load_json(art / "test-cases.json"), "api"))
        rows.append({
            "job_id": job["id"],
            "repo_full_name": job.get("repo_full_name", ""),
            "branch": job.get("branch", ""),
            "status": job.get("status", ""),
            "created_at": job.get("created_at"),
            "total_findings": job.get("total_findings", 0),
            "bug_count": count,
            "test_case_count": tc_count,
            "functional_case_count": func_count,
            "api_case_count": api_count,
            "has_audit_bugs_md": (art / "audit-bugs.md").is_file(),
            "has_test_cases": (art / "test-cases.md").is_file() or (art / "test-cases.json").is_file(),
            "has_functional_cases": (art / "test-cases-functional.md").is_file() or func_count > 0,
            "has_api_cases": (art / "test-cases-api.md").is_file() or api_count > 0,
            "has_test_results": (art / "test-cases-execution.log").is_file() or (art / "test-cases-report.json").is_file(),
            "has_features": (art / "manual-audit-checklist.md").is_file() or tc_count > 0,
            "has_modules": (art / "audit-summary.json").is_file(),
            "has_content": True,
        })
    return rows, total


def get_execution_report(job_id: str) -> dict | None:
    job = get_job(job_id)
    if not job:
        return None
    art = _artifacts_path(job)
    job_dir = _job_dir(job_id)
    pipeline = _load_json(job_dir / "pipeline.json", {})

    audit_bugs_md = _read_text(art / "audit-bugs.md")
    bugs_json = _load_json(art / "audit-bugs.json")
    bug_log = _read_text(job_dir / "step-logs" / "generate_bug_report.log") or _step_log(
        job_dir, job_id, "generate_bug_report"
    )

    test_cases_md = _read_text(art / "test-cases.md")
    test_cases_json = _load_json(art / "test-cases.json")
    if not test_cases_md.strip() and test_cases_json:
        audit_only = _filter_cases_by_category(test_cases_json, "audit")
        test_cases_md = _build_test_cases_md_from_json(
            {"test_cases": audit_only, "executed": test_cases_json.get("executed")},
            title="代码审计验收测试用例",
        )

    functional_md = _read_text(art / "test-cases-functional.md")
    functional_json = _load_json(art / "test-cases-functional.json")
    func_cases = _filter_cases_by_category(test_cases_json, "functional")
    if not functional_md.strip():
        if functional_json and functional_json.get("test_cases"):
            functional_md = _build_category_test_md(
                functional_json["test_cases"], "功能测试用例（源码扫描）",
            )
        elif func_cases:
            functional_md = _build_category_test_md(func_cases, "功能测试用例（源码扫描）")

    api_md = _read_text(art / "test-cases-api.md")
    api_json = _load_json(art / "test-cases-api.json")
    api_cases = _filter_cases_by_category(test_cases_json, "api")
    if not api_md.strip():
        if api_json and api_json.get("test_cases"):
            api_md = _build_category_test_md(api_json["test_cases"], "接口测试用例（源码扫描）")
        elif api_cases:
            api_md = _build_category_test_md(api_cases, "接口测试用例（源码扫描）")

    exec_log = _read_text(art / "test-cases-execution.log")
    test_report = _load_json(art / "test-cases-report.json", {})
    func_report = _load_json(art / "test-cases-functional-report.json", {})
    api_report = _load_json(art / "test-cases-api-report.json", {})
    test_results_md = _build_test_results_md(art, test_cases_json, test_report, exec_log)
    functional_results_md = _build_category_results_md(
        "功能测试用例执行结果", func_report, func_cases,
    )
    api_results_md = _build_category_results_md(
        "接口测试用例执行结果", api_report, api_cases,
    )
    gen_tc_log = _step_log(job_dir, job_id, "generate_test_cases")
    exec_tc_log = _step_log(job_dir, job_id, "execute_test_cases")

    checklist_md = _read_text(art / "manual-audit-checklist.md")
    features_md = _build_features_md(checklist_md, test_cases_json)

    summary = _load_json(art / "audit-summary.json", {})
    modules_md = _build_modules_md(summary, pipeline)

    return {
        "job_id": job_id,
        "repo_full_name": job.get("repo_full_name", ""),
        "branch": job.get("branch", ""),
        "status": job.get("status", ""),
        "created_at": job.get("created_at"),
        "audit_bugs_md": audit_bugs_md,
        "audit_bugs_json": bugs_json,
        "generate_bug_report_log": bug_log,
        "test_cases_md": test_cases_md,
        "test_cases_json": test_cases_json,
        "functional_test_cases_md": functional_md,
        "functional_test_cases_json": functional_json or {"test_cases": func_cases},
        "api_test_cases_md": api_md,
        "api_test_cases_json": api_json or {"test_cases": api_cases},
        "test_results_md": test_results_md,
        "functional_test_results_md": functional_results_md,
        "api_test_results_md": api_results_md,
        "test_cases_execution_log": exec_log,
        "generate_test_cases_log": gen_tc_log,
        "execute_test_cases_log": exec_tc_log or exec_log,
        "features_md": features_md,
        "manual_checklist_md": checklist_md,
        "modules_result_md": modules_md,
        "audit_summary": summary,
        "has_audit_bugs_md": bool(audit_bugs_md.strip()),
        "has_report_log": bool(bug_log.strip()),
        "has_test_cases": bool(test_cases_md.strip()),
        "has_functional_cases": bool(functional_md.strip()),
        "has_api_cases": bool(api_md.strip()),
        "has_test_results": bool(test_results_md.strip() or exec_log.strip()),
        "has_functional_results": bool(functional_results_md.strip()),
        "has_api_results": bool(api_results_md.strip()),
        "has_features": bool(features_md.strip()),
        "has_modules": bool(modules_md.strip()),
    }


# 兼容旧接口名
list_bugs_archive = list_execution_reports
get_bugs_bundle = get_execution_report
