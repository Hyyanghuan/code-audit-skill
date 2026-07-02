#!/usr/bin/env bash
# 本地运行 Code Audit Skill（模拟 GitHub Actions 主流程）
# 用法: bash scripts/run-local-audit.sh [目标目录] [--tg] [--preset=security]
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="test-fixtures/normal-project"
ENABLE_TG="false"
PRESET="${INPUT_AUDIT_PRESET:-security}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tg) ENABLE_TG="true"; shift ;;
    --preset=*) PRESET="${1#*=}"; shift ;;
    --preset) PRESET="${2:-security}"; shift 2 ;;
    --full) PRESET="full"; shift ;;
    --minimal) PRESET="minimal"; shift ;;
    -h|--help)
      echo "用法: bash scripts/run-local-audit.sh [目标目录] [--tg] [--preset=security]"
      exit 0
      ;;
    -*) echo "未知参数: $1" >&2; exit 1 ;;
    *) TARGET="$1"; shift ;;
  esac
done

export GITHUB_WORKSPACE="$ROOT"
export GITHUB_ACTION_PATH="$ROOT"
export GITHUB_RUN_ID="${GITHUB_RUN_ID:-local-$$}"
export RUNNER_TEMP="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
export GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-local/code-audit-skill}"
export GITHUB_REF="${GITHUB_REF:-refs/heads/local}"
export GITHUB_SHA="${GITHUB_SHA:-local0000}"
export GITHUB_EVENT_NAME="${GITHUB_EVENT_NAME:-local}"

export INPUT_WORKING_DIRECTORY="$TARGET"
export INPUT_FAIL_ON_FINDINGS="${INPUT_FAIL_ON_FINDINGS:-false}"
export INPUT_UPLOAD_ARTIFACTS="${INPUT_UPLOAD_ARTIFACTS:-true}"
export INPUT_ENABLE_TELEGRAM="$ENABLE_TG"
export INPUT_AUDIT_PRESET="$PRESET"
export INPUT_ENABLE_SARIF="${INPUT_ENABLE_SARIF:-true}"

echo "=========================================="
echo " Code Audit Skill — 本地运行"
echo " 目标: $TARGET"
echo " preset: $PRESET | TG: $ENABLE_TG"
echo " 产物: \$RUNNER_TEMP/code-audit-$GITHUB_RUN_ID/artifacts/"
echo "=========================================="

cd "$ROOT"

run_step() {
  echo ""
  echo ">>> $1"
  bash "$2" || true
}

run_step "初始化" "${ROOT}/scripts/init.sh"
run_step "语言检测" "${ROOT}/scripts/detect-languages.sh"

# shellcheck source=/dev/null
source "${RUNNER_TEMP}/code-audit-${GITHUB_RUN_ID}/env.sh" 2>/dev/null || true

MODULES=(
  run-gitleaks.sh
  run-bandit.sh
  run-dependency-scan.sh
  run-custom-rules.sh
)

for m in "${MODULES[@]}"; do
  if [[ -f "${ROOT}/scripts/$m" ]]; then
    run_step "$m" "${ROOT}/scripts/$m"
  fi
done

for mod in sast_patterns taint_analysis control_flow config_audit specialized_security diff_audit coverage_audit runtime_audit manual_checklist; do
  export AUDIT_MODULE="$mod"
  run_step "audit-engine: $mod" "${ROOT}/scripts/run-audit-module.sh"
done

run_step "汇总结果" "${ROOT}/scripts/finalize-results.sh"
run_step "生成 Bug 报告" "${ROOT}/scripts/generate-bug-report.sh"
run_step "生成测试用例" "${ROOT}/scripts/generate-test-cases.sh"
run_step "执行测试用例" "${ROOT}/scripts/execute-test-cases.sh"

if [[ "$ENABLE_TG" == "true" ]]; then
  run_step "Telegram 推送" "${ROOT}/scripts/send-telegram.sh"
fi

ART="${RUNNER_TEMP}/code-audit-${GITHUB_RUN_ID}/artifacts"
echo ""
echo "=========================================="
echo " 完成"
echo " 摘要: ${ART}/audit-summary.json"
echo " Bug:  ${ART}/audit-bugs.md"
echo " SARIF: ${ART}/codeaudit.sarif.json"
echo "=========================================="

if command -v python3 &>/dev/null && [[ -f "${ART}/audit-summary.json" ]]; then
  python3 -c "
import json
with open('${ART}/audit-summary.json') as f:
    s = json.load(f)
print('audit_status:', s.get('audit_status'))
print('findings:', s.get('total_findings'))
"
fi
