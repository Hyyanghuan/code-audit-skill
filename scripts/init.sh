#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

log_info "========== 代码审计 Skill 初始化 =========="

# 标准化所有布尔开关
ENABLE_GITLEAKS=$(normalize_bool "${INPUT_ENABLE_GITLEAKS:-}" "true")
ENABLE_SUPER_LINTER=$(normalize_bool "${INPUT_ENABLE_SUPER_LINTER:-}" "true")
ENABLE_BANDIT=$(normalize_bool "${INPUT_ENABLE_BANDIT:-}" "true")
ENABLE_DEPENDENCY=$(normalize_bool "${INPUT_ENABLE_DEPENDENCY_SCAN:-}" "true")
ENABLE_CUSTOM=$(normalize_bool "${INPUT_ENABLE_CUSTOM_RULES:-}" "true")
ENABLE_TEST_CASES=$(normalize_bool "${INPUT_ENABLE_TEST_CASES:-}" "true")
ENABLE_SAST_PATTERNS=$(normalize_bool "${INPUT_ENABLE_SAST_PATTERNS:-}" "true")
ENABLE_TAINT=$(normalize_bool "${INPUT_ENABLE_TAINT_ANALYSIS:-}" "true")
ENABLE_CONTROL_FLOW=$(normalize_bool "${INPUT_ENABLE_CONTROL_FLOW:-}" "true")
ENABLE_CONFIG_AUDIT=$(normalize_bool "${INPUT_ENABLE_CONFIG_AUDIT:-}" "true")
ENABLE_SPECIALIZED=$(normalize_bool "${INPUT_ENABLE_SPECIALIZED_SECURITY:-}" "true")
ENABLE_DIFF_AUDIT=$(normalize_bool "${INPUT_ENABLE_DIFF_AUDIT:-}" "true")
ENABLE_COVERAGE=$(normalize_bool "${INPUT_ENABLE_COVERAGE_AUDIT:-}" "true")
ENABLE_RUNTIME=$(normalize_bool "${INPUT_ENABLE_RUNTIME_AUDIT:-}" "true")
ENABLE_MANUAL_CHECKLIST=$(normalize_bool "${INPUT_ENABLE_MANUAL_CHECKLIST:-}" "true")

# 加载硬编码 TG 配置 config/telegram.yaml
# shellcheck source=load-telegram-config.sh
source "${SCRIPT_DIR}/load-telegram-config.sh"

# workflow input 为空时回退到 telegram.yaml
[[ -z "${INPUT_TELEGRAM_BOT_TOKEN:-}" ]] && INPUT_TELEGRAM_BOT_TOKEN="${TG_BOT_TOKEN:-}"
[[ -z "${INPUT_TELEGRAM_CHAT_ID:-}" ]] && INPUT_TELEGRAM_CHAT_ID="${TG_CHAT_ID:-}"
[[ -z "${INPUT_TELEGRAM_BOT_USERNAME:-}" ]] && INPUT_TELEGRAM_BOT_USERNAME="${TG_BOT_USERNAME:-}"

# 默认启用 TG（yaml enabled=true；workflow 可显式关闭）
if [[ -z "${INPUT_ENABLE_TELEGRAM:-}" ]]; then
  ENABLE_TELEGRAM=$(normalize_bool "${TG_CONFIG_ENABLED:-}" "true")
else
  ENABLE_TELEGRAM=$(normalize_bool "${INPUT_ENABLE_TELEGRAM:-}" "true")
fi

FAIL_ON_FINDINGS=$(normalize_bool "${INPUT_FAIL_ON_FINDINGS:-}" "true")
UPLOAD_ARTIFACTS=$(normalize_bool "${INPUT_UPLOAD_ARTIFACTS:-}" "true")

WORK_DIR="$(resolve_work_dir)"
ABS_WORK_DIR="${GITHUB_WORKSPACE}/${WORK_DIR}"
setup_audit_dirs

# Telegram 配置校验（在写入 env 之前）
TELEGRAM_CONFIGURED="true"
if [[ "$ENABLE_TELEGRAM" == "true" ]]; then
  if [[ -z "${INPUT_TELEGRAM_BOT_TOKEN:-}" || -z "${INPUT_TELEGRAM_CHAT_ID:-}" ]]; then
    TELEGRAM_CONFIGURED="false"
    log_warn "Telegram 已启用但 token/chat_id 为空，将尝试从 config/telegram.yaml 读取"
    echo "::warning title=Telegram 配置缺失::请检查 config/telegram.yaml 或 workflow secrets"
  else
    log_info "Telegram 配置就绪 (chat_id=${INPUT_TELEGRAM_CHAT_ID})"
  fi
fi

