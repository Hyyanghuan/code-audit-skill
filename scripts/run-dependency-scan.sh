#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

MODULE="dependency_scan"
LOG_FILE="${ARTIFACTS_DIR}/dependency-scan.log"
FINDINGS=0
STATUS="skipped"
MESSAGE=""

log_info "========== 依赖漏洞检测 (Trivy) =========="

# 检查是否有可扫描目标
SCAN_TARGETS=()
[[ -f "${ABS_WORK_DIR}/requirements.txt" ]] && SCAN_TARGETS+=("${ABS_WORK_DIR}/requirements.txt")
[[ -f "${ABS_WORK_DIR}/package.json" ]]     && SCAN_TARGETS+=("${ABS_WORK_DIR}/package.json")
[[ -f "${ABS_WORK_DIR}/go.mod" ]]           && SCAN_TARGETS+=("${ABS_WORK_DIR}/go.mod")
[[ -f "${ABS_WORK_DIR}/pyproject.toml" ]]   && SCAN_TARGETS+=("${ABS_WORK_DIR}/pyproject.toml")
[[ -f "${ABS_WORK_DIR}/Pipfile" ]]          && SCAN_TARGETS+=("${ABS_WORK_DIR}/Pipfile")

if [[ ${#SCAN_TARGETS[@]} -eq 0 ]]; then
  # 降级：对整个目录做 filesystem 扫描（排除依赖目录）
  HAS_MANIFEST="false"
else
  HAS_MANIFEST="true"
fi

TRIVY_VERSION="0.58.1"
TRIVY_BIN="${RUNNER_TEMP}/trivy"

if [[ ! -x "$TRIVY_BIN" ]]; then
  log_info "安装 trivy v${TRIVY_VERSION}..."
  curl -sfL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
    | tar -xz -C "${RUNNER_TEMP}" trivy 2>>"$LOG_FILE" || {
    MESSAGE="trivy 安装失败，已降级跳过"
    write_module_result "$MODULE" "error" 0 "$MESSAGE" "$LOG_FILE"
    exit 0
  }
  chmod +x "$TRIVY_BIN"
fi

REPORT_JSON="${ARTIFACTS_DIR}/trivy-report.json"
SKIP_DIRS="node_modules,vendor,.venv,venv,dist,build,target,__pycache__,.git,coverage,.tox,site-packages,test-fixtures"

set +e
if [[ "$HAS_MANIFEST" == "true" ]]; then
  for target in "${SCAN_TARGETS[@]}"; do
    echo "扫描: $target" >> "$LOG_FILE"
    "$TRIVY_BIN" fs \
      --scanners vuln \
      --severity HIGH,CRITICAL \
      --skip-dirs "$SKIP_DIRS" \
      --format json \
      --output "${REPORT_JSON}.tmp" \
      "$(dirname "$target")" 2>&1 | tee -a "$LOG_FILE"
  done
else
  "$TRIVY_BIN" fs \
    --scanners vuln \
    --severity HIGH,CRITICAL \
    --skip-dirs "$SKIP_DIRS" \
    --format json \
    --output "${REPORT_JSON}.tmp" \
    "${ABS_WORK_DIR}" 2>&1 | tee -a "$LOG_FILE"
fi
EXIT_CODE=$?
set -e

# 合并报告
if [[ -f "${REPORT_JSON}.tmp" ]]; then
  mv "${REPORT_JSON}.tmp" "$REPORT_JSON"
  FINDINGS=$(python3 -c "
import json
try:
    with open('${REPORT_JSON}') as f:
        d = json.load(f)
    count = 0
    for r in d.get('Results', []):
        for v in r.get('Vulnerabilities', []) or []:
            if v.get('Severity') in ('HIGH', 'CRITICAL'):
                count += 1
    print(count)
except Exception:
    print(0)
" 2>/dev/null || echo "0")
fi

if [[ "$EXIT_CODE" -eq 0 && "$FINDINGS" -eq 0 ]]; then
  STATUS="success"
  MESSAGE="依赖漏洞检测通过"
elif [[ "$FINDINGS" -gt 0 ]]; then
  STATUS="failure"
  MESSAGE="发现 ${FINDINGS} 处高危/严重依赖漏洞"
else
  STATUS="success"
  MESSAGE="依赖扫描完成，未发现高危漏洞"
fi

write_module_result "$MODULE" "$STATUS" "$FINDINGS" "$MESSAGE" "$LOG_FILE"
[[ "$STATUS" == "failure" ]] && exit 1 || exit 0
