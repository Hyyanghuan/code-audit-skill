#!/usr/bin/env python3
"""
汇总各审计模块与失败测试用例，生成 Bug 报告（MD + JSON）。
字段：BUG-ID、错误功能、功能描述、错误代码、错误原因、严重级别、文件位置、修复建议等。
"""
import json
import os
import sys
from datetime import datetime, timezone

ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "/tmp/artifacts")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/tmp/results")
OUTPUT_MD = os.path.join(ARTIFACTS_DIR, "audit-bugs.md")
OUTPUT_JSON = os.path.join(ARTIFACTS_DIR, "audit-bugs.json")

MODULE_INFO = {
    "gitleaks": ("Gitleaks 敏感密钥扫描", "检测代码中硬编码的 API Key、Token、密码等敏感信息泄露"),
    "super_linter": ("Super-Linter 代码规范检查", "多语言静态编码规范与风格校验"),
    "bandit": ("Bandit Python 安全扫描", "Python 代码安全漏洞与危险模式检测"),
    "dependency_scan": ("Trivy 依赖漏洞扫描", "第三方依赖库已知 CVE 漏洞检测"),
    "custom_rules": ("自定义业务规则扫描", "按业务 YAML 规则匹配违规代码模式"),
    "sast_patterns": ("SAST 词法语法扫描", "危险函数、SQL拼接、硬编码密钥等模式匹配"),
    "taint_analysis": ("SAST 污点分析", "外部可控输入未经净化到达高危 Sink 点"),
    "control_flow": ("SAST 控制流分析", "异常吞没、鉴权空实现、逻辑分支缺陷"),
    "config_audit": ("配置文件安全审计", "yml/Dockerfile/env 明文密码与不安全配置"),
    "specialized_security": ("专项安全审计", "越权、文件上传、业务风险、日志脱敏等"),
    "diff_audit": ("版本差分增量审计", "git diff 变更文件中的新增安全风险"),
    "coverage_audit": ("覆盖率驱动审计", "低覆盖率区域需人工复核"),
    "runtime_audit": ("DAST/IAST 运行时建议", "动态测试盲区与运行时安全建议"),
    "test_case": ("验收测试用例", "审计流水线验收测试未通过项"),
}

FIX_HINTS = {
    "sql_injection": "使用参数化查询 / ORM 绑定变量，禁止字符串拼接 SQL",
    "command_injection": "避免 eval/exec/os.system，使用安全 API 白名单",
    "hardcoded_secret": "将密钥移至环境变量或密钥管理服务，禁止硬编码",
    "xss": "对用户输入做 HTML 转义，避免 innerHTML 直接赋值",
    "deserialization": "使用 safe_load 等安全反序列化方式",
    "taint_sink": "对外部输入做校验与净化后再传入危险函数",
    "config": "移除配置文件明文密码，关闭生产 DEBUG，启用 SSL 验证",
    "file_upload": "校验文件类型白名单，重命名存储，禁止用户控制路径",
    "business_risk": "服务端校验金额/价格，禁止信任客户端输入",
    "log_desensitize": "日志脱敏处理手机号/身份证/银行卡等敏感字段",
    "general": "按安全规范修复后重新提交并触发审计",
}


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fix_suggestion(category, message=""):
    cat = (category or "general").lower()
    for key, hint in FIX_HINTS.items():
        if key in cat:
            return hint
    if "password" in message.lower() or "secret" in message.lower():
        return FIX_HINTS["hardcoded_secret"]
    if "sql" in message.lower():
        return FIX_HINTS["sql_injection"]
    return FIX_HINTS["general"]


def collect_from_module_items(module, data):
    bugs = []
    func_name, func_desc = MODULE_INFO.get(module, (module, "代码审计模块"))
    items = data.get("items") or []

    for item in items:
        sev = item.get("severity", "medium")
        if sev in ("info", "low") and module not in ("gitleaks", "bandit", "custom_rules"):
            continue
        msg = item.get("message") or item.get("description") or data.get("message", "未知问题")
        bugs.append({
            "source": module,
            "error_function": func_name,
            "function_description": func_desc,
            "error_code": item.get("snippet") or item.get("Match") or item.get("code", ""),
            "error_reason": msg,
            "severity": sev,
            "file_path": item.get("file") or item.get("File", ""),
            "line_number": item.get("line") or item.get("StartLine", item.get("line_number", "")),
            "category": item.get("category") or item.get("rule_id") or module,
            "fix_suggestion": fix_suggestion(item.get("category", ""), msg),
            "module_status": data.get("status", ""),
        })
    return bugs


def collect_gitleaks_report():
    bugs = []
    path = os.path.join(ARTIFACTS_DIR, "gitleaks-report.json")
    data = load_json(path, [])
    if not isinstance(data, list):
        return bugs
    func_name, func_desc = MODULE_INFO["gitleaks"]
    for item in data:
        bugs.append({
            "source": "gitleaks",
            "error_function": func_name,
            "function_description": func_desc,
            "error_code": item.get("Match", item.get("Secret", ""))[:200],
            "error_reason": f"检测到潜在密钥泄露: {item.get('Description', item.get('RuleID', 'secret'))}",
            "severity": "high",
            "file_path": item.get("File", ""),
            "line_number": item.get("StartLine", ""),
            "category": "hardcoded_secret",
            "fix_suggestion": FIX_HINTS["hardcoded_secret"],
            "module_status": "failure",
        })
    return bugs


