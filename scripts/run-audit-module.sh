#!/usr/bin/env bash
# 通用审计模块执行器：AUDIT_MODULE=模块名
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

MODULE="${AUDIT_MODULE:-sast_patterns}"
export AUDIT_MODULE="$MODULE"
export GITHUB_ACTION_PATH="${GITHUB_ACTION_PATH:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

log_info "========== 审计模块: ${MODULE} =========="

set +e
python3 "${SCRIPT_DIR}/audit-engine.py" 2>&1 | tee -a "${ARTIFACTS_DIR}/${MODULE}.log"
EXIT_CODE=${PIPESTATUS[0]}
set -e

[[ "$EXIT_CODE" -eq 1 ]] && exit 1 || exit 0
