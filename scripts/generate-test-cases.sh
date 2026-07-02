#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

log_info "========== 生成验收测试用例 =========="

if [[ "${ENABLE_TEST_CASES:-true}" != "true" ]]; then
  log_info "测试用例生成已关闭，跳过"
  gha_output "test-cases-generated" "false"
  exit 0
fi

export ARTIFACTS_DIR RESULTS_DIR WORK_DIR ABS_WORK_DIR

set +e
python3 "${SCRIPT_DIR}/generate-test-cases.py" 2>&1 | tee -a "${ARTIFACTS_DIR}/test-cases-generate.log"
EXIT_CODE=${PIPESTATUS[0]}
set -e

if [[ "$EXIT_CODE" -eq 0 && -f "${ARTIFACTS_DIR}/test-cases.json" ]]; then
  COUNT=$(python3 -c "import json; print(json.load(open('${ARTIFACTS_DIR}/test-cases.json')).get('total_count',0))" 2>/dev/null || echo "0")
  gha_output "test-cases-generated" "true"
  gha_output "test-cases-count" "$COUNT"
  log_info "已生成 ${COUNT} 条测试用例"
else
  log_warn "测试用例生成失败，已降级跳过"
  gha_output "test-cases-generated" "false"
fi

exit 0
