#!/usr/bin/env python3
"""根据代码审计配置与扫描结果，自动生成验收测试用例。"""
import json
import os
import sys
from datetime import datetime, timezone

ARTIFACTS_DIR = os.environ["ARTIFACTS_DIR"]
RESULTS_DIR = os.environ["RESULTS_DIR"]
OUTPUT_JSON = os.path.join(ARTIFACTS_DIR, "test-cases.json")

# 模块元数据
MODULE_META = {
    "gitleaks": {
        "name": "Gitleaks 敏感密钥扫描",
        "desc": "检测代码中的硬编码 API Key、Token、密码等敏感信息泄露",
        "content": "对目标工作目录执行 gitleaks 全量扫描，输出 JSON 报告",
        "steps": [
            "确认 enable-gitleaks 开关状态",
            "加载 gitleaks 配置与忽略规则",
            "扫描工作目录内所有文本文件",
            "解析 gitleaks-report.json 并统计 findings",
        ],
    },
    "super_linter": {
        "name": "Super-Linter 多语言规范检查",
        "desc": "对 Python/JS/YAML/Shell 等语言执行静态代码规范检查",
        "content": "基于项目语言检测结果，启用对应 linter 并扫描源码",
        "steps": [
            "读取 detect-languages.json 确定语言",
            "拉取 super-linter slim 镜像",
            "按 FILTER_REGEX_EXCLUDE 排除依赖目录",
            "执行 linter 并收集 ERROR 级别问题",
        ],
    },
    "bandit": {
        "name": "Bandit Python 安全扫描",
        "desc": "检测 Python 代码中的 SQL 注入、eval、硬编码密码等安全问题",
        "content": "递归扫描 .py 文件，输出 bandit JSON 报告",
        "steps": [
            "检测是否存在 Python 源码",
            "安装 bandit 并配置排除目录",
            "执行 bandit -r 扫描",
            "统计 HIGH/MEDIUM 级别问题数",
        ],
    },
    "dependency_scan": {
        "name": "依赖漏洞检测 (Trivy)",
        "desc": "扫描 requirements.txt/package.json/go.mod 等依赖清单中的已知漏洞",
        "content": "使用 trivy fs 扫描依赖目录，过滤 HIGH/CRITICAL 漏洞",
        "steps": [
            "识别项目依赖清单文件",
            "安装 trivy 并配置 skip-dirs",
            "执行 filesystem 漏洞扫描",
            "输出 trivy-report.json",
        ],
    },
    "custom_rules": {
        "name": "自定义业务规则扫描",
        "desc": "按 business-rules.yaml 中定义的正则规则扫描违规代码模式",
        "content": "遍历源码文件，匹配 eval/硬编码密码/SQL 拼接等业务规则",
        "steps": [
            "加载 custom-rules YAML 配置",
            "按 paths 过滤目标文件",
            "逐行正则匹配并记录 findings",
            "统计 high 级别违规数",
        ],
    },
}

