#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

log_info "========== 汇总审计结果 =========="

MODULES=(gitleaks super_linter bandit dependency_scan custom_rules)
TOTAL_FINDINGS=0
FAILED_MODULES=()
SKIPPED_MODULES=()
PASSED_MODULES=()
ERROR_MODULES=()

for mod in "${MODULES[@]}"; do
  result_file="${RESULTS_DIR}/${mod}.json"
  if [[ ! -f "$result_file" ]]; then
    SKIPPED_MODULES+=("$mod")
    write_module_result "$mod" "skipped" 0 "模块未执行（可能已关闭或无匹配代码）" ""
    continue
  fi

  status=$(python3 -c "import json; print(json.load(open('${result_file}')).get('status','unknown'))" 2>/dev/null || echo "unknown")
  findings=$(python3 -c "import json; print(json.load(open('${result_file}')).get('findings',0))" 2>/dev/null || echo "0")

  TOTAL_FINDINGS=$((TOTAL_FINDINGS + findings))

  case "$status" in
    success) PASSED_MODULES+=("$mod") ;;
    failure) FAILED_MODULES+=("$mod") ;;
    skipped) SKIPPED_MODULES+=("$mod") ;;
    error)   ERROR_MODULES+=("$mod") ;;
  esac
done

# 总体状态判定
AUDIT_STATUS="success"
if [[ ${#FAILED_MODULES[@]} -gt 0 ]]; then
  AUDIT_STATUS="failure"
elif [[ ${#PASSED_MODULES[@]} -eq 0 && ${#SKIPPED_MODULES[@]} -gt 0 ]]; then
  AUDIT_STATUS="skipped"
fi

python3 <<PYEOF
import json, glob, os

results_dir = "${RESULTS_DIR}"
artifacts_dir = "${ARTIFACTS_DIR}"
modules = ["gitleaks", "super_linter", "bandit", "dependency_scan", "custom_rules"]

summary = {
    "audit_status": "${AUDIT_STATUS}",
    "total_findings": ${TOTAL_FINDINGS},
    "modules": {},
    "passed": [],
    "failed": [],
    "skipped": [],
    "errors": [],
    "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "repository": "${GITHUB_REPOSITORY:-}",
    "ref": "${GITHUB_REF:-}",
    "sha": "${GITHUB_SHA:-}",
    "run_url": "${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-}/actions/runs/${GITHUB_RUN_ID:-}"
}

for mod in modules:
    path = os.path.join(results_dir, f"{mod}.json")
    if os.path.isfile(path):
        with open(path) as f:
            data = json.load(f)
        summary["modules"][mod] = data
        st = data.get("status", "unknown")
        if st == "success": summary["passed"].append(mod)
        elif st == "failure": summary["failed"].append(mod)
        elif st == "skipped": summary["skipped"].append(mod)
        else: summary["errors"].append(mod)

summary["audit_status"] = "failure" if summary["failed"] else ("skipped" if not summary["passed"] and summary["skipped"] else "success")
summary["total_findings"] = sum(m.get("findings", 0) for m in summary["modules"].values())

with open(os.path.join(artifacts_dir, "audit-summary.json"), "w") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
PYEOF

# 从 Python 输出更新状态
while IFS='=' read -r key val; do
  case "$key" in
    AUDIT_STATUS) AUDIT_STATUS="$val" ;;
    TOTAL_FINDINGS) TOTAL_FINDINGS="$val" ;;
  esac
done < <(python3 -c "
import json, os
p = os.path.join('${ARTIFACTS_DIR}', 'audit-summary.json')
with open(p) as f: s = json.load(f)
print(f\"AUDIT_STATUS={s['audit_status']}\")
print(f\"TOTAL_FINDINGS={s.get('total_findings', 0)}\")
" 2>/dev/null)

gha_output "audit-status" "$AUDIT_STATUS"
gha_output "findings-count" "$TOTAL_FINDINGS"
gha_output "results-json" "${ARTIFACTS_DIR}/audit-summary.json"

log_info "审计完成: status=${AUDIT_STATUS} findings=${TOTAL_FINDINGS}"
log_info "通过: ${PASSED_MODULES[*]:-无} | 失败: ${FAILED_MODULES[*]:-无} | 跳过: ${SKIPPED_MODULES[*]:-无}"
