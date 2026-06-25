#!/usr/bin/env python3
"""
全覆盖审计引擎：SAST 词法/污点/控制流、配置审计、专项安全、差分审计、
覆盖率解析、运行时建议、人工审计清单。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "/tmp/artifacts")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/tmp/results")
ABS_WORK_DIR = os.environ.get("ABS_WORK_DIR", ".")
GITHUB_ACTION_PATH = os.environ.get("GITHUB_ACTION_PATH", "")
MODULE = os.environ.get("AUDIT_MODULE", "sast_patterns")

SKIP_DIRS = {"node_modules", "vendor", ".venv", "venv", "dist", "build", "target",
             "__pycache__", ".git", "coverage", ".tox", "site-packages", "test-fixtures"}


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml"])
        import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def should_skip(rel):
    return any(p in rel.replace("\\", "/").split("/") for p in SKIP_DIRS)


def iter_files(globs):
    base = Path(ABS_WORK_DIR)
    seen = set()
    for g in globs:
        for p in base.rglob(g.replace("**/", "")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(base))
            if should_skip(rel) or rel in seen:
                continue
            seen.add(rel)
            yield rel, p


def scan_patterns(rules, globs, rule_key="pattern"):
    findings = []
    for rel, path in iter_files(globs):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for rule in rules:
            pat = rule.get(rule_key) or rule.get("pattern", "")
            if not pat:
                continue
            try:
                rx = re.compile(pat)
            except re.error:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    findings.append({
                        "file": rel, "line": i,
                        "severity": rule.get("severity", "medium"),
                        "category": rule.get("category", "general"),
                        "message": rule.get("message", pat),
                        "snippet": line.strip()[:150],
                    })
    return findings


def taint_analysis(cfg):
    sources = cfg.get("taint_sources", [])
    sinks = cfg.get("taint_sinks", [])
    src_pats = [(re.compile(s["pattern"]), s) for s in sources if s.get("pattern")]
    sink_pats = [(re.compile(s["pattern"]), s) for s in sinks if s.get("pattern")]
    globs = cfg.get("file_globs", {}).get("source", ["**/*.py"])
    findings = []
    for rel, path in iter_files(globs):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        tainted_vars = set()
        for i, line in enumerate(lines, 1):
            for rx, _ in src_pats:
                if rx.search(line):
                    for m in re.finditer(r"=\s*(\w+)", line):
                        tainted_vars.add(m.group(1))
                    findings.append({
                        "file": rel, "line": i, "severity": "info",
                        "category": "taint_source",
                        "message": f"污点源: 外部可控输入",
                        "snippet": line.strip()[:120],
                    })
            for rx, sink in sink_pats:
                if rx.search(line):
                    if tainted_vars or any(s in line for s in ("request", "input", "argv", "$_")):
                        findings.append({
                            "file": rel, "line": i,
                            "severity": "high",
                            "category": sink.get("category", "taint_sink"),
                            "message": f"污点到达 Sink: {sink.get('category', 'danger')}",
                            "snippet": line.strip()[:120],
                        })
    return findings


def git_diff_files():
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            cwd=ABS_WORK_DIR, stderr=subprocess.DEVNULL, text=True
        )
        return [f.strip() for f in out.splitlines() if f.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "origin/HEAD...HEAD"],
                cwd=ABS_WORK_DIR, stderr=subprocess.DEVNULL, text=True
            )
            return [f.strip() for f in out.splitlines() if f.strip()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []


def diff_audit(cfg):
    changed = git_diff_files()
    if not changed:
        return [], "无 git 变更文件或无法获取 diff"
    dangerous = scan_patterns(
        cfg.get("dangerous_functions", []) + cfg.get("specialized_patterns", []),
        ["**/*"],
    )
    diff_findings = [f for f in dangerous if f["file"] in changed]
    return diff_findings, f"差分审计 {len(changed)} 个变更文件，检出 {len(diff_findings)} 处"


def parse_coverage():
    findings = []
    base = Path(ABS_WORK_DIR)
    for cov_file in base.rglob("coverage.xml"):
        if should_skip(str(cov_file.relative_to(base))):
            continue
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(cov_file)
            root = tree.getroot()
            line_rate = float(root.attrib.get("line-rate", 0))
            if line_rate < 0.6:
                findings.append({
                    "file": str(cov_file.relative_to(base)), "line": 0,
                    "severity": "medium", "category": "coverage",
                    "message": f"行覆盖率偏低: {line_rate:.1%}，建议人工复核未覆盖代码",
                    "snippet": "",
                })
        except Exception:
            pass
    if not findings:
        for lcov in base.rglob("lcov.info"):
            if should_skip(str(lcov.relative_to(base))):
                continue
            findings.append({
                "file": str(lcov.relative_to(base)), "line": 0,
                "severity": "info", "category": "coverage",
                "message": "发现 lcov 覆盖率报告，建议结合未覆盖行人工审计",
                "snippet": "",
            })
            break
    return findings


def generate_manual_checklist(findings_summary=None):
    summary_file = os.path.join(ARTIFACTS_DIR, "audit-summary.json")
    if findings_summary is None and os.path.isfile(summary_file):
        try:
            with open(summary_file, encoding="utf-8") as f:
                s = json.load(f)
            findings_summary = (
                f"audit_status={s.get('audit_status')} "
                f"findings={s.get('total_findings')} "
                f"modules={len(s.get('modules', {}))}"
            )
        except Exception:
            findings_summary = "见 audit-summary.json"
    findings_summary = findings_summary or "见 audit-summary.json"
    md = os.path.join(ARTIFACTS_DIR, "manual-audit-checklist.md")
    sections = [
        ("逐模块通读审计", ["登录鉴权模块", "支付/资金模块", "文件上传下载", "权限控制", "定时任务", "核心接口逻辑"]),
        ("关键函数专项", ["数据库操作函数", "文件读写函数", "系统命令执行", "加密解密函数", "鉴权校验函数"]),
        ("逻辑漏洞审计", ["垂直/水平越权", "金额篡改", "重复下单", "优惠券叠加", "验证码绕过", "流程中断一致性"]),
        ("加密与密钥审计", ["弱加密算法", "密钥硬编码", "密钥轮换机制", "明文存储敏感数据", "不安全随机数"]),
        ("日志与脱敏审计", ["手机号/身份证/银行卡明文日志", "异常堆栈泄露敏感字段", "日志级别与留存策略"]),
    ]
    lines = [
        "# 人工深度审计清单",
        "",
        f"> 生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"> 自动扫描摘要: {findings_summary}",
        "",
        "请在自动扫描基础上，由审计人员逐项勾选完成。",
        "",
    ]
    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        for item in items:
            lines.append(f"- [ ] {item}")
        lines.append("")
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md


def runtime_advisory():
    """DAST/IAST 在 CI 中生成运行时审计建议报告。"""
    findings = []
    base = Path(ABS_WORK_DIR)
    advisories = []
    if list(base.rglob("docker-compose*.yml")) or list(base.rglob("Dockerfile*")):
        advisories.append("检测到容器部署配置，建议接入 IAST 探针或 ZAP 动态扫描")
    if list(base.rglob("**/test_*.py")) or list(base.rglob("**/*_test.go")):
        advisories.append("存在单元测试，建议采集覆盖率并结合 DAST 覆盖接口分支")
    if list(base.rglob("**/routes/**")) or list(base.rglob("**/controllers/**")):
        advisories.append("检测到路由/控制器，建议用接口流量联动审计所有 API 分支")
    for i, adv in enumerate(advisories):
        findings.append({
            "file": "runtime-advisory", "line": i + 1,
            "severity": "info", "category": "dast_iast",
            "message": adv, "snippet": "",
        })
    if not advisories:
        findings.append({
            "file": "runtime-advisory", "line": 1,
            "severity": "info", "category": "dast_iast",
            "message": "建议在预发环境部署 IAST/DAST 工具补全运行时盲区",
            "snippet": "",
        })
    report = os.path.join(ARTIFACTS_DIR, "runtime-audit-advisory.json")
    with open(report, "w", encoding="utf-8") as f:
        json.dump({"advisories": advisories, "findings": findings}, f, indent=2, ensure_ascii=False)
    return findings


def write_module_result(module, status, findings, message, log_file=""):
    high = sum(1 for f in findings if f.get("severity") in ("high", "critical"))
    report = {
        "module": module,
        "status": status,
        "findings": high,
        "total_issues": len(findings),
        "message": message,
        "items": findings[:200],
        "log_file": log_file,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, f"{module}.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(os.path.join(ARTIFACTS_DIR, f"{module}-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return high


def run_module(module):
    cfg_path = os.path.join(GITHUB_ACTION_PATH, "config", "sast-patterns.yaml")
    cfg = load_yaml(cfg_path) if os.path.isfile(cfg_path) else {}
    log_file = os.path.join(ARTIFACTS_DIR, f"{module}.log")
    findings = []
    message = ""

    if module == "sast_patterns":
        globs = cfg.get("file_globs", {}).get("source", ["**/*.py"])
        findings = scan_patterns(cfg.get("dangerous_functions", []), globs)
        message = f"词法/语法扫描完成，发现 {len(findings)} 处"

    elif module == "taint_analysis":
        findings = taint_analysis(cfg)
        message = f"污点分析完成，发现 {len(findings)} 处"

    elif module == "control_flow":
        globs = cfg.get("file_globs", {}).get("source", ["**/*.py"])
        findings = scan_patterns(cfg.get("control_flow_patterns", []), globs)
        message = f"控制流分析完成，发现 {len(findings)} 处"

    elif module == "config_audit":
        globs = cfg.get("file_globs", {}).get("config", ["**/*.yml", "**/Dockerfile*"])
        findings = scan_patterns(cfg.get("config_patterns", []), globs)
        message = f"配置文件审计完成，发现 {len(findings)} 处"

    elif module == "specialized_security":
        globs = cfg.get("file_globs", {}).get("source", []) + cfg.get("file_globs", {}).get("config", [])
        findings = scan_patterns(cfg.get("specialized_patterns", []), globs)
        message = f"专项安全审计完成，发现 {len(findings)} 处"

    elif module == "diff_audit":
        findings, message = diff_audit(cfg)

    elif module == "coverage_audit":
        findings = parse_coverage()
        message = f"覆盖率审计完成，发现 {len(findings)} 项建议"

    elif module == "runtime_audit":
        findings = runtime_advisory()
        message = f"运行时/DAST/IAST 建议生成，共 {len(findings)} 条"

    elif module == "manual_checklist":
        generate_manual_checklist("待汇总")
        findings = []
        message = "人工审计清单已生成 manual-audit-checklist.md"

    else:
        message = f"未知模块 {module}"
        write_module_result(module, "error", [], message)
        return 1

    high = sum(1 for f in findings if f.get("severity") in ("high", "critical"))
    status = "failure" if high > 0 else "success"
    write_module_result(module, status, findings, message, log_file)
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(message + "\n")
        json.dump(findings[:50], f, indent=2, ensure_ascii=False)

    print(message)
    return 1 if high_count(findings) > 0 else 0


def high_count(findings):
    return sum(1 for f in findings if f.get("severity") in ("high", "critical"))


if __name__ == "__main__":
    sys.exit(run_module(MODULE))