ENV_FLAGS = {
    "gitleaks": "ENABLE_GITLEAKS",
    "super_linter": "ENABLE_SUPER_LINTER",
    "bandit": "ENABLE_BANDIT",
    "dependency_scan": "ENABLE_DEPENDENCY",
    "custom_rules": "ENABLE_CUSTOM",
}


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default if default is not None else {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tc_id(index: int) -> str:
    return f"TC-AUDIT-{index:03d}"


def pending_case(**kwargs):
    return {
        "test_result": "待执行",
        "passed": None,
        **kwargs,
    }


def build_module_cases(detect, tc_counter):
    cases = []
    for mod, meta in MODULE_META.items():
        env_key = ENV_FLAGS[mod]
        enabled = os.environ.get(env_key, "true").lower() == "true"
        result = load_json(os.path.join(RESULTS_DIR, f"{mod}.json"))

        # 判断是否应跳过
        should_skip = False
        skip_reason = ""
        if not enabled:
            should_skip = True
            skip_reason = "模块开关已关闭"
        elif mod == "bandit" and not detect.get("has_python"):
            should_skip = True
            skip_reason = "无 Python 源码"
        elif mod == "super_linter" and not detect.get("has_lintable_code"):
            should_skip = True
            skip_reason = "无可 lint 代码"
        elif mod == "dependency_scan" and not detect.get("has_dependencies"):
            should_skip = True
            skip_reason = "无依赖清单"
        elif detect.get("is_empty") and mod in ("bandit", "super_linter", "dependency_scan"):
            should_skip = True
            skip_reason = "空项目"

        if should_skip:
            expected = f"模块应跳过（{skip_reason}），status=skipped 或未执行"
            assertion = {"type": "module_skip", "module": mod, "enabled": enabled}
        else:
            expected = "模块应正常执行完成，status 为 success 或 failure（检出问题时为 failure），不为 error"
            assertion = {
                "type": "module_executed",
                "module": mod,
                "enabled": enabled,
                "forbid_status": ["error"],
                "valid_status": ["success", "failure", "skipped"],
            }

        tc_counter[0] += 1
        cases.append(pending_case(
            tc_id=tc_id(tc_counter[0]),
            test_function=meta["name"],
            function_description=meta["desc"],
            test_content_description=meta["content"],
            test_steps=meta["steps"],
            expected_result=expected,
            assertion=assertion,
            module=mod,
        ))
    return cases


def build_infra_cases(detect, tc_counter):
    cases = []

    tc_counter[0] += 1
    cases.append(pending_case(
        tc_id=tc_id(tc_counter[0]),
        test_function="语言与结构检测",
        function_description="自动检测项目编程语言、依赖清单和空项目状态",
        test_content_description="执行 detect-languages.sh，生成 detect-languages.json",
        test_steps=[
            "扫描工作目录统计各语言文件数",
            "检测依赖清单是否存在",
            "判断 is_empty / has_python 等标志",
            "写入 detect-languages.json 制品",
        ],
        expected_result="detect-languages.json 存在且包含 has_python、has_lintable_code、is_empty 字段",
        assertion={"type": "file_json_fields", "file": "detect-languages.json",
                   "fields": ["has_python", "has_lintable_code", "is_empty", "file_counts"]},
    ))

    tc_counter[0] += 1
    cases.append(pending_case(
        tc_id=tc_id(tc_counter[0]),
        test_function="审计结果汇总",
        function_description="汇总各扫描模块结果为 audit-summary.json",
        test_content_description="读取各模块 JSON，计算 total_findings 和 audit_status",
        test_steps=[
            "遍历 gitleaks/super_linter/bandit/dependency_scan/custom_rules 结果",
            "统计 passed/failed/skipped 模块列表",
            "计算 audit_status 和 total_findings",
            "写入 audit-summary.json",
        ],
        expected_result="audit-summary.json 存在，audit_status 为 success/failure/skipped，modules 非空或全跳过",
        assertion={"type": "audit_summary"},
    ))

    tc_counter[0] += 1
    cases.append(pending_case(
        tc_id=tc_id(tc_counter[0]),
        test_function="Findings 计数一致性",
        function_description="验证汇总 findings 与各模块 findings 之和一致",
        test_content_description="对比 audit-summary.total_findings 与各模块 findings 累加值",
        test_steps=[
            "读取 audit-summary.json 的 total_findings",
            "累加各模块 findings 字段",
            "对比两者是否相等",
        ],
        expected_result="total_findings 等于各已执行模块 findings 之和",
        assertion={"type": "findings_consistency"},
    ))

    if detect.get("is_empty"):
        tc_counter[0] += 1
        cases.append(pending_case(
            tc_id=tc_id(tc_counter[0]),
            test_function="空项目降级容错",
            function_description="空项目时各扫描模块应优雅跳过，不中断流程",
            test_content_description="工作目录无源码文件时的降级行为验证",
            test_steps=[
                "确认 is_empty=true",
                "检查 bandit/super_linter 等模块 status",
                "确认 audit_status 不为 error",
            ],
            expected_result="空项目下 audit_status 为 skipped 或 success，无 error 级模块失败",
            assertion={"type": "empty_project_graceful"},
        ))

    return cases


def export_markdown(cases, summary_stats):
    md_path = os.path.join(ARTIFACTS_DIR, "test-cases.md")
    lines = [
        "# 代码审计验收测试用例",
        "",
        f"> 生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"> 总计: {summary_stats['total']} | 通过: {summary_stats['passed']} | 失败: {summary_stats['failed']} | 待执行: {summary_stats['pending']}",
        "",
        "| TC-ID | 测试功能 | 功能描述 | 测试内容描述 | 测试步骤 | 预期结果 | 测试结果 | 是否通过 |",
        "|-------|----------|----------|--------------|----------|----------|----------|----------|",
    ]
    for c in cases:
        steps = "<br>".join(f"{i+1}. {s}" for i, s in enumerate(c["test_steps"]))
        passed = c.get("passed")
        if passed is True:
            passed_str = "✅ 是"
        elif passed is False:
            passed_str = "❌ 否"
        else:
            passed_str = "⏳ 待执行"
        lines.append(
            f"| {c['tc_id']} | {c['test_function']} | {c['function_description']} "
            f"| {c['test_content_description']} | {steps} | {c['expected_result']} "
            f"| {c.get('test_result', '待执行')} | {passed_str} |"
        )
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md_path


def export_csv(cases):
    import csv
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
                "测试结果": c.get("test_result", "待执行"),
                "是否通过": "是" if passed is True else ("否" if passed is False else "待执行"),
            })
    return csv_path


def main():
    detect = load_json(os.path.join(ARTIFACTS_DIR, "detect-languages.json"), {})
    tc_counter = [0]

    cases = []
    cases.extend(build_infra_cases(detect, tc_counter))
    cases.extend(build_module_cases(detect, tc_counter))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "work_dir": os.environ.get("WORK_DIR", "."),
        "total_count": len(cases),
        "executed": False,
        "test_cases": cases,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    export_markdown(cases, {"total": len(cases), "passed": 0, "failed": 0, "pending": len(cases)})
    export_csv(cases)

    print(f"已生成 {len(cases)} 条测试用例 -> {OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
