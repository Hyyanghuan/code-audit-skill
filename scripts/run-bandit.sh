#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

MODULE="bandit"
LOG_FILE="${ARTIFACTS_DIR}/bandit.log"
FINDINGS=0
STATUS="skipped"
MESSAGE=""

log_info "========== Bandit Python 安全扫描 =========="

# 无 Python 代码自动跳过
PY_FILES=$(find "${ABS_WORK_DIR}" -type f -name '*.py' \
  -not -path '*/node_modules/*' \
  -not -path '*/.venv/*' \
  -not -path '*/venv/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/dist/*' \
  -not -path '*/build/*' \
  -not -path '*/site-packages/*' \
  -not -path '*/test-fixtures/*' \
  2>/dev/null | wc -l | tr -d ' ')

if [[ "$PY_FILES" -eq 0 ]]; then
  MESSAGE="未发现 Python 源码，跳过 bandit"
  write_module_result "$MODULE" "skipped" 0 "$MESSAGE" "$LOG_FILE"
  exit 0
fi

# 安装 bandit
pip install --quiet bandit==1.7.10 2>>"$LOG_FILE" || {
  MESSAGE="bandit 安装失败，已降级跳过"
  write_module_result "$MODULE" "error" 0 "$MESSAGE" "$LOG_FILE"
  exit 0
}

REPORT_JSON="${ARTIFACTS_DIR}/bandit-report.json"

set +e
bandit -r "${ABS_WORK_DIR}" \
  -f json \
  -o "${REPORT_JSON}" \
  --exclude '*/tests/*,*/test/*,*/.venv/*,*/venv/*,*/node_modules/*,*/dist/*,*/build/*,*/__pycache__/*,*/site-packages/*,*/test-fixtures/*' \
  -ll \
  2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

if [[ -f "$REPORT_JSON" ]]; then
  FINDINGS=$(python3 -c "
import json
with open('${REPORT_JSON}') as f:
    d = json.load(f)
print(d.get('metrics', {}).get('_totals', {}).get('SEVERITY.HIGH', 0) +
      d.get('metrics', {}).get('_totals', {}).get('SEVERITY.MEDIUM', 0))
" 2>/dev/null || echo "0")
fi

if [[ "$EXIT_CODE" -eq 0 ]]; then
  STATUS="success"
  MESSAGE="Python 安全扫描通过"
elif [[ "$EXIT_CODE" -eq 1 ]]; then
  STATUS="failure"
  MESSAGE="发现 ${FINDINGS} 处 Python 安全问题"
else
  STATUS="error"
  MESSAGE="bandit 执行异常 (exit=${EXIT_CODE})，已降级"
fi

write_module_result "$MODULE" "$STATUS" "$FINDINGS" "$MESSAGE" "$LOG_FILE"
[[ "$STATUS" == "failure" ]] && exit 1 || exit 0
