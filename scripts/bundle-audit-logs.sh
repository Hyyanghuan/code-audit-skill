#!/usr/bin/env bash
# 合并所有审计运行日志为单个文件，供 Telegram 发送
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

ARTIFACTS_DIR="${ARTIFACTS_DIR:-${RUNNER_TEMP}/code-audit-${GITHUB_RUN_ID}/artifacts}"
OUTPUT="${ARTIFACTS_DIR}/audit-logs-combined.txt"
MAX_KB="${TG_MAX_LOG_SIZE_KB:-1024}"

log_info "========== 合并审计运行日志 =========="

{
  echo "========================================"
  echo " Code Audit Skill - 运行日志汇总"
  echo " 生成时间: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
  echo " 仓库: ${GITHUB_REPOSITORY:-unknown}"
  echo " Run ID: ${GITHUB_RUN_ID:-unknown}"
  echo "========================================"
  echo ""

  for f in audit-meta.json detect-languages.json audit-summary.json \
           test-cases-report.json audit-bugs.json telegram-diagnostic.json; do
    if [[ -f "${ARTIFACTS_DIR}/${f}" ]]; then
      echo "########## ${f} ##########"
      cat "${ARTIFACTS_DIR}/${f}"
      echo ""
    fi
  done

  for f in "${ARTIFACTS_DIR}"/*.log; do
    [[ -f "$f" ]] || continue
    echo "########## $(basename "$f") ##########"
    cat "$f"
    echo ""
  done

  RESULTS_DIR="${RESULTS_DIR:-${ARTIFACTS_DIR}/../results}"
  if [[ -d "$RESULTS_DIR" ]]; then
    for f in "${RESULTS_DIR}"/*.json; do
      [[ -f "$f" ]] || continue
      echo "########## results/$(basename "$f") ##########"
      cat "$f"
      echo ""
    done
  fi
} > "$OUTPUT" 2>/dev/null || true

# 截断过大文件
SIZE_KB=$(du -k "$OUTPUT" 2>/dev/null | cut -f1)
if [[ "${SIZE_KB:-0}" -gt "$MAX_KB" ]]; then
  log_warn "日志文件 ${SIZE_KB}KB 超过限制 ${MAX_KB}KB，截断保留尾部"
  tail -c "$((MAX_KB * 1024))" "$OUTPUT" > "${OUTPUT}.tmp"
  {
    echo "...(日志已截断，仅保留最后 ${MAX_KB}KB)..."
    cat "${OUTPUT}.tmp"
  } > "$OUTPUT"
  rm -f "${OUTPUT}.tmp"
fi

log_info "合并日志: ${OUTPUT} ($(wc -c < "$OUTPUT" 2>/dev/null || echo 0) bytes)"
echo "$OUTPUT"
