#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

# 回退 artifacts 目录（init 失败时）
if [[ -z "${ARTIFACTS_DIR:-}" ]]; then
  ARTIFACTS_DIR="${RUNNER_TEMP:-/tmp}/code-audit-${GITHUB_RUN_ID:-}/artifacts"
  mkdir -p "$ARTIFACTS_DIR"
fi

LOG_FILE="${ARTIFACTS_DIR}/telegram.log"
DIAG_FILE="${ARTIFACTS_DIR}/telegram-diagnostic.json"

log_info "========== Telegram 汇总通知（审计 + 测试用例）=========="

TOKEN="${INPUT_TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${INPUT_TELEGRAM_CHAT_ID:-}"
BOT_USER="${INPUT_TELEGRAM_BOT_USERNAME:-}"

# --- 诊断信息 ---
TOKEN_SET="false"
TOKEN_LEN=0
[[ -n "$TOKEN" ]] && TOKEN_SET="true" && TOKEN_LEN=${#TOKEN}
CHAT_ID_SET="false"
[[ -n "$CHAT_ID" ]] && CHAT_ID_SET="true"

log_info "TG 诊断: token已设置=${TOKEN_SET} (长度=${TOKEN_LEN}) chat_id已设置=${CHAT_ID_SET} chat_id=${CHAT_ID:-空}"
log_info "TG 诊断: enable_telegram=${ENABLE_TELEGRAM:-unknown} artifacts_dir=${ARTIFACTS_DIR}"

write_diag() {
  local status="$1"
  local detail="$2"
  local http="${3:-}"
  cat > "$DIAG_FILE" <<EOF
{
  "status": "${status}",
  "detail": "${detail}",
  "http_code": "${http}",
  "token_configured": ${TOKEN_SET},
  "token_length": ${TOKEN_LEN},
  "chat_id_configured": ${CHAT_ID_SET},
  "chat_id": "${CHAT_ID:-}",
  "artifacts_dir": "${ARTIFACTS_DIR}",
  "summary_file_exists": $( [[ -f "${ARTIFACTS_DIR}/audit-summary.json" ]] && echo true || echo false ),
  "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
}
EOF
}

if [[ -z "$TOKEN" || -z "$CHAT_ID" ]]; then
  MSG="Telegram token 或 chat_id 为空，无法发送"
  log_warn "$MSG"
  echo "::warning title=Telegram 发送跳过::${MSG}。请检查 GitHub Secrets: TG_BOT_TOKEN、TG_CHAT_ID"
  write_diag "skipped" "$MSG"
  exit 0
fi

SUMMARY_FILE="${ARTIFACTS_DIR}/audit-summary.json"
TEST_CASES_FILE="${ARTIFACTS_DIR}/test-cases.json"

# 读取审计汇总
if [[ -f "$SUMMARY_FILE" ]]; then
  read -r AUDIT_STATUS TOTAL_FINDINGS RUN_URL REPO REF SHA <<< "$(python3 -c "
import json
with open('${SUMMARY_FILE}') as f:
    s = json.load(f)
print(s.get('audit_status','unknown'), s.get('total_findings',0), s.get('run_url',''), '${GITHUB_REPOSITORY:-}', '${GITHUB_REF:-}', '${GITHUB_SHA:-}'[:8])
" 2>/dev/null || echo "unknown 0 '' '' '' ''")"
else
  AUDIT_STATUS="unknown"
  TOTAL_FINDINGS=0
  RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
  REPO="${GITHUB_REPOSITORY:-unknown}"
  REF="${GITHUB_REF:-}"
  SHA="${GITHUB_SHA:-}"
  SHA="${SHA:0:8}"
  log_warn "audit-summary.json 不存在，使用默认概览"
fi

# 构建模块详情（纯文本，避免 HTML 解析失败）
MODULE_DETAIL=""
if [[ -f "$SUMMARY_FILE" ]]; then
  MODULE_DETAIL=$(python3 -c "
import json
with open('${SUMMARY_FILE}') as f:
    s = json.load(f)
icons = {'success':'[OK]','failure':'[FAIL]','skipped':'[SKIP]','error':'[WARN]'}
lines = []
for mod, data in s.get('modules', {}).items():
    st = data.get('status','unknown')
    icon = icons.get(st, '[?]')
    findings = data.get('findings', 0)
    msg = data.get('message', '')
    lines.append(f'{icon} {mod}: {st} ({findings}) - {msg}')
print(chr(10).join(lines) if lines else '无模块详情')
" 2>/dev/null || echo "无法解析模块详情")
fi

# 构建测试用例详情
TEST_CASE_DETAIL=""
TEST_PASS_RATE="N/A"
ALL_TESTS_PASSED="unknown"
if [[ -f "$TEST_CASES_FILE" ]]; then
  TEST_CASE_DETAIL=$(python3 -c "
import json
with open('${TEST_CASES_FILE}') as f:
    d = json.load(f)
if not d.get('executed'):
    print('测试用例尚未执行')
    raise SystemExit(0)
stats = d.get('execution_stats', {})
lines = [f\"总计: {stats.get('total',0)} | 通过: {stats.get('passed',0)} | 失败: {stats.get('failed',0)}\"]
for c in d.get('test_cases', []):
    icon = '[OK]' if c.get('passed') is True else ('[FAIL]' if c.get('passed') is False else '[?]')
    passed = '是' if c.get('passed') is True else ('否' if c.get('passed') is False else '待执行')
    lines.append(f\"{icon} {c['tc_id']} {c['test_function']}: {passed}\")
    lines.append(f\"   结果: {c.get('test_result','')[:120]}\")
print(chr(10).join(lines))
" 2>/dev/null || echo "无法解析测试用例")
  TEST_STATS=$(python3 -c "
import json
with open('${TEST_CASES_FILE}') as f:
    d = json.load(f)
if d.get('executed'):
    s = d.get('execution_stats', {})
    print(f\"{s.get('passed',0)}/{s.get('total',0)}\")
    print('true' if s.get('failed',1)==0 else 'false')
else:
    print('N/A')
    print('unknown')
" 2>/dev/null)
  TEST_PASS_RATE=$(echo "$TEST_STATS" | head -1)
  ALL_TESTS_PASSED=$(echo "$TEST_STATS" | tail -1)
elif [[ -f "$SUMMARY_FILE" ]]; then
  TEST_CASE_DETAIL=$(python3 -c "
import json
with open('${SUMMARY_FILE}') as f:
    tc = json.load(f).get('test_cases', {})
if not tc:
    print('未启用测试用例')
else:
    lines = [f\"总计: {tc.get('total',0)} | 通过: {tc.get('passed',0)} | 失败: {tc.get('failed',0)}\"]
    for c in tc.get('cases', []):
        icon = '[OK]' if c.get('passed') is True else ('[FAIL]' if c.get('passed') is False else '[?]')
        lines.append(f\"{icon} {c['tc_id']} {c['test_function']}: {c.get('passed_label','')}\")
    print(chr(10).join(lines))
" 2>/dev/null || echo "无测试用例数据")
  TEST_PASS_RATE=$(python3 -c "
import json
with open('${SUMMARY_FILE}') as f:
    tc = json.load(f).get('test_cases', {})
print(tc.get('pass_rate','N/A') if tc else 'N/A')
" 2>/dev/null || echo "N/A")
fi

OVERALL_STATUS="$AUDIT_STATUS"
if [[ "$ALL_TESTS_PASSED" == "false" ]]; then
  OVERALL_STATUS="failure"
elif [[ "$AUDIT_STATUS" == "success" && "$ALL_TESTS_PASSED" == "true" ]]; then
  OVERALL_STATUS="success"
fi

if [[ "$OVERALL_STATUS" == "success" ]]; then
  HEADER="[PASS] 代码审计与验收测试全部通过"
elif [[ "$AUDIT_STATUS" == "failure" ]]; then
  HEADER="[FAIL] 代码审计未通过"
elif [[ "$ALL_TESTS_PASSED" == "false" ]]; then
  HEADER="[WARN] 审计完成但验收测试未全部通过"
elif [[ "$AUDIT_STATUS" == "skipped" ]]; then
  HEADER="[SKIP] 代码审计已跳过（无可扫描内容）"
else
  HEADER="[?] 代码审计状态未知"
fi

EVENT_NAME="${GITHUB_EVENT_NAME:-manual}"
ACTOR="${GITHUB_ACTOR:-unknown}"
SHA_SHORT="${GITHUB_SHA:-unknown}"
SHA_SHORT="${SHA_SHORT:0:8}"

# 纯文本消息（避免 HTML parse_mode 导致 400）
MESSAGE=$(cat <<EOF
${HEADER}

━━━ 审计概览 ━━━
仓库: ${REPO}
分支/Ref: ${REF}
Commit: ${SHA_SHORT}
触发: ${EVENT_NAME} by ${ACTOR}
审计状态: ${AUDIT_STATUS}
问题总数: ${TOTAL_FINDINGS}

扫描模块:
${MODULE_DETAIL}

━━━ 验收测试用例 ━━━
通过率: ${TEST_PASS_RATE}
${TEST_CASE_DETAIL}

运行链接: ${RUN_URL}
$( [[ -n "$BOT_USER" ]] && echo "Bot: ${BOT_USER}" )
EOF
)

# Telegram 消息长度限制 4096
MSG_LEN=${#MESSAGE}
if [[ "$MSG_LEN" -gt 4000 ]]; then
  log_warn "消息过长 (${MSG_LEN} 字符)，截断至 4000"
  MESSAGE="${MESSAGE:0:3990}"$'\n...(已截断)'
fi

send_telegram() {
  local parse_mode="${1:-}"
  local extra_args=()
  [[ -n "$parse_mode" ]] && extra_args+=(-d "parse_mode=${parse_mode}")

  curl -sS -w "\n%{http_code}" \
    --max-time 30 \
    --connect-timeout 10 \
    -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    -d "chat_id=${CHAT_ID}" \
    -d "disable_web_page_preview=true" \
    "${extra_args[@]}" \
    --data-urlencode "text=${MESSAGE}" \
    2>&1
}

set +e
# 优先纯文本（无 parse_mode），兼容性最好
RESPONSE=$(send_telegram "")
CURL_EXIT=$?
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

# 失败时尝试 HTML 模式（部分旧逻辑兼容）
if [[ "$CURL_EXIT" -ne 0 || "$HTTP_CODE" != "200" ]]; then
  log_warn "纯文本发送失败 (http=${HTTP_CODE})，响应: ${BODY}"
  RESPONSE=$(send_telegram "HTML")
  CURL_EXIT=$?
  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY=$(echo "$RESPONSE" | sed '$d')
fi
set -e

{
  echo "timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "overall_status: ${OVERALL_STATUS}"
  echo "audit_status: ${AUDIT_STATUS}"
  echo "message_length: ${MSG_LEN}"
  echo "token_configured: ${TOKEN_SET}"
  echo "chat_id: ${CHAT_ID}"
  echo "curl_exit: ${CURL_EXIT}"
  echo "http_code: ${HTTP_CODE}"
  echo "response: ${BODY}"
} > "$LOG_FILE"

if [[ "$CURL_EXIT" -ne 0 || "$HTTP_CODE" != "200" ]]; then
  ERR_DETAIL=""
  if echo "$BODY" | grep -q '"error_code":401'; then
    ERR_DETAIL="Bot Token 无效或已撤销，请在 @BotFather 重新生成并更新 TG_BOT_TOKEN Secret"
  elif echo "$BODY" | grep -q '"error_code":400'; then
    ERR_DETAIL="请求参数错误，常见原因: Chat ID 错误或 Bot 未加入群组"
  elif echo "$BODY" | grep -q '"error_code":403'; then
    ERR_DETAIL="Bot 被用户/群组封禁，或无发言权限"
  else
    ERR_DETAIL="HTTP ${HTTP_CODE}, 详见 telegram.log"
  fi
  log_warn "Telegram 推送失败: ${ERR_DETAIL}"
  echo "::warning title=Telegram 发送失败::${ERR_DETAIL}"
  write_diag "failed" "$ERR_DETAIL" "$HTTP_CODE"
  exit 0
fi

log_info "Telegram 汇总通知发送成功"
write_diag "success" "消息已发送" "$HTTP_CODE"

# 写入 GitHub Step Summary（Actions UI 可见）
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  cat >> "$GITHUB_STEP_SUMMARY" <<EOF

### Telegram 通知
- 状态: ✅ 已发送
- Chat ID: \`${CHAT_ID}\`
- 审计状态: ${AUDIT_STATUS}
- 问题数: ${TOTAL_FINDINGS}

EOF
fi

exit 0
