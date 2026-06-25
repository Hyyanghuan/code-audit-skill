#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

log_info "========== 执行验收测试用例 =========="

if [[ "${ENABLE_TEST_CASES:-true}" != "true" ]]; then
  log_info "测试用例执行已关闭，跳过"
  gha_output "test-cases-executed" "false"
  exit 0
fi

if [[ ! -f "${ARTIFACTS_DIR}/test-cases.json" ]]; then
  log_warn "test-cases.json 不存在，跳过执行"
  gha_output "test-cases-executed" "false"
  exit 0
fi

export ARTIFACTS_DIR RESULTS_DIR

set +e
OUTPUT=$(python3 "${SCRIPT_DIR}/execute-test-cases.py" 2>&1 | tee -a "${ARTIFACTS_DIR}/test-cases-execution.log")
EXIT_CODE=${PIPESTATUS[0]}
set -e

TEST_PASSED=$(echo "$OUTPUT" | grep '^TEST_PASSED=' | tail -1 | cut -d= -f2)
TEST_FAILED=$(echo "$OUTPUT" | grep '^TEST_FAILED=' | tail -1 | cut -d= -f2)
TEST_ALL_PASSED=$(echo "$OUTPUT" | grep '^TEST_ALL_PASSED=' | tail -1 | cut -d= -f2)

TEST_PASSED="${TEST_PASSED:-0}"
TEST_FAILED="${TEST_FAILED:-0}"
TEST_ALL_PASSED="${TEST_ALL_PASSED:-unknown}"

gha_output "test-cases-executed" "true"
gha_output "test-cases-passed" "$TEST_PASSED"
gha_output "test-cases-failed" "$TEST_FAILED"
gha_output "test-cases-all-passed" "$TEST_ALL_PASSED"

log_info "测试用例执行完成: 通过=${TEST_PASSED} 失败=${TEST_FAILED}"
exit 0
