#!/usr/bin/env python3
"""执行验收测试用例，回写测试结果与是否通过，并更新汇总。"""
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

ARTIFACTS_DIR = os.environ["ARTIFACTS_DIR"]
RESULTS_DIR = os.environ["RESULTS_DIR"]
CASES_JSON = os.path.join(ARTIFACTS_DIR, "test-cases.json")
SUMMARY_JSON = os.path.join(ARTIFACTS_DIR, "audit-summary.json")
EXEC_LOG = os.path.join(ARTIFACTS_DIR, "test-cases-execution.log")


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def log(msg):
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    with open(EXEC_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def check_module_skip(assertion, module_result):
    mod = assertion["module"]
    if module_result is None:
        return True, f"模块 {mod} 未执行（符合跳过预期）", True
    status = module_result.get("status", "unknown")
    if status == "skipped":
        return True, f"模块 {mod} status=skipped，符合跳过预期", True
    if not assertion.get("enabled", True):
        return True, f"模块 {mod} 已禁用且 status={status}", True
    return False, f"模块 {mod} 预期跳过但 status={status}", False


def check_module_executed(assertion, module_result):
    mod = assertion["module"]
    if module_result is None:
        return False, f"模块 {mod} 无结果文件，执行未完成", False
    status = module_result.get("status", "unknown")
    forbid = assertion.get("forbid_status", ["error"])
    valid = assertion.get("valid_status", ["success", "failure", "skipped"])
    findings = module_result.get("findings", 0)
    msg = module_result.get("message", "")

    if status in forbid:
        return False, f"模块 {mod} status={status}（禁止状态），message={msg}", False
    if status not in valid:
        return False, f"模块 {mod} status={status} 不在有效范围 {valid}", False
    return True, f"模块 {mod} status={status}, findings={findings}, message={msg}", True


def check_file_json_fields(assertion):
    fname = assertion["file"]
    path = os.path.join(ARTIFACTS_DIR, fname)
    if not os.path.isfile(path):
        return False, f"文件 {fname} 不存在", False
    data = load_json(path, {})
    missing = [f for f in assertion.get("fields", []) if f not in data]
    if missing:
        return False, f"{fname} 缺少字段: {missing}", False
    return True, f"{fname} 存在且包含必需字段 {assertion.get('fields')}", True


def check_audit_summary():
    summary = load_json(SUMMARY_JSON, {})
    if not summary:
        return False, "audit-summary.json 不存在或为空", False
    status = summary.get("audit_status")
    if status not in ("success", "failure", "skipped"):
        return False, f"audit_status={status} 无效", False
    modules = summary.get("modules", {})
    return True, f"audit_status={status}, modules={len(modules)}, total_findings={summary.get('total_findings', 0)}", True


def check_findings_consistency():
    summary = load_json(SUMMARY_JSON, {})
    if not summary:
        return False, "audit-summary.json 不存在", False
    reported = summary.get("total_findings", 0)
    calculated = sum(m.get("findings", 0) for m in summary.get("modules", {}).values())
    if reported != calculated:
        return False, f"total_findings={reported} 与模块累加={calculated} 不一致", False
    return True, f"total_findings={reported} 与模块累加一致", True


def check_empty_project_graceful():
    detect = load_json(os.path.join(ARTIFACTS_DIR, "detect-languages.json"), {})
    summary = load_json(SUMMARY_JSON, {})
    if not detect.get("is_empty"):
        return True, "非空项目，跳过空项目专项断言", True
    errors = []
    for mod, data in summary.get("modules", {}).items():
        if data.get("status") == "error":
            errors.append(mod)
    if errors:
        return False, f"空项目下模块 {errors} 出现 error 状态", False
    status = summary.get("audit_status", "unknown")
    return True, f"空项目降级正常，audit_status={status}", True


def _work_root() -> str:
    return os.environ.get("ABS_WORK_DIR") or os.environ.get("GITHUB_WORKSPACE") or "."


def check_source_symbol_exists(assertion):
    rel = assertion.get("file", "")
    symbol = assertion.get("symbol", "")
    kind = assertion.get("kind", "function")
    path = os.path.join(_work_root(), rel)
    if not os.path.isfile(path):
        return False, f"源文件 {rel} 不存在", False
    text = open(path, encoding="utf-8", errors="replace").read()
    if kind == "class":
        pat = rf"^class\s+{re.escape(symbol)}\s*[:\(]"
    else:
        pat = rf"^(?:async\s+)?def\s+{re.escape(symbol)}\s*\("
        if not re.search(pat, text, re.MULTILINE):
            pat = rf"(?:function|const)\s+{re.escape(symbol)}\s*[=\(]"
    if re.search(pat, text, re.MULTILINE):
        return True, f"符号 {symbol} 存在于 {rel}", True
    return False, f"符号 {symbol} 未在 {rel} 中找到", False


def check_api_route_in_source(assertion):
    rel = assertion.get("file", "")
    method = (assertion.get("method") or "GET").upper()
    route = assertion.get("path", "")
    path = os.path.join(_work_root(), rel)
    if not os.path.isfile(path):
        return False, f"源文件 {rel} 不存在", False
    text = open(path, encoding="utf-8", errors="replace").read()
    route_esc = re.escape(route)
    patterns = [
        rf'@(?:app|router|api|bp)\.{method.lower()}\(\s*["\']{route_esc}',
        rf'@app\.route\(\s*["\']{route_esc}',
        rf'path\(\s*["\']{route_esc}',
        rf'\.{method.lower()}\(\s*[`"\']{route_esc}',
        rf'HandleFunc\(\s*"{route_esc}"',
    ]
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True, f"路由 {method} {route} 已在 {rel} 中定义", True
    if route in text:
        return True, f"路径 {route} 在 {rel} 中出现（静态匹配）", True
    return False, f"路由 {method} {route} 未在 {rel} 中找到", False


def check_file_exists(assertion):
    fname = assertion["file"]
    path = os.path.join(ARTIFACTS_DIR, fname)
    if os.path.isfile(path):
        size = os.path.getsize(path)
        return True, f"文件 {fname} 存在 ({size} bytes)", True
    return False, f"文件 {fname} 不存在", False


def run_assertion(case):
    assertion = case.get("assertion", {})
    atype = assertion.get("type", "")
    module_result = None
    if "module" in assertion:
        module_result = load_json(os.path.join(RESULTS_DIR, f"{assertion['module']}.json"))

    handlers = {
        "module_skip": lambda: check_module_skip(assertion, module_result),
        "module_executed": lambda: check_module_executed(assertion, module_result),
        "file_json_fields": lambda: check_file_json_fields(assertion),
        "audit_summary": lambda: check_audit_summary(),
        "findings_consistency": lambda: check_findings_consistency(),
        "empty_project_graceful": lambda: check_empty_project_graceful(),
        "file_exists": lambda: check_file_exists(assertion),
        "source_symbol_exists": lambda: check_source_symbol_exists(assertion),
        "api_route_in_source": lambda: check_api_route_in_source(assertion),
    }
    handler = handlers.get(atype)
    if not handler:
        return False, f"未知断言类型: {atype}", False
    return handler()


def export_reports(cases, stats):
    """复用 generate-test-cases.py 的 MD/CSV 导出（含设计方法与场景分类）。"""
    import importlib.util
    gen_path = os.path.join(os.path.dirname(__file__), "generate-test-cases.py")
    spec = importlib.util.spec_from_file_location("gen_tc", gen_path)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    audit_cases = [c for c in cases if c.get("case_category", "audit") == "audit"]
    func_cases = [c for c in cases if c.get("case_category") == "functional"]
    api_cases = [c for c in cases if c.get("case_category") == "api"]

    def _stats(subset):
        passed = sum(1 for c in subset if c.get("passed") is True)
        failed = sum(1 for c in subset if c.get("passed") is False)
        return {"total": len(subset), "passed": passed, "failed": failed, "pending": len(subset) - passed - failed}

    gen.export_markdown(audit_cases, _stats(audit_cases), executed=True, filename="test-cases.md",
                        title="代码审计验收测试用例报告")
    if func_cases:
        gen.export_markdown(func_cases, _stats(func_cases), executed=True,
                            filename="test-cases-functional.md", title="功能测试用例报告（源码扫描）")
    if api_cases:
        gen.export_markdown(api_cases, _stats(api_cases), executed=True,
                            filename="test-cases-api.md", title="接口测试用例报告（源码扫描）")
    gen.export_csv(cases)


def _write_category_report(filename, cases, stats):
    subset_stats = {
        "total": len(cases),
        "passed": sum(1 for c in cases if c.get("passed") is True),
        "failed": sum(1 for c in cases if c.get("passed") is False),
    }
    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "stats": subset_stats,
        "test_cases": cases,
    }
    with open(os.path.join(ARTIFACTS_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def merge_into_audit_summary(cases, stats):
    summary = load_json(SUMMARY_JSON, {})
    summary["test_cases"] = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total": stats["total"],
        "passed": stats["passed"],
        "failed": stats["failed"],
        "pass_rate": f"{stats['passed']}/{stats['total']}",
        "all_passed": stats["failed"] == 0,
        "cases": [
            {
                "tc_id": c["tc_id"],
                "test_function": c["test_function"],
                "design_method": c.get("design_method", ""),
                "scenario_category": c.get("scenario_category", ""),
                "test_result": c.get("test_result", ""),
                "passed": c.get("passed"),
                "passed_label": "是" if c.get("passed") is True else ("否" if c.get("passed") is False else "待执行"),
            }
            for c in cases
        ],
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 独立执行报告
    report = {
        "executed_at": summary["test_cases"]["executed_at"],
        "stats": stats,
        "test_cases": cases,
    }
    with open(os.path.join(ARTIFACTS_DIR, "test-cases-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    func_cases = [c for c in cases if c.get("case_category") == "functional"]
    api_cases = [c for c in cases if c.get("case_category") == "api"]
    if func_cases:
        _write_category_report("test-cases-functional-report.json", func_cases, stats)
    if api_cases:
        _write_category_report("test-cases-api-report.json", api_cases, stats)


def main():
    payload = load_json(CASES_JSON)
    if not payload or not payload.get("test_cases"):
        log("ERROR: test-cases.json 不存在或为空")
        return 1

    cases = payload["test_cases"]
    passed_count = 0
    failed_count = 0

    log(f"开始执行 {len(cases)} 条测试用例")

    for case in cases:
        tc = case["tc_id"]
        try:
            ok, result_msg, _ = run_assertion(case)
            case["test_result"] = result_msg
            case["passed"] = ok
            case["executed_at"] = datetime.now(timezone.utc).isoformat()
            if ok:
                passed_count += 1
                log(f"[PASS] {tc}: {result_msg}")
            else:
                failed_count += 1
                log(f"[FAIL] {tc}: {result_msg}")
        except Exception as e:
            case["test_result"] = f"执行异常: {e}"
            case["passed"] = False
            failed_count += 1
            log(f"[ERROR] {tc}: {e}")

    stats = {"total": len(cases), "passed": passed_count, "failed": failed_count}
    payload["executed"] = True
    payload["execution_stats"] = stats
    payload["test_cases"] = cases

    with open(CASES_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    export_reports(cases, stats)
    merge_into_audit_summary(cases, stats)

    log(f"执行完成: 通过={passed_count} 失败={failed_count}")
    print(f"TEST_PASSED={passed_count}")
    print(f"TEST_FAILED={failed_count}")
    print(f"TEST_ALL_PASSED={'true' if failed_count == 0 else 'false'}")
    return 0 if failed_count == 0 else 0  # 不阻断主流程


if __name__ == "__main__":
    sys.exit(main())
