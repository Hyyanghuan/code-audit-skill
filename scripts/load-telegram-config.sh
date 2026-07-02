#!/usr/bin/env bash
# 加载 Telegram 配置
# 优先级：workflow input > 环境变量 TG_* > telegram.local.yaml > telegram.yaml
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION_ROOT="${GITHUB_ACTION_PATH:-${SCRIPT_DIR}/..}"
TG_CONFIG_FILE="${TG_CONFIG_FILE:-${ACTION_ROOT}/config/telegram.yaml}"
TG_LOCAL_FILE="${ACTION_ROOT}/config/telegram.local.yaml"

load_yaml_tg() {
  python3 <<'PYEOF'
import os, sys
try:
    import yaml
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml"])
    import yaml

PLACEHOLDERS = {"", "CHANGE_ME", "YOUR_BOT_TOKEN", "YOUR_CHAT_ID", "xxx", "..."}


def is_real(val):
    if val is None:
        return False
    s = str(val).strip()
    if not s or s in PLACEHOLDERS:
        return False
    if s.startswith("${") and s.endswith("}"):
        return False
    return True


def load_merged():
    paths = [
        os.environ.get("TG_CONFIG_FILE", ""),
        os.environ.get("TG_LOCAL_FILE", ""),
    ]
    data = {}
    for p in paths:
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                part = yaml.safe_load(f) or {}
            for k, v in part.items():
                if v is not None and v != "":
                    data[k] = v
    return data


def pick(key, input_env="", env_key=""):
    ev = os.environ.get(input_env, "").strip() if input_env else ""
    if is_real(ev):
        return ev
    ev2 = os.environ.get(env_key, "").strip() if env_key else ""
    if is_real(ev2):
        return ev2
    yaml_val = data.get(key, "")
    return str(yaml_val).strip() if is_real(yaml_val) else ""


data = load_merged()
token = pick("bot_token", "INPUT_TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN")
chat = pick("chat_id", "INPUT_TELEGRAM_CHAT_ID", "TG_CHAT_ID")
user = pick("bot_username", "INPUT_TELEGRAM_BOT_USERNAME", "TG_BOT_USERNAME")

enabled = data.get("enabled", True)
send_md = data.get("send_test_cases_md", True)
send_logs = data.get("send_audit_logs", True)
send_summary = data.get("send_summary_message", True)
send_bug = data.get("send_bug_report_md", True)
send_req = data.get("send_requirements_checklist", True)
max_log_kb = data.get("max_log_size_kb", 5000)

sources = []
if os.environ.get("INPUT_TELEGRAM_BOT_TOKEN", "").strip():
    sources.append("workflow-input")
elif os.environ.get("TG_BOT_TOKEN", "").strip():
    sources.append("env")
elif is_real(data.get("bot_token")):
    sources.append("yaml")
else:
    sources.append("unset")

print(f"export TG_BOT_TOKEN='{token}'")
print(f"export TG_CHAT_ID='{chat}'")
print(f"export TG_BOT_USERNAME='{user}'")
print(f"export TG_CONFIG_ENABLED='{str(enabled).lower()}'")
print(f"export TG_SEND_TEST_CASES_MD='{str(send_md).lower()}'")
print(f"export TG_SEND_AUDIT_LOGS='{str(send_logs).lower()}'")
print(f"export TG_SEND_SUMMARY='{str(send_summary).lower()}'")
print(f"export TG_SEND_BUG_REPORT='{str(send_bug).lower()}'")
print(f"export TG_SEND_REQUIREMENTS_CHECKLIST='{str(send_req).lower()}'")
print(f"export TG_MAX_LOG_SIZE_KB='{max_log_kb}'")
print(f"export TG_CONFIG_SOURCE='{','.join(sources)}'")
PYEOF
}

export TG_CONFIG_FILE TG_LOCAL_FILE
if [[ -f "$TG_LOCAL_FILE" ]]; then
  export TG_CONFIG_FILE="$TG_LOCAL_FILE"
elif [[ ! -f "$TG_CONFIG_FILE" ]]; then
  TG_CONFIG_FILE="${ACTION_ROOT}/config/telegram.yaml"
fi

if [[ -f "$TG_CONFIG_FILE" ]] || [[ -f "$TG_LOCAL_FILE" ]]; then
  eval "$(load_yaml_tg)"
else
  TG_BOT_TOKEN="${INPUT_TELEGRAM_BOT_TOKEN:-${TG_BOT_TOKEN:-}}"
  TG_CHAT_ID="${INPUT_TELEGRAM_CHAT_ID:-${TG_CHAT_ID:-}}"
  TG_BOT_USERNAME="${INPUT_TELEGRAM_BOT_USERNAME:-}"
  TG_CONFIG_SOURCE="env-only"
fi
