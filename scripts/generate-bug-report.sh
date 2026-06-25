#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

log_info "========== 生成 Bug 报告 =========="

export ARTIFACTS_DIR RESULTS_DIR

python3 "${SCRIPT_DIR}/generate-bug-report.py" 2>&1 | tee -a "${ARTIFACTS_DIR}/bug-report-generate.log"

BUG_COUNT=$(grep '^BUG_COUNT=' "${ARTIFACTS_DIR}/bug-report-generate.log" 2>/dev/null | tail -1 | cut -d= -f2)
BUG_COUNT="${BUG_COUNT:-0}"

gha_output "bug-count" "$BUG_COUNT"
gha_output "bug-report-md" "${ARTIFACTS_DIR}/audit-bugs.md"

log_info "Bug 报告生成完成: ${BUG_COUNT} 个"
exit 0
