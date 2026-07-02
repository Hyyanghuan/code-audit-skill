#!/usr/bin/env python3
"""企业级能力单元测试。"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def test_version_file():
    v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert v == "1.0.0"


def test_telegram_yaml_no_secrets():
    text = (ROOT / "config" / "telegram.yaml").read_text(encoding="utf-8")
    assert "AAH" not in text  # 常见 TG token 片段
    assert 'bot_token: ""' in text or "bot_token: ''" in text or 'bot_token: ""' in text.replace("'", '"')


def test_audit_presets_yaml():
    import yaml
    data = yaml.safe_load((ROOT / "config" / "audit-presets.yaml").read_text(encoding="utf-8"))
    assert "minimal" in data["presets"]
    assert data["presets"]["minimal"]["modules"]["enable_super_linter"] is False


def test_apply_preset_minimal():
    env = os.environ.copy()
    env["INPUT_AUDIT_PRESET"] = "minimal"
    env["INPUT_ENABLE_GITLEAKS"] = "true"
    out = subprocess.check_output([sys.executable, str(SCRIPTS / "apply-audit-preset.py")], env=env, text=True)
    assert "INPUT_ENABLE_SUPER_LINTER=false" in out
    assert "AUDIT_PRESET_APPLIED=minimal" in out


def test_apply_preset_full():
    env = os.environ.copy()
    env["INPUT_AUDIT_PRESET"] = "full"
    env["INPUT_ENABLE_BANDIT"] = "false"
    out = subprocess.check_output([sys.executable, str(SCRIPTS / "apply-audit-preset.py")], env=env, text=True)
    assert "INPUT_ENABLE_BANDIT=false" in out


def test_load_tg_config_priority():
    """环境变量应优先于空 yaml（Python 路径）。"""
    os.environ["TG_BOT_TOKEN"] = "env-token-test"
    os.environ["TG_CHAT_ID"] = "-100123"
    os.environ.pop("INPUT_TELEGRAM_BOT_TOKEN", None)
    sys.path.insert(0, str(SCRIPTS))
    import importlib
    mod = importlib.import_module("generate_requirements_checklist")
    importlib.reload(mod)
    cfg = mod.load_tg_config()
    assert cfg.get("bot_token") == "env-token-test"
    assert cfg.get("chat_id") == "-100123"
    os.environ.pop("TG_BOT_TOKEN", None)
    os.environ.pop("TG_CHAT_ID", None)


def test_generate_sarif_empty():
    import tempfile
    import shutil
    tmp = Path(tempfile.mkdtemp())
    try:
        os.environ["ARTIFACTS_DIR"] = str(tmp)
        os.environ["RESULTS_DIR"] = str(tmp)
        os.environ["GITHUB_ACTION_PATH"] = str(ROOT)
        (tmp / "audit-summary.json").write_text('{"modules": {}, "audit_status": "success"}', encoding="utf-8")
        out = subprocess.check_output([sys.executable, str(SCRIPTS / "generate-sarif.py")], text=True)
        sarif_path = Path(out.splitlines()[0])
        assert sarif_path.is_file()
        import json
        data = json.loads(sarif_path.read_text(encoding="utf-8"))
        assert data["version"] == "2.1.0"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_requirements_registry():
    import yaml
    reg = yaml.safe_load((ROOT / "docs" / "memory" / "requirements-registry.yaml").read_text(encoding="utf-8"))
    assert len(reg.get("requirements", [])) >= 5
