#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

MODULE="super_linter"
LOG_FILE="${ARTIFACTS_DIR}/super-linter.log"
FINDINGS=0
STATUS="skipped"
MESSAGE=""

log_info "========== Super-Linter 多语言规范检查 =========="

# 加载语言检测结果
DETECT_FILE="${ARTIFACTS_DIR}/detect-languages.json"
if [[ -f "$DETECT_FILE" ]]; then
  HAS_PYTHON=$(python3 -c "import json; print(str(json.load(open('${DETECT_FILE}')).get('has_python', False)).lower())" 2>/dev/null || echo "false")
  HAS_JS=$(python3 -c "import json; print(str(json.load(open('${DETECT_FILE}')).get('has_javascript', False)).lower())" 2>/dev/null || echo "false")
  IS_EMPTY=$(python3 -c "import json; print(str(json.load(open('${DETECT_FILE}')).get('is_empty', False)).lower())" 2>/dev/null || echo "false")
fi

if [[ "${IS_EMPTY:-false}" == "true" ]]; then
  MESSAGE="空项目，跳过 super-linter"
  write_module_result "$MODULE" "skipped" 0 "$MESSAGE" "$LOG_FILE"
  exit 0
fi

LINTER_IMAGE="ghcr.io/super-linter/super-linter:slim-v7.2.1"
export RUN_LOCAL=true
export USE_FIND_ALGORITHM=true
export DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
export FILTER_REGEX_EXCLUDE='(node_modules|vendor|\.venv|venv|dist|build|target|__pycache__|\.git|coverage|\.tox|\.pytest_cache|\.mypy_cache|\.ruff_cache|site-packages|test-fixtures)'

# 语言开关
LANGUAGES="${INPUT_SUPER_LINTER_LANGUAGES:-}"
VALIDATE_ANY=false

enable_lang() {
  local flag="$1"
  export "$flag=true"
  VALIDATE_ANY=true
}

if [[ -n "$LANGUAGES" ]]; then
  IFS=',' read -ra LANG_ARR <<< "$LANGUAGES"
  for lang in "${LANG_ARR[@]}"; do
    lang="$(echo "$lang" | tr '[:upper:]' '[:lower:]' | xargs 2>/dev/null || true)"
    case "$lang" in
      python)     enable_lang VALIDATE_PYTHON_PYLINT ;;
      javascript|js) enable_lang VALIDATE_JAVASCRIPT_ES ;;
      typescript|ts) enable_lang VALIDATE_TYPESCRIPT_ES ;;
      go)         enable_lang VALIDATE_GOLANG ;;
      yaml)       enable_lang VALIDATE_YAML ;;
      json)       enable_lang VALIDATE_JSON ;;
      markdown|md) enable_lang VALIDATE_MARKDOWN ;;
      shell|bash|sh) enable_lang VALIDATE_BASH ;;
      *)          log_warn "未知 linter 语言: ${lang}" ;;
    esac
  done
else
  [[ "${HAS_PYTHON:-false}" == "true" ]] && enable_lang VALIDATE_PYTHON_PYLINT
  [[ "${HAS_JS:-false}" == "true" ]]       && enable_lang VALIDATE_JAVASCRIPT_ES VALIDATE_TYPESCRIPT_ES
  enable_lang VALIDATE_YAML
  enable_lang VALIDATE_JSON
  enable_lang VALIDATE_MARKDOWN
  enable_lang VALIDATE_BASH
fi

if [[ "$VALIDATE_ANY" != "true" ]]; then
  MESSAGE="无匹配语言代码，跳过 super-linter"
  write_module_result "$MODULE" "skipped" 0 "$MESSAGE" "$LOG_FILE"
  exit 0
fi

# 使用 Docker 运行 super-linter（固定版本镜像）
if ! command -v docker &>/dev/null; then
  MESSAGE="Docker 不可用，super-linter 已降级跳过"
  write_module_result "$MODULE" "error" 0 "$MESSAGE" "$LOG_FILE"
  exit 0
fi

log_info "拉取镜像 ${LINTER_IMAGE} ..."
docker pull "$LINTER_IMAGE" >>"$LOG_FILE" 2>&1 || {
  MESSAGE="super-linter 镜像拉取失败，已降级跳过"
  write_module_result "$MODULE" "error" 0 "$MESSAGE" "$LOG_FILE"
  exit 0
}

ENV_ARGS=()
while IFS='=' read -r k v; do
  [[ "$k" =~ ^VALIDATE_ ]] && ENV_ARGS+=(-e "${k}=${v}")
done < <(env)

set +e
docker run --rm \
  -e RUN_LOCAL=true \
  -e USE_FIND_ALGORITHM=true \
  -e DEFAULT_BRANCH="${DEFAULT_BRANCH}" \
  -e FILTER_REGEX_EXCLUDE="${FILTER_REGEX_EXCLUDE}" \
  -e GITHUB_WORKSPACE=/tmp/lint \
  -e GITHUB_TOKEN="${GITHUB_TOKEN:-}" \
  "${ENV_ARGS[@]}" \
  -v "${ABS_WORK_DIR}:/tmp/lint" \
  -w /tmp/lint \
  "$LINTER_IMAGE" \
  2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

FINDINGS=$(grep -cE '\[ERROR\]|Linted.*errors found|Error code:' "$LOG_FILE" 2>/dev/null || echo "0")
FINDINGS=$(echo "$FINDINGS" | tr -dc '0-9')
[[ -z "$FINDINGS" ]] && FINDINGS=0

if [[ "$EXIT_CODE" -eq 0 && "$FINDINGS" -eq 0 ]]; then
  STATUS="success"
  MESSAGE="规范检查通过"
elif [[ "$EXIT_CODE" -ne 0 || "$FINDINGS" -gt 0 ]]; then
  STATUS="failure"
  MESSAGE="发现 ${FINDINGS} 处规范问题"
else
  STATUS="error"
  MESSAGE="super-linter 执行异常，已降级"
fi

write_module_result "$MODULE" "$STATUS" "$FINDINGS" "$MESSAGE" "$LOG_FILE"
[[ "$STATUS" == "failure" ]] && exit 1 || exit 0
