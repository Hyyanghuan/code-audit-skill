#!/usr/bin/env python3
"""从 audit-summary 与各模块报告生成 SARIF 2.1.0（GitHub Code Scanning 兼容）。"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "/tmp/artifacts")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/tmp/results")
OUTPUT = os.path.join(ARTIFACTS_DIR, "codeaudit.sarif.json")

SEVERITY_MAP = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}


def load_json(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rule_id(module, item, idx):
    cat = item.get("category", "general")
    return f"{module}/{cat}/{idx}"


def main():
    summary = load_json(os.path.join(ARTIFACTS_DIR, "audit-summary.json")) or {}
    repo = os.environ.get("GITHUB_REPOSITORY", "unknown/unknown")
    sha = os.environ.get("GITHUB_SHA", "unknown")
    ref = os.environ.get("GITHUB_REF", "refs/heads/main")

    runs = []
    rules = {}
    results = []

    modules = summary.get("modules") or {}
    for mod, data in modules.items():
        items = data.get("items") or []
        for i, item in enumerate(items[:100], 1):
            sev = SEVERITY_MAP.get(str(item.get("severity", "medium")).lower(), "warning")
            rid = rule_id(mod, item, i)
            if rid not in rules:
                rules[rid] = {
                    "id": rid,
                    "name": item.get("category", mod),
                    "shortDescription": {"text": item.get("message", mod)[:200]},
                    "fullDescription": {"text": data.get("message", mod)},
                    "defaultConfiguration": {"level": sev},
                }
            loc = {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": item.get("file", "unknown"),
                        "uriBaseId": "ROOTPATH",
                    },
                    "region": {"startLine": max(1, int(item.get("line", 1)))},
                }
            }
            results.append({
                "ruleId": rid,
                "level": sev,
                "message": {"text": item.get("message", "finding")},
                "locations": [loc],
                "partialFingerprints": {
                    "primaryLocationLineHash": f"{mod}:{item.get('file')}:{item.get('line')}:{item.get('message', '')[:40]}"
                },
            })

    tool_driver = {
        "name": "Code Audit Skill",
        "version": open(os.path.join(os.environ.get("GITHUB_ACTION_PATH", "."), "VERSION"), encoding="utf-8").read().strip()
        if os.path.isfile(os.path.join(os.environ.get("GITHUB_ACTION_PATH", "."), "VERSION"))
        else "1.0.0",
        "informationUri": "https://github.com",
        "rules": list(rules.values()),
    }

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": tool_driver},
            "results": results,
            "automationDetails": {
                "description": {"text": f"Code Audit Skill scan for {repo}"},
                "id": f"code-audit/{sha[:12]}",
            },
            "properties": {
                "repository": repo,
                "ref": ref,
                "sha": sha,
                "audit_status": summary.get("audit_status", "unknown"),
            },
        }],
    }

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(sarif, f, indent=2, ensure_ascii=False)
    print(OUTPUT)
    print(f"SARIF results: {len(results)}")


if __name__ == "__main__":
    main()