def collect_bandit_report():
    bugs = []
    path = os.path.join(ARTIFACTS_DIR, "bandit-report.json")
    data = load_json(path, {})
    results = data.get("results", []) if isinstance(data, dict) else []
    func_name, func_desc = MODULE_INFO["bandit"]
    for item in results:
        sev = item.get("issue_severity", "MEDIUM").lower()
        if sev == "low":
            continue
        bugs.append({
            "source": "bandit",
            "error_function": func_name,
            "function_description": func_desc,
            "error_code": item.get("code", "")[:300],
            "error_reason": item.get("issue_text", "Python 安全问题"),
            "severity": sev,
            "file_path": item.get("filename", ""),
            "line_number": item.get("line_number", ""),
            "category": item.get("test_id", "python_security"),
            "fix_suggestion": fix_suggestion("command_injection", item.get("issue_text", "")),
            "module_status": "failure",
        })
    return bugs


def collect_custom_rules_report():
    bugs = []
    path = os.path.join(ARTIFACTS_DIR, "custom-rules-report.json")
    data = load_json(path, {})
    func_name, func_desc = MODULE_INFO["custom_rules"]
    for item in data.get("findings", []):
        if item.get("severity") not in ("high", "critical", "medium"):
            continue
        bugs.append({
            "source": "custom_rules",
            "error_function": f"{func_name} [{item.get('rule_id', '')}]",
            "function_description": func_desc,
            "error_code": item.get("snippet", ""),
            "error_reason": item.get("message", "业务规则违规"),
            "severity": item.get("severity", "high"),
            "file_path": item.get("file", ""),
            "line_number": item.get("line", ""),
            "category": item.get("rule_id", "business_rule"),
            "fix_suggestion": fix_suggestion(item.get("rule_id", ""), item.get("message", "")),
            "module_status": "failure",
        })
    return bugs


def collect_trivy_report():
    bugs = []
    path = os.path.join(ARTIFACTS_DIR, "trivy-report.json")
    data = load_json(path, {})
    func_name, func_desc = MODULE_INFO["dependency_scan"]
    for result in data.get("Results", []) or []:
        target = result.get("Target", "")
        for vuln in result.get("Vulnerabilities", []) or []:
            if vuln.get("Severity") not in ("HIGH", "CRITICAL"):
                continue
            bugs.append({
                "source": "dependency_scan",
                "error_function": func_name,
                "function_description": func_desc,
                "error_code": f"{vuln.get('PkgName', '')}@{vuln.get('InstalledVersion', '')}",
                "error_reason": f"{vuln.get('VulnerabilityID', '')}: {vuln.get('Title', vuln.get('Description', ''))[:200]}",
                "severity": vuln.get("Severity", "HIGH").lower(),
                "file_path": target,
                "line_number": "",
                "category": "dependency_vulnerability",
                "fix_suggestion": f"升级至 {vuln.get('FixedVersion', '最新安全版本')}",
                "module_status": "failure",
            })
    return bugs


def collect_module_failures():
    """模块级失败（无明细 items 时）。"""
    bugs = []
    summary = load_json(os.path.join(ARTIFACTS_DIR, "audit-summary.json"), {})
    for mod, data in summary.get("modules", {}).items():
        if data.get("status") not in ("failure", "error"):
            continue
        if data.get("findings", 0) > 0 and data.get("items"):
            continue
        func_name, func_desc = MODULE_INFO.get(mod, (mod, ""))
        bugs.append({
            "source": mod,
            "error_function": func_name,
            "function_description": func_desc,
            "error_code": "(模块级失败，详见日志)",
            "error_reason": data.get("message", f"模块 {mod} 审计失败"),
            "severity": "high" if data.get("status") == "failure" else "medium",
            "file_path": "",
            "line_number": "",
            "category": mod,
            "fix_suggestion": FIX_HINTS["general"],
            "module_status": data.get("status", ""),
        })
    return bugs


def collect_failed_test_cases():
    bugs = []
    path = os.path.join(ARTIFACTS_DIR, "test-cases.json")
    data = load_json(path, {})
    func_name, func_desc = MODULE_INFO["test_case"]
    for tc in data.get("test_cases", []):
        if tc.get("passed") is not False:
            continue
        bugs.append({
            "source": "test_case",
            "error_function": tc.get("test_function", func_name),
            "function_description": tc.get("function_description", func_desc),
            "error_code": tc.get("tc_id", ""),
            "error_reason": tc.get("test_result", "验收测试未通过"),
            "severity": "medium",
            "file_path": tc.get("tc_id", ""),
            "line_number": "",
            "category": tc.get("scenario_code", "test_failure"),
            "fix_suggestion": f"预期: {tc.get('expected_result', '')}",
            "module_status": "failure",
            "test_steps": tc.get("test_steps", []),
        })
    return bugs


