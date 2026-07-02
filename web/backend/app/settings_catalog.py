"""审计与 Telegram 配置项目录（中文标签、说明、可选项，供前端渲染）。"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.config import settings

PRESET_LABELS = {
    "full": "全部模块",
    "minimal": "最小门禁",
    "security": "安全专项",
    "python": "Python 聚焦",
    "ci-fast": "CI 快速",
    "custom": "自定义（按下方开关）",
}

MODULE_DESCRIPTIONS = {
    "enable_gitleaks": "扫描 Git 历史与工作区中的 API Key、Token、密码等硬编码密钥泄露。",
    "enable_super_linter": "对多种语言做编码规范、风格与静态语法检查（体积大、耗时较长）。",
    "enable_bandit": "针对 Python 源码检测 SQL 注入、命令执行、不安全反序列化等安全问题。",
    "enable_dependency_scan": "使用 Trivy 扫描 requirements/package 等依赖文件的已知 CVE 漏洞。",
    "enable_custom_rules": "按 config/custom-rules/business-rules.yaml 中的业务规则匹配违规模式。",
    "enable_test_cases": "审计结束后自动生成验收测试用例 MD 并在流水线内执行断言。",
    "enable_sast_patterns": "词法级检测 eval/exec、SQL 拼接、硬编码密码等危险代码模式。",
    "enable_taint_analysis": "追踪外部输入（Source）是否未经净化到达 exec/SQL 等危险函数（Sink）。",
    "enable_control_flow": "检测异常被空 catch 吞没、鉴权函数空实现等控制流缺陷。",
    "enable_config_audit": "审计 YAML/Dockerfile/.env 等配置文件中的明文密码与不安全项。",
    "enable_specialized_security": "越权访问、不安全文件上传、业务逻辑风险、日志脱敏等专项。",
    "enable_diff_audit": "仅对 git diff 变更文件做增量安全扫描（需完整 git 历史）。",
    "enable_coverage_audit": "结合 coverage.xml/lcov 标记低覆盖率区域，提示人工复核。",
    "enable_runtime_audit": "输出 DAST/IAST 动态测试建议与运行时安全盲区提示（非真实渗透）。",
    "enable_manual_checklist": "生成人工深度审计清单 Markdown，供安全人员线下复核。",
}

TOOLS_DOC = """
**工具与路径说明**

