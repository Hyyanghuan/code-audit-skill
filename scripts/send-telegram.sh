#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

if [[ -z "${ARTIFACTS_DIR:-}" ]]; then
  ARTIFACTS_DIR="${RUNNER_TEMP:-/tmp}/code-audit-${GITHUB_RUN_ID:-}/artifacts"
  mkdir -p "$ARTIFACTS_DIR"
fi

LOG_FILE="${ARTIFACTS_DIR}/telegram.log"
DIAG_FILE="${ARTIFACTS_DIR}/telegram-diagnostic.json"

log_info "========== Telegram 汇总通知（审计 + 测试用例 MD + 运行日志）=========="

# 加载硬编码配置 config/telegram.yaml（workflow input 可覆盖）
# shellcheck source=load-telegram-config.sh
source "${SCRIPT_DIR}/load-telegram-config.sh"

TOKEN="${INPUT_TELEGRAM_BOT_TOKEN:-${TG_BOT_TOKEN:-}}"
CHAT_ID="${INPUT_TELEGRAM_CHAT_ID:-${TG_CHAT_ID:-}}"
BOT_USER="${INPUT_TELEGRAM_BOT_USERNAME:-${TG_BOT_USERNAME:-}}"
SEND_SUMMARY="${TG_SEND_SUMMARY:-true}"
SEND_MD="${TG_SEND_TEST_CASES_MD:-true}"
SEND_BUG="${TG_SEND_BUG_REPORT:-true}"
SEND_LOGS="${TG_SEND_AUDIT_LOGS:-true}"

log_info "TG 配置来源: ${TG_CONFIG_SOURCE:-unknown}"
log_info "TG chat_id=${CHAT_ID:-空} bot=${BOT_USER:-未设置} send_md=${SEND_MD} send_bug=${SEND_BUG} send_logs=${SEND_LOGS}"

# 生成 Bug 报告（若前置步骤未执行）
BUG_MD="${ARTIFACTS_DIR}/audit-bugs.md"
if [[ ! -f "$BUG_MD" ]]; then
  bash "${SCRIPT_DIR}/generate-bug-report.sh" 2>/dev/null || true
fi

