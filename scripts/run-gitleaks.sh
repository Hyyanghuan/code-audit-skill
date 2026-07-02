#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

MODULE="gitleaks"
LOG_FILE="${ARTIFACTS_DIR}/gitleaks.log"
FINDINGS=0
STATUS="success"
MESSAGE="未发现敏感密钥"

log_info "========== Gitleaks 敏感密钥扫描 =========="

IGNORE_FILE="${AUDIT_DIR}/gitleaks-ignore.txt"
generate_ignore_file "$IGNORE_FILE"

# 确定配置文件
GITLEAKS_CFG="${INPUT_GITLEAKS_CONFIG:-}"
if [[ -z "$GITLEAKS_CFG" || ! -f "$GITLEAKS_CFG" ]]; then
  GITLEAKS_CFG="${GITHUB_ACTION_PATH}/config/gitleaks.toml"
fi

# 安装 gitleaks（固定版本）
GITLEAKS_VERSION="8.21.2"
if ! command -v gitleaks &>/dev/null; then
  log_info "安装 gitleaks v${GITLEAKS_VERSION}..."
  curl -sSL --http1.1 --retry 2 --retry-delay 3 \
    "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
    | tar -xz -C /tmp 2>>"$LOG_FILE" || {
    STATUS="error"
    MESSAGE="gitleaks 安装失败，已跳过"
    write_module_result "$MODULE" "$STATUS" 0 "$MESSAGE" "$LOG_FILE"
    exit 0
  }
  chmod +x /tmp/gitleaks
  export PATH="/tmp:$PATH"
fi

REPORT_JSON="${ARTIFACTS_DIR}/gitleaks-report.json"

set +e
gitleaks detect \
  --source="${ABS_WORK_DIR}" \
  --config="${GITLEAKS_CFG}" \
  --report-path="${REPORT_JSON}" \
  --report-format=json \
  --no-git \
  --verbose \
  --redact \
  2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

if [[ "$EXIT_CODE" -eq 0 ]]; then
  STATUS="success"
  MESSAGE="未发现敏感密钥"
  FINDINGS=0
elif [[ "$EXIT_CODE" -eq 1 ]]; then
  STATUS="failure"
  if [[ -f "$REPORT_JSON" ]]; then
    FINDINGS=$(python3 -c "import json; d=json.load(open('${REPORT_JSON}')); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo "1")
  else
    FINDINGS=1
  fi
  MESSAGE="发现 ${FINDINGS} 处潜在密钥泄露"
  log_error "$MESSAGE"
else
  STATUS="error"
  MESSAGE="gitleaks 执行异常 (exit=${EXIT_CODE})，已降级跳过"
  log_warn "$MESSAGE"
fi

write_module_result "$MODULE" "$STATUS" "$FINDINGS" "$MESSAGE" "$LOG_FILE"
[[ "$STATUS" == "failure" ]] && exit 1 || exit 0