# 持久化环境供后续步骤
ENV_FILE="$AUDIT_DIR/env.sh"
cat > "$ENV_FILE" <<EOF
export AUDIT_DIR='${AUDIT_DIR}'
export ARTIFACTS_DIR='${ARTIFACTS_DIR}'
export RESULTS_DIR='${RESULTS_DIR}'
export WORK_DIR='${WORK_DIR}'
export ABS_WORK_DIR='${ABS_WORK_DIR}'
export ENABLE_GITLEAKS='${ENABLE_GITLEAKS}'
export ENABLE_SUPER_LINTER='${ENABLE_SUPER_LINTER}'
export ENABLE_BANDIT='${ENABLE_BANDIT}'
export ENABLE_DEPENDENCY='${ENABLE_DEPENDENCY}'
export ENABLE_CUSTOM='${ENABLE_CUSTOM}'
export ENABLE_TEST_CASES='${ENABLE_TEST_CASES}'
export ENABLE_SAST_PATTERNS='${ENABLE_SAST_PATTERNS}'
export ENABLE_TAINT='${ENABLE_TAINT}'
export ENABLE_CONTROL_FLOW='${ENABLE_CONTROL_FLOW}'
export ENABLE_CONFIG_AUDIT='${ENABLE_CONFIG_AUDIT}'
export ENABLE_SPECIALIZED='${ENABLE_SPECIALIZED}'
export ENABLE_DIFF_AUDIT='${ENABLE_DIFF_AUDIT}'
export ENABLE_COVERAGE='${ENABLE_COVERAGE}'
export ENABLE_RUNTIME='${ENABLE_RUNTIME}'
export ENABLE_MANUAL_CHECKLIST='${ENABLE_MANUAL_CHECKLIST}'
export ENABLE_TELEGRAM='${ENABLE_TELEGRAM}'
export FAIL_ON_FINDINGS='${FAIL_ON_FINDINGS}'
export UPLOAD_ARTIFACTS='${UPLOAD_ARTIFACTS}'
export INPUT_GITLEAKS_CONFIG='${INPUT_GITLEAKS_CONFIG:-}'
export INPUT_CUSTOM_RULES_PATH='${INPUT_CUSTOM_RULES_PATH:-}'
export INPUT_IGNORE_PATHS_FILE='${INPUT_IGNORE_PATHS_FILE:-}'
export INPUT_SUPER_LINTER_LANGUAGES='${INPUT_SUPER_LINTER_LANGUAGES:-}'
export INPUT_TELEGRAM_BOT_TOKEN='${INPUT_TELEGRAM_BOT_TOKEN:-}'
export INPUT_TELEGRAM_CHAT_ID='${INPUT_TELEGRAM_CHAT_ID:-}'
export INPUT_TELEGRAM_BOT_USERNAME='${INPUT_TELEGRAM_BOT_USERNAME:-}'
export TELEGRAM_CONFIGURED='${TELEGRAM_CONFIGURED}'
EOF

# 写入元信息
cat > "$ARTIFACTS_DIR/audit-meta.json" <<EOF
{
  "repository": "${GITHUB_REPOSITORY:-unknown}",
  "ref": "${GITHUB_REF:-}",
  "sha": "${GITHUB_SHA:-}",
  "actor": "${GITHUB_ACTOR:-}",
  "event": "${GITHUB_EVENT_NAME:-}",
  "run_id": "${GITHUB_RUN_ID:-}",
  "run_url": "${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-}/actions/runs/${GITHUB_RUN_ID:-}",
  "work_dir": "${WORK_DIR}",
  "init_time": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
}
EOF

# 输出到 GITHUB_OUTPUT
gha_output "audit_dir" "$AUDIT_DIR"
gha_output "enable_gitleaks" "$ENABLE_GITLEAKS"
gha_output "enable_super_linter" "$ENABLE_SUPER_LINTER"
gha_output "enable_bandit" "$ENABLE_BANDIT"
gha_output "enable_dependency" "$ENABLE_DEPENDENCY"
gha_output "enable_custom_rules" "$ENABLE_CUSTOM"
gha_output "enable_test_cases" "$ENABLE_TEST_CASES"
gha_output "enable_sast_patterns" "$ENABLE_SAST_PATTERNS"
gha_output "enable_taint_analysis" "$ENABLE_TAINT"
gha_output "enable_control_flow" "$ENABLE_CONTROL_FLOW"
gha_output "enable_config_audit" "$ENABLE_CONFIG_AUDIT"
gha_output "enable_specialized_security" "$ENABLE_SPECIALIZED"
gha_output "enable_diff_audit" "$ENABLE_DIFF_AUDIT"
gha_output "enable_coverage_audit" "$ENABLE_COVERAGE"
gha_output "enable_runtime_audit" "$ENABLE_RUNTIME"
gha_output "enable_manual_checklist" "$ENABLE_MANUAL_CHECKLIST"
gha_output "enable_telegram" "$ENABLE_TELEGRAM"
gha_output "telegram_configured" "$TELEGRAM_CONFIGURED"
gha_output "fail_on_findings" "$FAIL_ON_FINDINGS"
gha_output "upload_artifacts" "$UPLOAD_ARTIFACTS"
gha_output "work_dir" "$WORK_DIR"

log_info "工作目录: ${WORK_DIR}"
log_info "审计目录: ${AUDIT_DIR}"
log_info "模块开关: gitleaks=${ENABLE_GITLEAKS} linter=${ENABLE_SUPER_LINTER} bandit=${ENABLE_BANDIT} deps=${ENABLE_DEPENDENCY} custom=${ENABLE_CUSTOM} tests=${ENABLE_TEST_CASES} tg=${ENABLE_TELEGRAM}"
