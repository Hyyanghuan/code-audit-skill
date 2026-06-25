#!/usr/bin/env bash
# 加载 Telegram 配置：workflow input > 环境变量 > config/telegram.yaml 硬编码
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TG_CONFIG_FILE="${GITHUB_ACTION_PATH:-${SCRIPT_DIR}/..}/config/telegram.yaml"

load_yaml_tg() {
  python3 <<'PYEOF'
import os, sys
try:
    import yaml
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml"])
    import yaml

cfg_path = os.environ.get("TG_CONFIG_FILE", "")
data = {}
if cfg_path and os.path.isfile(cfg_path):
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

def pick(yaml_key, input_env_key=""):
    ev = os.environ.get(input_env_key, "").strip() if input_env_key else ""
    if ev:
        return ev
    return str(data.get(yaml_key, "") or "").strip()

token = pick("bot_token", "INPUT_TELEGRAM_BOT_TOKEN")
chat = pick("chat_id", "INPUT_TELEGRAM_CHAT_ID")
user = pick("bot_username", "INPUT_TELEGRAM_BOT_USERNAME")
enabled = data.get("enabled", True)
send_md = data.get("send_test_cases_md", True)
send_logs = data.get("send_audit_logs", True)
send_summary = data.get("send_summary_message", True)
send_bug = data.get("send_bug_report_md", True)
max_log_kb = data.get("max_log_size_kb", 1024)

# 输出 shell export
print(f"export TG_BOT_TOKEN='{token}'")
print(f"export TG_CHAT_ID='{chat}'")
print(f"export TG_BOT_USERNAME='{user}'")
print(f"export TG_CONFIG_ENABLED='{str(enabled).lower()}'")
print(f"export TG_SEND_TEST_CASES_MD='{str(send_md).lower()}'")
print(f"export TG_SEND_AUDIT_LOGS='{str(send_logs).lower()}'")
print(f"export TG_SEND_SUMMARY='{str(send_summary).lower()}'")
print(f"export TG_SEND_BUG_REPORT='{str(send_bug).lower()}'")
print(f"export TG_MAX_LOG_SIZE_KB='{max_log_kb}'")
print(f"export TG_CONFIG_SOURCE='{cfg_path}'")
PYEOF
}

export TG_CONFIG_FILE
if [[ -f "$TG_CONFIG_FILE" ]]; then
  eval "$(TG_CONFIG_FILE="$TG_CONFIG_FILE" load_yaml_tg)"
else
  log_warn "未找到 telegram.yaml: ${TG_CONFIG_FILE}" 2>/dev/null || true
  TG_BOT_TOKEN="${INPUT_TELEGRAM_BOT_TOKEN:-}"
  TG_CHAT_ID="${INPUT_TELEGRAM_CHAT_ID:-}"
  TG_BOT_USERNAME="${INPUT_TELEGRAM_BOT_USERNAME:-}"
fi
