#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

MODULE="custom_rules"
LOG_FILE="${ARTIFACTS_DIR}/custom-rules.log"
FINDINGS=0
STATUS="success"
MESSAGE="自定义规则检查通过"

log_info "========== 自定义业务规则扫描 =========="

RULES_FILE="${INPUT_CUSTOM_RULES_PATH:-}"
if [[ -z "$RULES_FILE" || ! -f "$RULES_FILE" ]]; then
  RULES_FILE="${GITHUB_ACTION_PATH}/config/custom-rules/business-rules.yaml"
fi

if [[ ! -f "$RULES_FILE" ]]; then
  MESSAGE="未找到自定义规则文件，跳过"
  write_module_result "$MODULE" "skipped" 0 "$MESSAGE" "$LOG_FILE"
  exit 0
fi

log_info "使用规则文件: ${RULES_FILE}"

CUSTOM_RESULTS="${ARTIFACTS_DIR}/custom-rules-report.json"
export RULES_FILE ABS_WORK_DIR CUSTOM_RESULTS

set +e
python3 <<'PYEOF' 2>&1 | tee -a "$LOG_FILE"
import json, re, os, sys, fnmatch, subprocess

rules_file = os.environ["RULES_FILE"]
work_dir = os.environ["ABS_WORK_DIR"]
results_file = os.environ.get("CUSTOM_RESULTS", "")

findings = []
try:
    import yaml
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml"])
    import yaml

with open(rules_file) as f:
    data = yaml.safe_load(f)

rules = data.get("rules", []) if isinstance(data, dict) else []
skip_dirs = {"node_modules", "vendor", ".venv", "venv", "dist", "build", "target",
             "__pycache__", ".git", "coverage", ".tox", "site-packages", "test-fixtures"}

def should_skip(path):
    return any(p in path.replace("\\", "/").split("/") for p in skip_dirs)

def match_glob(rel, globs):
    if globs == ["**/*"]:
        return True
    for g in globs:
        g_clean = g.replace("**/", "")
        if fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(rel, g_clean):
            return True
        if fnmatch.fnmatch(os.path.basename(rel), g.split("/")[-1]):
            return True
    return False

for rule in rules:
    rid = rule.get("id", "unknown")
    pattern = rule.get("pattern", "")
    severity = rule.get("severity", "medium")
    message = rule.get("message", "")
    path_globs = rule.get("paths", ["**/*"])
    if not pattern:
        continue
    try:
        regex = re.compile(pattern)
    except re.error as e:
        print(f"[WARN] 规则 {rid} 正则无效: {e}")
        continue
    for root, dirs, files in os.walk(work_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, work_dir)
            if should_skip(rel):
                continue
            if not match_glob(rel, path_globs):
                continue
            try:
                with open(fpath, errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if regex.search(line):
                            findings.append({
                                "rule_id": rid,
                                "severity": severity,
                                "file": rel,
                                "line": i,
                                "message": message,
                                "snippet": line.strip()[:120]
                            })
            except (OSError, UnicodeDecodeError):
                pass

high = sum(1 for f in findings if f["severity"] in ("high", "critical"))
with open(results_file, "w") as f:
    json.dump({"findings": findings, "high": high, "total": len(findings)}, f, indent=2)

print(f"自定义规则扫描完成: total={len(findings)} high={high}")
sys.exit(1 if high > 0 else 0)
PYEOF
EXIT_CODE=${PIPESTATUS[0]}
set -e

if [[ -f "$CUSTOM_RESULTS" ]]; then
  FINDINGS=$(python3 -c "import json; d=json.load(open('${CUSTOM_RESULTS}')); print(d.get('high',0))" 2>/dev/null || echo "0")
fi

if [[ "$EXIT_CODE" -eq 0 ]]; then
  STATUS="success"
  MESSAGE="自定义规则检查通过"
elif [[ "$EXIT_CODE" -eq 1 ]]; then
  STATUS="failure"
  MESSAGE="发现 ${FINDINGS} 处高危自定义规则违规"
else
  STATUS="error"
  MESSAGE="自定义规则扫描异常，已降级"
fi

write_module_result "$MODULE" "$STATUS" "$FINDINGS" "$MESSAGE" "$LOG_FILE"
[[ "$STATUS" == "failure" ]] && exit 1 || exit 0
