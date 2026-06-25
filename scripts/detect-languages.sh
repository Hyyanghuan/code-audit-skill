#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
load_audit_env || true

ABS="${ABS_WORK_DIR:-${GITHUB_WORKSPACE}}"

log_info "检测项目语言: ${ABS}"

HAS_PYTHON="false"
HAS_JS="false"
HAS_GO="false"
HAS_RUBY="false"
HAS_JAVA="false"
HAS_RUST="false"
HAS_LINTABLE="false"
HAS_DEPS="false"

py_count=$(count_files_with_ext "$ABS" py)
js_count=$(count_files_with_ext "$ABS" js ts jsx tsx)
go_count=$(count_files_with_ext "$ABS" go)
rb_count=$(count_files_with_ext "$ABS" rb)
java_count=$(count_files_with_ext "$ABS" java)
rs_count=$(count_files_with_ext "$ABS" rs)
md_count=$(count_files_with_ext "$ABS" md yaml yml json sh bash)

[[ "$py_count" -gt 0 ]]   && HAS_PYTHON="true"
[[ "$js_count" -gt 0 ]]   && HAS_JS="true"
[[ "$go_count" -gt 0 ]]   && HAS_GO="true"
[[ "$rb_count" -gt 0 ]]   && HAS_RUBY="true"
[[ "$java_count" -gt 0 ]]  && HAS_JAVA="true"
[[ "$rs_count" -gt 0 ]]   && HAS_RUST="true"

if [[ "$py_count" -gt 0 || "$js_count" -gt 0 || "$go_count" -gt 0 \
      || "$rb_count" -gt 0 || "$java_count" -gt 0 || "$md_count" -gt 0 ]]; then
  HAS_LINTABLE="true"
fi

if has_dependency_manifest "$ABS" || [[ "$py_count" -gt 0 || "$js_count" -gt 0 || "$go_count" -gt 0 ]]; then
  HAS_DEPS="true"
fi

# 空项目检测
TOTAL_FILES=$(find "$ABS" -type f \
  -not -path '*/.git/*' \
  -not -path '*/node_modules/*' \
  2>/dev/null | wc -l | tr -d ' ')
IS_EMPTY="false"
[[ "$TOTAL_FILES" -eq 0 ]] && IS_EMPTY="true"

DETECT_JSON="${RESULTS_DIR:-${RUNNER_TEMP}/code-audit-detect}/detect.json"
mkdir -p "$(dirname "$DETECT_JSON")"
cat > "$DETECT_JSON" <<EOF
{
  "has_python": ${HAS_PYTHON},
  "has_javascript": ${HAS_JS},
  "has_go": ${HAS_GO},
  "has_ruby": ${HAS_RUBY},
  "has_java": ${HAS_JAVA},
  "has_rust": ${HAS_RUST},
  "has_lintable_code": ${HAS_LINTABLE},
  "has_dependencies": ${HAS_DEPS},
  "is_empty": ${IS_EMPTY},
  "file_counts": {"py": ${py_count}, "js_ts": ${js_count}, "go": ${go_count}, "total": ${TOTAL_FILES}}
}
EOF

if [[ -n "${ARTIFACTS_DIR:-}" ]]; then
  cp "$DETECT_JSON" "${ARTIFACTS_DIR}/detect-languages.json"
fi

# 追加到 env 供后续步骤使用
ENV_FILE="${RUNNER_TEMP:-/tmp}/code-audit-${GITHUB_RUN_ID:-}/env.sh"
if [[ -f "$ENV_FILE" ]]; then
  cat >> "$ENV_FILE" <<EOF
export HAS_PYTHON='${HAS_PYTHON}'
export HAS_JS='${HAS_JS}'
export HAS_GO='${HAS_GO}'
export HAS_LINTABLE='${HAS_LINTABLE}'
export HAS_DEPS='${HAS_DEPS}'
export IS_EMPTY='${IS_EMPTY}'
EOF
fi

gha_output "has_python" "$HAS_PYTHON"
gha_output "has_javascript" "$HAS_JS"
gha_output "has_go" "$HAS_GO"
gha_output "has_lintable_code" "$HAS_LINTABLE"
gha_output "has_dependencies" "$HAS_DEPS"
gha_output "is_empty" "$IS_EMPTY"

log_info "语言检测完成: python=${HAS_PYTHON} js=${HAS_JS} go=${HAS_GO} lintable=${HAS_LINTABLE} deps=${HAS_DEPS} empty=${IS_EMPTY}"