write_diag() {
  local status="$1" detail="$2" http="${3:-}"
  python3 -c "
import json, os
from datetime import datetime, timezone
d = {
  'status': '${status}',
  'detail': '''${detail}''',
  'http_code': '${http}',
  'chat_id': '${CHAT_ID:-}',
  'config_source': '${TG_CONFIG_SOURCE:-}',
  'timestamp': datetime.now(timezone.utc).isoformat()
}
with open('${DIAG_FILE}', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
"
}

if [[ -z "$TOKEN" || -z "$CHAT_ID" ]]; then
  MSG="Telegram token/chat_id 为空，请检查 config/telegram.yaml"
  log_warn "$MSG"
  echo "::warning title=Telegram 未配置::${MSG}"
  write_diag "skipped" "$MSG"
  exit 0
fi

# 合并运行日志
COMBINED_LOG="${ARTIFACTS_DIR}/audit-logs-combined.txt"
if [[ "${SEND_LOGS}" == "true" ]]; then
  COMBINED_LOG=$(bash "${SCRIPT_DIR}/bundle-audit-logs.sh" 2>/dev/null | tail -1 || echo "${ARTIFACTS_DIR}/audit-logs-combined.txt")
fi

SUMMARY_FILE="${ARTIFACTS_DIR}/audit-summary.json"
TEST_MD="${ARTIFACTS_DIR}/test-cases.md"
TEST_CASES_FILE="${ARTIFACTS_DIR}/test-cases.json"

# 读取审计状态
AUDIT_STATUS="unknown"
TOTAL_FINDINGS=0
RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
REPO="${GITHUB_REPOSITORY:-unknown}"
REF="${GITHUB_REF:-}"
SHA_SHORT="${GITHUB_SHA:-}"
SHA_SHORT="${SHA_SHORT:0:8}"

if [[ -f "$SUMMARY_FILE" ]]; then
  read -r AUDIT_STATUS TOTAL_FINDINGS RUN_URL <<< "$(python3 -c "
import json
with open('${SUMMARY_FILE}') as f:
    s = json.load(f)
print(s.get('audit_status','unknown'), s.get('total_findings',0), s.get('run_url','${RUN_URL}'))
" 2>/dev/null || echo "unknown 0 ${RUN_URL}")"
fi

# 测试用例统计
TC_STATS="N/A"
if [[ -f "$TEST_CASES_FILE" ]]; then
  TC_STATS=$(python3 -c "
import json
with open('${TEST_CASES_FILE}') as f:
    d = json.load(f)
if d.get('executed'):
    s = d.get('execution_stats', {})
    print(f\"{s.get('passed',0)}/{s.get('total',0)} 通过\")
else:
    print(f\"{d.get('total_count',0)} 条待执行\")
" 2>/dev/null || echo "N/A")
fi

# Bug 统计（摘要消息前读取）
BUG_COUNT=0
BUG_HIGH=0
if [[ -f "${ARTIFACTS_DIR}/audit-bugs.json" ]]; then
  read -r BUG_COUNT BUG_HIGH <<< "$(python3 -c "
import json
with open('${ARTIFACTS_DIR}/audit-bugs.json') as f:
    m = json.load(f).get('meta', {})
print(m.get('total_bugs', 0), m.get('high_count', 0))
" 2>/dev/null || echo "0 0")"
fi

send_document() {
  local file="$1"
  local caption="$2"
  [[ -f "$file" ]] || { log_warn "文件不存在，跳过发送: $file"; return 1; }
  local size
  size=$(wc -c < "$file" 2>/dev/null || echo 0)
  log_info "发送文档: $(basename "$file") (${size} bytes)"
  curl -sS --http1.1 -w "\n%{http_code}" \
    --max-time 120 \
    -X POST "https://api.telegram.org/bot${TOKEN}/sendDocument" \
    -F "chat_id=${CHAT_ID}" \
    -F "document=@${file}" \
    -F "caption=${caption}" \
    2>&1
}

send_message() {
  local text="$1"
  curl -sS --http1.1 -w "\n%{http_code}" \
    --max-time 30 \
    -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    -d "chat_id=${CHAT_ID}" \
    -d "disable_web_page_preview=true" \
    --data-urlencode "text=${text}" \
    2>&1
}

parse_response() {
  local resp="$1"
  HTTP_CODE=$(echo "$resp" | tail -1)
  BODY=$(echo "$resp" | sed '$d')
}

SENT_ITEMS=()
FAIL_ITEMS=()

# ── 1. 发送文字摘要 ──
if [[ "${SEND_SUMMARY}" == "true" ]]; then
  MSG=$(cat <<EOF
[Code Audit] ${AUDIT_STATUS^^}

仓库: ${REPO}
分支: ${REF}
Commit: ${SHA_SHORT}
审计状态: ${AUDIT_STATUS}
问题数: ${TOTAL_FINDINGS}
Bug数: ${BUG_COUNT:-0}
测试用例: ${TC_STATS}
运行: ${RUN_URL}
Bot: ${BOT_USER}
EOF
)
  RESP=$(send_message "$MSG")
  parse_response "$RESP"
  if [[ "$HTTP_CODE" == "200" ]]; then
    SENT_ITEMS+=("摘要消息")
    log_info "摘要消息发送成功"
  else
    FAIL_ITEMS+=("摘要消息:${HTTP_CODE}")
    log_warn "摘要消息失败: ${BODY}"
  fi
fi

# ── 2b. 发送 Bug 报告 MD（存在错误时）──
if [[ "${SEND_BUG}" == "true" && -f "$BUG_MD" && "${BUG_COUNT:-0}" -gt 0 ]]; then
  # Bug 告警短消息
  ALERT_MSG="[BUG ALERT] 发现 ${BUG_COUNT} 个错误 (高危 ${BUG_HIGH})
仓库: ${REPO}
分支: ${REF}
详情见 audit-bugs.md 附件
运行: ${RUN_URL}"
  RESP=$(send_message "$ALERT_MSG")
  parse_response "$RESP"
  if [[ "$HTTP_CODE" == "200" ]]; then
    SENT_ITEMS+=("Bug告警")
  fi

  CAPTION="Bug报告 ${BUG_COUNT}个 | 高危${BUG_HIGH} | ${REPO} | Run#${GITHUB_RUN_ID:-0}"
  RESP=$(send_document "$BUG_MD" "$CAPTION")
  parse_response "$RESP"
  if [[ "$HTTP_CODE" == "200" ]]; then
    SENT_ITEMS+=("audit-bugs.md")
    log_info "audit-bugs.md 发送成功 (${BUG_COUNT} bugs)"
  else
    FAIL_ITEMS+=("audit-bugs.md:${HTTP_CODE}")
    log_warn "audit-bugs.md 发送失败: ${BODY}"
  fi
elif [[ "${BUG_COUNT:-0}" -eq 0 ]]; then
  log_info "未发现 Bug，跳过 audit-bugs.md 发送"
fi

# ── 3. 发送测试用例 MD 文档 ──
if [[ "${SEND_MD}" == "true" && -f "$TEST_MD" ]]; then
  CAPTION="测试用例报告 ${REPO} | ${TC_STATS} | Run#${GITHUB_RUN_ID:-0}"
  RESP=$(send_document "$TEST_MD" "$CAPTION")
  parse_response "$RESP"
  if [[ "$HTTP_CODE" == "200" ]]; then
    SENT_ITEMS+=("test-cases.md")
    log_info "test-cases.md 发送成功"
  else
    FAIL_ITEMS+=("test-cases.md:${HTTP_CODE}")
    log_warn "test-cases.md 发送失败: ${BODY}"
  fi
else
  log_warn "test-cases.md 不存在或已关闭发送"
fi

# ── 3. 发送人工审计清单 MD ──
MANUAL_MD="${ARTIFACTS_DIR}/manual-audit-checklist.md"
if [[ "${SEND_MD}" == "true" && -f "$MANUAL_MD" ]]; then
  CAPTION="人工深度审计清单 ${REPO} | Run#${GITHUB_RUN_ID:-0}"
  RESP=$(send_document "$MANUAL_MD" "$CAPTION")
  parse_response "$RESP"
  if [[ "$HTTP_CODE" == "200" ]]; then
    SENT_ITEMS+=("manual-audit-checklist.md")
    log_info "manual-audit-checklist.md 发送成功"
  else
    FAIL_ITEMS+=("manual-checklist:${HTTP_CODE}")
  fi
fi

# ── 4. 发送合并运行日志 ──
if [[ "${SEND_LOGS}" == "true" && -f "$COMBINED_LOG" ]]; then
  CAPTION="审计运行日志 ${REPO} | Run#${GITHUB_RUN_ID:-0}"
  RESP=$(send_document "$COMBINED_LOG" "$CAPTION")
  parse_response "$RESP"
  if [[ "$HTTP_CODE" == "200" ]]; then
    SENT_ITEMS+=("audit-logs-combined.txt")
    log_info "运行日志发送成功"
  else
    FAIL_ITEMS+=("audit-logs:${HTTP_CODE}")
    log_warn "运行日志发送失败: ${BODY}"
  fi
fi

# 记录日志
{
  echo "timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "sent: ${SENT_ITEMS[*]:-无}"
  echo "failed: ${FAIL_ITEMS[*]:-无}"
  echo "audit_status: ${AUDIT_STATUS}"
  echo "chat_id: ${CHAT_ID}"
} > "$LOG_FILE"

if [[ ${#SENT_ITEMS[@]} -gt 0 ]]; then
  log_info "Telegram 推送完成: ${SENT_ITEMS[*]}"
  write_diag "success" "已发送: ${SENT_ITEMS[*]}"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    cat >> "$GITHUB_STEP_SUMMARY" <<EOF

### Telegram 通知
- 已发送: ${SENT_ITEMS[*]}
- 失败: ${FAIL_ITEMS[*]:-无}
- Chat ID: \`${CHAT_ID}\`

EOF
  fi
else
  log_warn "Telegram 无任何内容发送成功"
  write_diag "failed" "全部失败: ${FAIL_ITEMS[*]:-未知}"
fi

exit 0
