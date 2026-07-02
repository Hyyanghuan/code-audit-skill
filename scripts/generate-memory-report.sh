#!/usr/bin/env bash
# 记忆层报告生成入口（包装 Python 脚本）
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/generate-memory-report.py" "$@"
