#!/usr/bin/env bash
# shellcheck disable=SC2034
# 公共工具库：参数容错、日志、路径解析
set -uo pipefail

# --- 日志 ---
log_info()  { echo "[INFO]  $(date -u +'%Y-%m-%dT%H:%M:%SZ') $*"; }
log_warn()  { echo "[WARN]  $(date -u +'%Y-%m-%dT%H:%M:%SZ') $*" >&2; }
log_error() { echo "[ERROR] $(date -u +'%Y-%m-%dT%H:%M:%SZ') $*" >&2; }

# --- 布尔入参标准化（空值 / 大小写 / 特殊字符容错）---
normalize_bool() {
  local raw="${1:-}"
  local default="${2:-false}"
  raw="$(echo "$raw" | tr '[:upper:]' '[:lower:]' | xargs 2>/dev/null || true)"
  case "$raw" in
    true|1|yes|y|on)  echo "true" ;;
    false|0|no|n|off) echo "false" ;;
    "")               echo "$default" ;;
    *)                log_warn "无法识别的布尔值 '${raw}'，使用默认 '${default}'"; echo "$default" ;;
  esac
}

# --- 安全读取环境变量（空值回退默认值）---
env_or_default() {
  local key="$1"
  local default="${2:-}"
  local val="${!key:-}"
  if [[ -z "$val" ]]; then
    echo "$default"
  else
    echo "$val"
  fi
}

# --- 解析工作目录 ---
resolve_work_dir() {
  local wd="${INPUT_WORKING_DIRECTORY:-.}"
  wd="$(echo "$wd" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$wd" ]] && wd="."
  if [[ ! -d "$GITHUB_WORKSPACE/$wd" ]]; then
    log_warn "工作目录 '$wd' 不存在，回退到仓库根目录"
    wd="."
  fi
  echo "$wd"
}

# --- 审计目录 ---
setup_audit_dirs() {
  AUDIT_DIR="${RUNNER_TEMP:-/tmp}/code-audit-${GITHUB_RUN_ID:-$$}"
  ARTIFACTS_DIR="$AUDIT_DIR/artifacts"
  RESULTS_DIR="$AUDIT_DIR/results"
  mkdir -p "$ARTIFACTS_DIR" "$RESULTS_DIR"
  export AUDIT_DIR ARTIFACTS_DIR RESULTS_DIR
}

# --- 加载 init 阶段写入的环境 ---
load_audit_env() {
  local env_file="${RUNNER_TEMP:-/tmp}/code-audit-${GITHUB_RUN_ID:-}/env.sh"
  if [[ -f "$env_file" ]]; then
    # shellcheck disable=SC1090
    source "$env_file"
    return 0
  fi
  # 兼容旧路径匹配
  env_file="$(ls -t ${RUNNER_TEMP:-/tmp}/code-audit-*/env.sh 2>/dev/null | head -1)"
  if [[ -f "$env_file" ]]; then
    # shellcheck disable=SC1090
    source "$env_file"
    return 0
  fi
  log_warn "未找到 audit env.sh，使用默认值"
  return 1
}

# --- 写入模块结果 JSON ---
write_module_result() {
  local module="$1"
  local status="$2"   # success | failure | skipped | error
  local findings="${3:-0}"
  local message="${4:-}"
  local log_file="${5:-}"

  # JSON 转义 message
  message="$(echo "$message" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')"

  cat > "$RESULTS_DIR/${module}.json" <<EOF
{
  "module": "${module}",
  "status": "${status}",
  "findings": ${findings},
  "message": "${message}",
  "log_file": "${log_file}",
  "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
}
EOF
  log_info "模块 [${module}] 状态=${status} 发现=${findings}"
}

# --- 默认忽略路径（编译产物、测试缓存、第三方依赖）---
DEFAULT_IGNORE_PATTERNS=(
  '**/node_modules/**'
  '**/vendor/**'
  '**/.venv/**'
  '**/venv/**'
  '**/__pycache__/**'
  '**/.pytest_cache/**'
  '**/dist/**'
  '**/build/**'
  '**/target/**'
  '**/.git/**'
  '**/coverage/**'
  '**/.tox/**'
  '**/.mypy_cache/**'
  '**/.ruff_cache/**'
  '**/site-packages/**'
  '**/*.min.js'
  '**/*.min.css'
  '**/package-lock.json'
  '**/yarn.lock'
  '**/poetry.lock'
  '**/Pipfile.lock'
)

# --- 生成 .gitignore 风格的忽略文件供工具使用 ---
generate_ignore_file() {
  local out="$1"
  {
    for p in "${DEFAULT_IGNORE_PATTERNS[@]}"; do echo "$p"; done
    if [[ -n "${INPUT_IGNORE_PATHS_FILE:-}" && -f "$INPUT_IGNORE_PATHS_FILE" ]]; then
      cat "$INPUT_IGNORE_PATHS_FILE"
    elif [[ -f "${GITHUB_ACTION_PATH}/config/ignore-paths.txt" ]]; then
      grep -v '^#' "${GITHUB_ACTION_PATH}/config/ignore-paths.txt" | grep -v '^$' || true
    fi
  } > "$out"
}

# --- GitHub Actions 输出 ---
gha_output() {
  local name="$1"
  local value="$2"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      echo "${name}<<EOF_OUTPUT"
      echo "$value"
      echo "EOF_OUTPUT"
    } >> "$GITHUB_OUTPUT"
  fi
}

# --- 统计目录下某扩展名文件数（排除忽略路径）---
count_files_with_ext() {
  local dir="$1"
  shift
  local count=0
  for ext in "$@"; do
    local n
    n=$(find "$dir" -type f -name "*.${ext}" \
      -not -path '*/node_modules/*' \
      -not -path '*/vendor/*' \
      -not -path '*/.venv/*' \
      -not -path '*/venv/*' \
      -not -path '*/dist/*' \
      -not -path '*/build/*' \
      -not -path '*/target/*' \
      -not -path '*/__pycache__/*' \
      2>/dev/null | wc -l | tr -d ' ')
    count=$((count + n))
  done
  echo "$count"
}

# --- 检测是否存在依赖清单 ---
has_dependency_manifest() {
  local dir="$1"
  [[ -f "$dir/package.json" || -f "$dir/requirements.txt" || -f "$dir/pyproject.toml" \
     || -f "$dir/Pipfile" || -f "$dir/go.mod" || -f "$dir/Gemfile" \
     || -f "$dir/pom.xml" || -f "$dir/build.gradle" || -f "$dir/Cargo.toml" ]]
}
