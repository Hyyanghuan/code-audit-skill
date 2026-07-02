from __future__ import annotations

from app.config import settings as app_settings
from app.database import get_setting, set_setting
from app.settings_catalog import (
    ENV_MAP,
    get_default_audit_settings,
    get_default_telegram_settings,
    load_preset_modules,
)


def _bool_str(val) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    s = str(val).strip().lower()
    return "true" if s in ("1", "true", "yes", "on") else "false"


def get_audit_settings() -> dict:
    defaults = get_default_audit_settings()
    stored = get_setting("audit_config", {}) or {}
    merged = {**defaults, **stored}
    return merged


def save_audit_settings(data: dict) -> dict:
    defaults = get_default_audit_settings()
    clean = {**defaults, **{k: data[k] for k in defaults if k in data}}
    set_setting("audit_config", clean)
    return clean


def apply_preset_to_settings(preset: str) -> dict:
    current = get_audit_settings()
    current["audit_preset"] = preset
    modules = load_preset_modules(preset)
    key_map = {
        "enable_gitleaks": "enable_gitleaks",
        "enable_super_linter": "enable_super_linter",
        "enable_bandit": "enable_bandit",
        "enable_dependency_scan": "enable_dependency_scan",
        "enable_custom_rules": "enable_custom_rules",
        "enable_test_cases": "enable_test_cases",
        "enable_sast_patterns": "enable_sast_patterns",
        "enable_taint_analysis": "enable_taint_analysis",
        "enable_control_flow": "enable_control_flow",
        "enable_config_audit": "enable_config_audit",
        "enable_specialized_security": "enable_specialized_security",
        "enable_diff_audit": "enable_diff_audit",
        "enable_coverage_audit": "enable_coverage_audit",
        "enable_runtime_audit": "enable_runtime_audit",
        "enable_manual_checklist": "enable_manual_checklist",
        "super_linter_languages": "super_linter_languages",
    }
    for yaml_key, setting_key in key_map.items():
        if yaml_key in modules:
            current[setting_key] = modules[yaml_key]
    return save_audit_settings(current)


def audit_settings_to_env(cfg: dict | None = None) -> dict[str, str]:
    cfg = cfg or get_audit_settings()
    env: dict[str, str] = {}
    bool_keys = {
        "fail_on_findings",
        "upload_artifacts",
        "enable_sarif",
        *{k for k in ENV_MAP if k.startswith("enable_")},
    }

    for key, env_key in ENV_MAP.items():
        val = cfg.get(key)
        if val is None:
            continue
        if key in bool_keys:
            env[env_key] = _bool_str(val)
        elif key == "artifact_retention_days":
            env[env_key] = str(int(val))
        else:
            env[env_key] = str(val)

    auto_tg = cfg.get("auto_send_telegram", False)
    env["INPUT_ENABLE_TELEGRAM"] = _bool_str(auto_tg)
    env["INPUT_AUDIT_PRESET"] = str(cfg.get("audit_preset", "security"))
    return env


def get_effective_retention_hours() -> int:
    cfg = get_audit_settings()
    return int(cfg.get("job_retention_hours") or app_settings.job_retention_hours)