- 路径均相对于 Skill 仓库根目录（Docker 内为 `/skill`），或填写绝对路径。
- 留空表示使用内置默认配置。
- 修改后保存，下次审计任务生效。
"""

LINTER_LANGUAGE_OPTIONS = [
    {"value": "", "label": "留空 — 自动检测"},
    {"value": "Python", "label": "Python"},
    {"value": "Javascript", "label": "Javascript"},
    {"value": "Typescript", "label": "Typescript"},
    {"value": "Go", "label": "Go"},
    {"value": "Java", "label": "Java"},
    {"value": "Python,Javascript", "label": "Python + Javascript"},
]

AUDIT_GROUPS = [
    {
        "id": "general",
        "label": "通用设置",
        "doc": "控制审计预设、目标目录与报告格式等全局行为。",
        "fields": [
            {
                "key": "audit_preset",
                "label": "审计预设",
                "type": "select",
                "options": [
                    {"value": "custom", "label": "自定义（按下方开关）"},
                    {"value": "full", "label": "全部模块"},
                    {"value": "minimal", "label": "最小门禁"},
                    {"value": "security", "label": "安全专项"},
                    {"value": "python", "label": "Python 聚焦"},
                    {"value": "ci-fast", "label": "CI 快速"},
                ],
                "default": "security",
                "hint": "非 custom/full 时，预设会覆盖下方部分模块开关（与 GitHub Action 行为一致）",
            },
            {
                "key": "working_directory",
                "label": "审计目标目录",
                "type": "text",
                "default": ".",
                "hint": "相对被审计仓库根路径。单体仓库填 `.`，Monorepo 可填 `packages/api` 等。",
            },
            {
                "key": "fail_on_findings",
                "label": "发现高危问题时判定失败",
                "type": "boolean",
                "default": False,
                "hint": "Web 控制台仅影响脚本 exit code，不阻断页面展示。",
            },
            {
                "key": "upload_artifacts",
                "label": "上传/保留扫描制品",
                "type": "boolean",
                "default": False,
            },
            {
                "key": "artifact_retention_days",
                "label": "制品保留天数",
                "type": "number",
                "default": 14,
                "min": 1,
                "max": 90,
            },
            {
                "key": "enable_sarif",
                "label": "生成 SARIF 报告",
                "type": "boolean",
                "default": True,
                "hint": "输出 codeaudit.sarif.json，兼容 GitHub Code Scanning。",
            },
        ],
    },
    {
        "id": "modules",
        "label": "扫描模块开关",
        "doc": "每个模块可独立开关。关闭可减少耗时；安全场景建议至少保留 gitleaks + SAST + bandit。",
        "fields": [
            {"key": "enable_gitleaks", "label": "Gitleaks 敏感密钥扫描", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_gitleaks"]},
            {"key": "enable_super_linter", "label": "Super-Linter 多语言规范检查", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_super_linter"]},
            {"key": "enable_bandit", "label": "Bandit Python 安全扫描", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_bandit"]},
            {"key": "enable_dependency_scan", "label": "依赖漏洞检测 (Trivy)", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_dependency_scan"]},
            {"key": "enable_custom_rules", "label": "自定义业务规则扫描", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_custom_rules"]},
            {"key": "enable_test_cases", "label": "自动生成并执行验收测试用例", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_test_cases"]},
            {"key": "enable_sast_patterns", "label": "SAST 词法/语法扫描", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_sast_patterns"]},
            {"key": "enable_taint_analysis", "label": "SAST 污点分析", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_taint_analysis"]},
            {"key": "enable_control_flow", "label": "SAST 控制流分析", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_control_flow"]},
            {"key": "enable_config_audit", "label": "配置文件审计", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_config_audit"]},
            {"key": "enable_specialized_security", "label": "专项安全审计", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_specialized_security"]},
            {"key": "enable_diff_audit", "label": "版本差分审计", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_diff_audit"]},
            {"key": "enable_coverage_audit", "label": "覆盖率驱动审计", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_coverage_audit"]},
            {"key": "enable_runtime_audit", "label": "DAST/IAST 运行时建议", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_runtime_audit"]},
            {"key": "enable_manual_checklist", "label": "生成人工深度审计清单", "type": "boolean", "default": True,
             "description": MODULE_DESCRIPTIONS["enable_manual_checklist"]},
        ],
    },
    {
        "id": "tools",
        "label": "工具与路径",
        "doc": TOOLS_DOC.strip(),
        "fields": [
            {
                "key": "super_linter_languages",
                "label": "Super-Linter 语言列表",
                "type": "select",
                "default": "",
                "options": LINTER_LANGUAGE_OPTIONS,
                "allow_custom": True,
                "placeholder": "或手动输入：Python,Javascript",
                "hint": "逗号分隔语言名；留空由 Super-Linter 自动检测。",
            },
            {
                "key": "gitleaks_config",
                "label": "Gitleaks 配置文件路径",
                "type": "path",
                "default": "",
                "placeholder": "config/gitleaks.toml",
                "hint": "Toml 格式的 gitleaks 规则文件。留空使用内置 config/gitleaks.toml。",
            },
            {
                "key": "custom_rules_path",
                "label": "自定义业务规则文件路径",
                "type": "path",
                "default": "",
                "placeholder": "config/custom-rules/business-rules.yaml",
                "hint": "YAML 业务规则，与 enable_custom_rules 配合使用。",
            },
            {
                "key": "ignore_paths_file",
                "label": "额外忽略路径配置文件",
                "type": "path",
                "default": "",
                "placeholder": "config/ignore-paths.txt",
                "hint": "每行一个 glob 路径，扫描时跳过匹配文件。",
            },
        ],
    },
    {
        "id": "web",
        "label": "Web 控制台",
        "doc": "控制 Web 界面行为，与 GitHub Action 参数独立。",
        "fields": [
            {
                "key": "https_proxy",
                "label": "HTTPS 代理（访问 GitHub）",
                "type": "text",
                "default": "",
                "placeholder": "http://host.docker.internal:7890",
                "hint": "Docker 内 clone/API 失败时填写。Windows 常用 host.docker.internal 指向本机代理端口。",
            },
            {
                "key": "http_proxy",
                "label": "HTTP 代理（可选）",
                "type": "text",
                "default": "",
                "placeholder": "留空则与 HTTPS 代理相同",
            },
            {
                "key": "job_retention_hours",
                "label": "文档本地保留时长（小时）",
                "type": "number",
                "default": 72,
                "min": 1,
                "max": 720,
                "hint": "到期后自动清理任务与文档",
            },
            {
                "key": "auto_send_telegram",
                "label": "审计完成后自动推送 Telegram",
                "type": "boolean",
                "default": False,
                "hint": "关闭时需在任务详情页手动发送",
            },
        ],
    },
]

TELEGRAM_REPORT_FILES = [
    {"filename": "audit-summary.json", "label": "审计摘要 JSON", "default": True},
    {"filename": "audit-bugs.md", "label": "Bug 报告 Markdown", "default": True},
    {"filename": "test-cases.md", "label": "验收测试用例 Markdown", "default": True},
    {"filename": "test-cases-functional.md", "label": "功能测试用例 Markdown", "default": True},
    {"filename": "test-cases-api.md", "label": "接口测试用例 Markdown", "default": True},
    {"filename": "test-cases-report.json", "label": "用例执行结果 JSON", "default": False},
    {"filename": "test-cases-functional-report.json", "label": "功能用例执行结果 JSON", "default": False},
    {"filename": "test-cases-api-report.json", "label": "接口用例执行结果 JSON", "default": False},
    {"filename": "test-cases-execution.log", "label": "用例执行日志", "default": False},
    {"filename": "manual-audit-checklist.md", "label": "需求/人工审计清单", "default": True},
    {"filename": "audit-logs-combined.txt", "label": "合并运行日志", "default": True},
]


def get_default_send_report_files() -> dict:
    return {item["filename"]: item.get("default", False) for item in TELEGRAM_REPORT_FILES}


def migrate_send_report_files(stored: dict) -> dict:
    """从旧版布尔开关迁移到 send_report_files。"""
    if isinstance(stored.get("send_report_files"), dict) and stored["send_report_files"]:
        defaults = get_default_send_report_files()
        merged = {**defaults, **stored["send_report_files"]}
        return {k: bool(v) for k, v in merged.items()}

    files = get_default_send_report_files()
    if stored.get("send_test_cases_md") is False:
        for name in ("test-cases.md", "test-cases-functional.md", "test-cases-api.md"):
            files[name] = False
    if stored.get("send_bug_report_md") is False:
        files["audit-bugs.md"] = False
    if stored.get("send_audit_logs") is False:
        files["audit-logs-combined.txt"] = False
    if stored.get("send_requirements_checklist") is False:
        files["manual-audit-checklist.md"] = False
    return files


TELEGRAM_GROUPS = [
    {
        "id": "telegram_connection",
        "label": "Telegram 连接",
        "doc": "配置 Bot 凭证；也可通过环境变量 TG_BOT_TOKEN / TG_CHAT_ID 注入。",
        "fields": [
            {"key": "enabled", "label": "启用 Telegram 集成", "type": "boolean", "default": True},
            {"key": "bot_token", "label": "Bot Token", "type": "password", "default": ""},
            {"key": "chat_id", "label": "Chat ID", "type": "text", "default": "", "placeholder": "-100xxxxxxxxxx"},
            {"key": "bot_username", "label": "Bot 用户名", "type": "text", "default": "", "placeholder": "@your_bot"},
        ],
    },
    {
        "id": "telegram_send",
        "label": "Telegram 推送内容",
        "doc": "文字摘要与一键发送报告时包含的文件；未勾选的文件不会发送到 Telegram 群。",
        "fields": [
            {"key": "send_summary_message", "label": "发送文字摘要", "type": "boolean", "default": True},
            {
                "key": "send_report_files",
                "label": "一键发送报告文件",
                "type": "file_checklist",
                "default": None,
                "description": "任务详情页「发送 TG」与审计完成自动推送时，仅发送已勾选的文件。",
            },
            {
                "key": "max_log_size_kb",
                "label": "日志大小上限（KB）",
                "type": "number",
                "default": 5000,
                "min": 100,
                "max": 50000,
            },
        ],
    },
]

ENV_MAP = {
    "working_directory": "INPUT_WORKING_DIRECTORY",
    "fail_on_findings": "INPUT_FAIL_ON_FINDINGS",
    "upload_artifacts": "INPUT_UPLOAD_ARTIFACTS",
    "artifact_retention_days": "INPUT_ARTIFACT_RETENTION_DAYS",
    "audit_preset": "INPUT_AUDIT_PRESET",
    "enable_sarif": "INPUT_ENABLE_SARIF",
    "enable_gitleaks": "INPUT_ENABLE_GITLEAKS",
    "enable_super_linter": "INPUT_ENABLE_SUPER_LINTER",
    "enable_bandit": "INPUT_ENABLE_BANDIT",
    "enable_dependency_scan": "INPUT_ENABLE_DEPENDENCY_SCAN",
    "enable_custom_rules": "INPUT_ENABLE_CUSTOM_RULES",
    "enable_test_cases": "INPUT_ENABLE_TEST_CASES",
    "enable_sast_patterns": "INPUT_ENABLE_SAST_PATTERNS",
    "enable_taint_analysis": "INPUT_ENABLE_TAINT_ANALYSIS",
    "enable_control_flow": "INPUT_ENABLE_CONTROL_FLOW",
    "enable_config_audit": "INPUT_ENABLE_CONFIG_AUDIT",
    "enable_specialized_security": "INPUT_ENABLE_SPECIALIZED_SECURITY",
    "enable_diff_audit": "INPUT_ENABLE_DIFF_AUDIT",
    "enable_coverage_audit": "INPUT_ENABLE_COVERAGE_AUDIT",
    "enable_runtime_audit": "INPUT_ENABLE_RUNTIME_AUDIT",
    "enable_manual_checklist": "INPUT_ENABLE_MANUAL_CHECKLIST",
    "super_linter_languages": "INPUT_SUPER_LINTER_LANGUAGES",
    "gitleaks_config": "INPUT_GITLEAKS_CONFIG",
    "custom_rules_path": "INPUT_CUSTOM_RULES_PATH",
    "ignore_paths_file": "INPUT_IGNORE_PATHS_FILE",
}


def get_tool_path_suggestions() -> dict:
    root = Path(settings.skill_path)
    config = root / "config"
    suggestions = {
        "gitleaks_config": [],
        "custom_rules_path": [],
        "ignore_paths_file": [],
    }
    if (config / "gitleaks.toml").exists():
        suggestions["gitleaks_config"].append("config/gitleaks.toml")
    rules = config / "custom-rules"
    if rules.exists():
        for f in rules.glob("*.yaml"):
            suggestions["custom_rules_path"].append(str(f.relative_to(root)).replace("\\", "/"))
    if (config / "ignore-paths.txt").exists():
        suggestions["ignore_paths_file"].append("config/ignore-paths.txt")
    return suggestions


def _field_defaults(groups: list) -> dict:
    out = {}
    for g in groups:
        for f in g["fields"]:
            out[f["key"]] = f.get("default")
    return out


def get_default_audit_settings() -> dict:
    return _field_defaults(AUDIT_GROUPS)


def get_default_telegram_settings() -> dict:
    defaults = _field_defaults(TELEGRAM_GROUPS)
    defaults["send_report_files"] = get_default_send_report_files()
    return defaults


def load_preset_modules(preset: str) -> dict:
    if preset in ("", "full", "custom"):
        return {}
    path = Path(settings.skill_path) / "config" / "audit-presets.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    bundle = (data.get("presets") or {}).get(preset) or {}
    return bundle.get("modules") or {}


def list_presets_meta() -> list[dict]:
    path = Path(settings.skill_path) / "config" / "audit-presets.yaml"
    if not path.exists():
        return [{"id": k, "label": v, "description": ""} for k, v in PRESET_LABELS.items()]
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    presets = data.get("presets") or {}
    result = [{"id": "custom", "label": PRESET_LABELS["custom"], "description": "完全按下方开关执行"}]
    for pid, pinfo in presets.items():
        result.append(
            {
                "id": pid,
                "label": PRESET_LABELS.get(pid, pid),
                "description": pinfo.get("description", ""),
            }
        )
    return result
