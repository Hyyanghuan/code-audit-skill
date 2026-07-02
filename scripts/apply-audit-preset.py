#!/usr/bin/env python3
"""应用 audit-presets.yaml 到模块开关（preset != full 时整包覆盖）。"""
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("GITHUB_ACTION_PATH", Path(__file__).resolve().parent.parent))
PRESETS = ROOT / "config" / "audit-presets.yaml"

MODULE_KEYS = [
    ("enable_gitleaks", "INPUT_ENABLE_GITLEAKS"),
    ("enable_super_linter", "INPUT_ENABLE_SUPER_LINTER"),
    ("enable_bandit", "INPUT_ENABLE_BANDIT"),
    ("enable_dependency_scan", "INPUT_ENABLE_DEPENDENCY_SCAN"),
    ("enable_custom_rules", "INPUT_ENABLE_CUSTOM_RULES"),
    ("enable_test_cases", "INPUT_ENABLE_TEST_CASES"),
    ("enable_sast_patterns", "INPUT_ENABLE_SAST_PATTERNS"),
    ("enable_taint_analysis", "INPUT_ENABLE_TAINT_ANALYSIS"),
    ("enable_control_flow", "INPUT_ENABLE_CONTROL_FLOW"),
    ("enable_config_audit", "INPUT_ENABLE_CONFIG_AUDIT"),
    ("enable_specialized_security", "INPUT_ENABLE_SPECIALIZED_SECURITY"),
    ("enable_diff_audit", "INPUT_ENABLE_DIFF_AUDIT"),
    ("enable_coverage_audit", "INPUT_ENABLE_COVERAGE_AUDIT"),
    ("enable_runtime_audit", "INPUT_ENABLE_RUNTIME_AUDIT"),
    ("enable_manual_checklist", "INPUT_ENABLE_MANUAL_CHECKLIST"),
]


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml"])
        import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def normalize_bool(val, default="true"):
    if val is None or str(val).strip() == "":
        s = default.lower()
    else:
        s = str(val).strip().lower()
    return "true" if s in ("1", "true", "yes", "on") else "false"


def main():
    preset = (os.environ.get("INPUT_AUDIT_PRESET") or "full").strip().lower()
    cfg = load_yaml(PRESETS)
    presets = cfg.get("presets") or {}

    if preset in ("", "full", "custom"):
        # full/custom：保留各 INPUT_ENABLE_* 原值
        for _, env_key in MODULE_KEYS:
            print(f"{env_key}={normalize_bool(os.environ.get(env_key))}")
        sl = os.environ.get("INPUT_SUPER_LINTER_LANGUAGES", "")
        print(f"INPUT_SUPER_LINTER_LANGUAGES={sl}")
        print(f"AUDIT_PRESET_APPLIED=full")
        return

    bundle = presets.get(preset, {})
    if not bundle:
        print(f"::warning title=未知 preset::{preset}，回退 full", file=sys.stderr)
        preset = "full"
        for _, env_key in MODULE_KEYS:
            print(f"{env_key}={normalize_bool(os.environ.get(env_key))}")
        print(f"AUDIT_PRESET_APPLIED=full")
        return

    modules = bundle.get("modules") or {}
    for yaml_key, env_key in MODULE_KEYS:
        if yaml_key in modules:
            val = "true" if modules[yaml_key] else "false"
        else:
            val = normalize_bool(os.environ.get(env_key))
        print(f"{env_key}={val}")

    sl = modules.get("super_linter_languages", os.environ.get("INPUT_SUPER_LINTER_LANGUAGES", ""))
    print(f"INPUT_SUPER_LINTER_LANGUAGES={sl}")
    print(f"AUDIT_PRESET_APPLIED={preset}")


if __name__ == "__main__":
    main()
