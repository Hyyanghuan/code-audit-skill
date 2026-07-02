#!/usr/bin/env bash
# 发送最新需求清单到 Telegram
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/generate_requirements_checklist.py" --render --send-tg "$@"
