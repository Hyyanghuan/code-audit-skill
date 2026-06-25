#!/usr/bin/env python3
"""执行验收测试用例，回写测试结果与是否通过，并更新汇总。"""
import csv
import json
import os
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
    }
    handler = handlers.get(atype)
    if not handler:
        return False, f"未知断言类型: {atype}", False
    return handler()


def export_markdown(cases, stats):
    md_path = os.path.join(ARTIFACTS_DIR, "test-cases.md")
    lines = [
        "# 代码审计验收测试用例",
        "",
        f"> 执行时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"> 总计: {stats['total']} | ✅ 通过: {stats['passed']} | ❌ 失败: {stats['failed']}",
        "",
        "| TC-ID | 测试功能 | 功能描述 | 测试内容描述 | 测试步骤 | 预期结果 | 测试结果 | 是否通过 |",
        "|-------|----------|----------|--------------|----------|----------|----------|----------|",
    ]
    for c in cases:
        steps = "<br>".join(f"{i+1}. {s}" for i, s in enumerate(c["test_steps"]))
        passed = c.get("passed")
        passed_str = "✅ 是" if passed is True else ("❌ 否" if passed is False else "⏳ 待执行")
        lines.append(
            f"| {c['tc_id']} | {c['test_function']} | {c['function_description']} "
            f"| {c['test_content_description']} | {steps} | {c['expected_result']} "
            f"| {c.get('test_result', '')} | {passed_str} |"
        )
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def export_csv(cases):
    csv_path = os.path.join(ARTIFACTS_DIR, "test-cases.csv")
    fields = ["TC-ID", "测试功能", "功能描述", "测试内容描述", "测试步骤",
              "预期结果", "测试结果", "是否通过"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in cases:
            passed = c.get("passed")
            w.writerow({
                "TC-ID": c["tc_id"],
                "测试功能": c["test_function"],
                "功能描述": c["function_description"],
                "测试内容描述": c["test_content_description"],
                "测试步骤": " | ".join(c["test_steps"]),
                "预期结果": c["expected_result"],
                "测试结果": c.get("test_result", ""),
                "是否通过": "是" if passed is True else ("否" if passed is False else "待执行"),
            })


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

    export_markdown(cases, stats)
    export_csv(cases)
    merge_into_audit_summary(cases, stats)

    log(f"执行完成: 通过={passed_count} 失败={failed_count}")
    print(f"TEST_PASSED={passed_count}")
    print(f"TEST_FAILED={failed_count}")
    print(f"TEST_ALL_PASSED={'true' if failed_count == 0 else 'false'}")
    return 0 if failed_count == 0 else 0  # 不阻断主流程


if __name__ == "__main__":
    sys.exit(main())