def dedupe_bugs(bugs):
    seen = set()
    unique = []
    for b in bugs:
        key = (b.get("source"), b.get("file_path"), b.get("line_number"),
               b.get("error_reason", "")[:80], b.get("error_code", "")[:80])
        if key in seen:
            continue
        seen.add(key)
        unique.append(b)
    return unique


def export_markdown(bugs, meta):
    lines = [
        "# 代码审计 Bug 报告",
        "",
        f"> 生成时间: {meta['generated_at']}",
        f"> 仓库: {meta['repository']}",
        f"> 分支: {meta['ref']}",
        f"> Commit: `{meta['sha'][:8] if meta.get('sha') else ''}`",
        f"> 审计状态: **{meta['audit_status']}**",
        f"> Bug 总数: **{len(bugs)}** （高危: {meta['high_count']} | 中危: {meta['medium_count']}）",
        f"> 运行链接: {meta.get('run_url', '')}",
        "",
    ]

    if not bugs:
        lines.extend([
            "## 无 Bug",
            "",
            "本次审计未发现错误或所有问题已修复。",
            "",
        ])
    else:
        lines.extend([
            "## Bug 汇总表",
            "",
            "| BUG-ID | 严重级别 | 错误功能 | 文件位置 | 错误原因 |",
            "|--------|----------|----------|----------|----------|",
        ])
        for b in bugs:
            loc = f"{b.get('file_path', '')}"
            if b.get("line_number"):
                loc += f":{b['line_number']}"
            reason = str(b.get("error_reason", "")).replace("|", "\\|")[:80]
            lines.append(
                f"| {b['bug_id']} | {b.get('severity', '')} | {b.get('error_function', '')} "
                f"| `{loc}` | {reason} |"
            )

        lines.extend(["", "---", "", "## Bug 详情", ""])
        for b in bugs:
            lines.append(f"### {b['bug_id']} [{b.get('severity', '').upper()}] {b.get('error_function', '')}")
            lines.append("")
            lines.append(f"- **功能描述**: {b.get('function_description', '')}")
            lines.append(f"- **错误原因**: {b.get('error_reason', '')}")
            lines.append(f"- **文件位置**: `{b.get('file_path', '')}`" +
                         (f" 第 {b['line_number']} 行" if b.get("line_number") else ""))
            lines.append(f"- **问题分类**: {b.get('category', '')}")
            lines.append(f"- **来源模块**: {b.get('source', '')}")
            lines.append(f"- **修复建议**: {b.get('fix_suggestion', '')}")
            if b.get("test_steps"):
                lines.append(f"- **测试步骤**: {' → '.join(b['test_steps'])}")
            lines.append("")
            lines.append("**错误代码**:")
            lines.append("")
            lines.append("```")
            code = b.get("error_code", "") or "(无代码片段)"
            lines.append(code[:2000])
            lines.append("```")
            lines.append("")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    all_bugs = []

    # 专用报告文件（明细更丰富）
    all_bugs.extend(collect_gitleaks_report())
    all_bugs.extend(collect_bandit_report())
    all_bugs.extend(collect_custom_rules_report())
    all_bugs.extend(collect_trivy_report())

    # 引擎模块 items
    modules = [
        "sast_patterns", "taint_analysis", "control_flow", "config_audit",
        "specialized_security", "diff_audit", "coverage_audit",
    ]
    for mod in modules:
        data = load_json(os.path.join(RESULTS_DIR, f"{mod}.json"), {})
        if data:
            all_bugs.extend(collect_from_module_items(mod, data))

    all_bugs.extend(collect_module_failures())
    all_bugs.extend(collect_failed_test_cases())

    all_bugs = dedupe_bugs(all_bugs)

    # 分配 BUG-ID
    for i, b in enumerate(all_bugs, 1):
        b["bug_id"] = f"BUG-{i:04d}"

    summary = load_json(os.path.join(ARTIFACTS_DIR, "audit-summary.json"), {})
    high_count = sum(1 for b in all_bugs if b.get("severity") in ("high", "critical"))
    medium_count = sum(1 for b in all_bugs if b.get("severity") == "medium")

    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "repository": os.environ.get("GITHUB_REPOSITORY", summary.get("repository", "")),
        "ref": os.environ.get("GITHUB_REF", summary.get("ref", "")),
        "sha": os.environ.get("GITHUB_SHA", summary.get("sha", "")),
        "audit_status": summary.get("audit_status", "unknown"),
        "run_url": summary.get("run_url", ""),
        "total_bugs": len(all_bugs),
        "high_count": high_count,
        "medium_count": medium_count,
    }

    payload = {"meta": meta, "bugs": all_bugs}
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    export_markdown(all_bugs, meta)

    print(f"BUG_COUNT={len(all_bugs)}")
    print(f"BUG_HIGH={high_count}")
    print(f"Generated: {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
