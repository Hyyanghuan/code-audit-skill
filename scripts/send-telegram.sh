#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

log_info "========== Telegram 汇总通知（审计 + 测试用例）=========="

TOKEN="${INPUT_TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${INPUT_TELEGRAM_CHAT_ID:-}"
BOT_USER="${INPUT_TELEGRAM_BOT_USERNAME:-}"

if [[ -z "$TOKEN" || -z "$CHAT_ID" ]]; then
  log_warn "Telegram token 或 chat_id 为空，跳过通知"
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
fi

# 构建模块详情
MODULE_DETAIL=""
if [[ -f "$SUMMARY_FILE" ]]; then
  MODULE_DETAIL=$(python3 -c "
import json
with open('${SUMMARY_FILE}') as f:
    s = json.load(f)
icons = {'success':'✅','failure':'❌','skipped':'⏭️','error':'⚠️'}
lines = []
for mod, data in s.get('modules', {}).items():
    st = data.get('status','unknown')
    icon = icons.get(st, '❓')
    findings = data.get('findings', 0)
    msg = data.get('message', '')
    lines.append(f'{icon} {mod}: {st} ({findings}) - {msg}')
print(chr(10).join(lines) if lines else '无模块详情')
" 2>/dev/null || echo "无法解析模块详情")
fi

# 构建测试用例详情
TEST_CASE_DETAIL=""
TEST_STATS=""
ALL_TESTS_PASSED="unknown"
if [[ -f "$TEST_CASES_FILE" ]]; then
  TEST_CASE_DETAIL=$(python3 -c "
import json
with open('${TEST_CASES_FILE}') as f:
    d = json.load(f)
if not d.get('executed'):
    print('测试用例尚未执行')
    exit()
stats = d.get('execution_stats', {})
lines = [f\"总计: {stats.get('total',0)} | 通过: {stats.get('passed',0)} | 失败: {stats.get('failed',0)}\"]
for c in d.get('test_cases', []):
    icon = '✅' if c.get('passed') is True else ('❌' if c.get('passed') is False else '⏳')
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
        icon = '✅' if c.get('passed') is True else ('❌' if c.get('passed') is False else '⏳')
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

# 综合状态判定（审计 + 测试用例）
OVERALL_STATUS="$AUDIT_STATUS"
if [[ "$ALL_TESTS_PASSED" == "false" ]]; then
  OVERALL_STATUS="failure"
elif [[ "$AUDIT_STATUS" == "success" && "$ALL_TESTS_PASSED" == "true" ]]; then
  OVERALL_STATUS="success"
fi

if [[ "$OVERALL_STATUS" == "success" ]]; then
  HEADER="✅ 代码审计与验收测试全部通过"
  EMOJI="🎉"
elif [[ "$AUDIT_STATUS" == "failure" ]]; then
  HEADER="❌ 代码审计未通过"
  EMOJI="🚨"
elif [[ "$ALL_TESTS_PASSED" == "false" ]]; then
  HEADER="⚠️ 审计完成但验收测试未全部通过"
  EMOJI="🧪"
elif [[ "$AUDIT_STATUS" == "skipped" ]]; then
  HEADER="⏭️ 代码审计已跳过（无可扫描内容）"
  EMOJI="ℹ️"
else
  HEADER="⚠️ 代码审计状态未知"
  EMOJI="❓"
fi

EVENT_NAME="${GITHUB_EVENT_NAME:-manual}"
ACTOR="${GITHUB_ACTOR:-unknown}"
SHA_SHORT="${GITHUB_SHA:-unknown}"
SHA_SHORT="${SHA_SHORT:0:8}"

escape_html() {
  echo "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
}

MESSAGE=$(cat <<EOF
${HEADER} ${EMOJI}

<b>━━━ 审计概览 ━━━</b>
<b>仓库</b>: $(escape_html "$REPO")
<b>分支/Ref</b>: $(escape_html "$REF")
<b>Commit</b>: <code>${SHA_SHORT}</code>
<b>触发</b>: ${EVENT_NAME} by ${ACTOR}
<b>审计状态</b>: ${AUDIT_STATUS}
<b>问题总数</b>: ${TOTAL_FINDINGS}

<b>扫描模块</b>:
<pre>$(escape_html "$MODULE_DETAIL")</pre>

<b>━━━ 验收测试用例 ━━━</b>
<b>通过率</b>: ${TEST_PASS_RATE:-N/A}
<pre>$(escape_html "$TEST_CASE_DETAIL")</pre>

<b>运行链接</b>: ${RUN_URL}
$( [[ -n "$BOT_USER" ]] && echo "<b>Bot</b>: ${BOT_USER}" )
EOF
)

LOG_FILE="${ARTIFACTS_DIR}/telegram.log"

set +e
RESPONSE=$(curl -sS -w "\n%{http_code}" \
  --max-time 30 \
  --connect-timeout 10 \
  -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "parse_mode=HTML" \
  -d "disable_web_page_preview=true" \
  --data-urlencode "text=${MESSAGE}" \
  2>&1)
CURL_EXIT=$?
set -e

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

{
  echo "timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "overall_status: ${OVERALL_STATUS}"
  echo "audit_status: ${AUDIT_STATUS}"
  echo "test_pass_rate: ${TEST_PASS_RATE:-N/A}"
  echo "curl_exit: ${CURL_EXIT}"
  echo "http_code: ${HTTP_CODE}"
  echo "response: ${BODY}"
} > "$LOG_FILE"

if [[ "$CURL_EXIT" -ne 0 || "$HTTP_CODE" != "200" ]]; then
  log_warn "Telegram 推送失败 (curl=${CURL_EXIT}, http=${HTTP_CODE})，不影响审计主流程"
  log_warn "响应: ${BODY}"
  exit 0
fi

log_info "Telegram 汇总通知发送成功（审计 + 测试用例）"
exit 0
