"""审计流水线步骤跟踪 — 写入 jobs/{id}/pipeline.json 供前端实时展示。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_lock = Lock()

STEP_DEFINITIONS = [
    {"id": "clone", "label": "同步 GitHub 仓库", "phase": "准备"},
    {"id": "init", "label": "初始化审计环境", "phase": "准备", "script": "init.sh"},
    {"id": "detect_languages", "label": "检测项目语言与结构", "phase": "准备", "script": "detect-languages.sh"},
    {"id": "gitleaks", "label": "Gitleaks 敏感密钥扫描", "phase": "扫描", "script": "run-gitleaks.sh", "module": "gitleaks"},
    {"id": "super_linter", "label": "Super-Linter 规范检查", "phase": "扫描", "script": "run-super-linter.sh", "module": "super_linter", "enable_key": "enable_super_linter"},
    {"id": "bandit", "label": "Bandit Python 安全扫描", "phase": "扫描", "script": "run-bandit.sh", "module": "bandit"},
    {"id": "dependency_scan", "label": "Trivy 依赖漏洞扫描", "phase": "扫描", "script": "run-dependency-scan.sh", "module": "dependency_scan"},
    {"id": "custom_rules", "label": "自定义业务规则扫描", "phase": "扫描", "script": "run-custom-rules.sh", "module": "custom_rules"},
    {"id": "sast_patterns", "label": "SAST 词法/语法扫描", "phase": "引擎", "script": "run-audit-module.sh", "module": "sast_patterns", "audit_module": "sast_patterns"},
    {"id": "taint_analysis", "label": "SAST 污点分析", "phase": "引擎", "script": "run-audit-module.sh", "module": "taint_analysis", "audit_module": "taint_analysis"},
    {"id": "control_flow", "label": "SAST 控制流分析", "phase": "引擎", "script": "run-audit-module.sh", "module": "control_flow", "audit_module": "control_flow"},
    {"id": "config_audit", "label": "配置文件审计", "phase": "引擎", "script": "run-audit-module.sh", "module": "config_audit", "audit_module": "config_audit"},
    {"id": "specialized_security", "label": "专项安全审计", "phase": "引擎", "script": "run-audit-module.sh", "module": "specialized_security", "audit_module": "specialized_security"},
    {"id": "diff_audit", "label": "版本差分审计", "phase": "引擎", "script": "run-audit-module.sh", "module": "diff_audit", "audit_module": "diff_audit"},
    {"id": "coverage_audit", "label": "覆盖率驱动审计", "phase": "引擎", "script": "run-audit-module.sh", "module": "coverage_audit", "audit_module": "coverage_audit"},
    {"id": "runtime_audit", "label": "DAST/IAST 运行时建议", "phase": "引擎", "script": "run-audit-module.sh", "module": "runtime_audit", "audit_module": "runtime_audit"},
    {"id": "manual_checklist", "label": "人工深度审计清单", "phase": "引擎", "script": "run-audit-module.sh", "module": "manual_checklist", "audit_module": "manual_checklist"},
    {"id": "finalize", "label": "汇总审计结果", "phase": "报告", "script": "finalize-results.sh"},
    {"id": "generate_bug_report", "label": "生成 Bug 报告", "phase": "报告", "script": "generate-bug-report.sh"},
    {"id": "generate_test_cases", "label": "生成验收测试用例", "phase": "报告", "script": "generate-test-cases.sh", "enable_key": "enable_test_cases"},
    {"id": "execute_test_cases", "label": "执行验收测试用例", "phase": "报告", "script": "execute-test-cases.sh", "enable_key": "enable_test_cases"},
]

MODULE_ENABLE_MAP = {
    "gitleaks": "enable_gitleaks",
    "super_linter": "enable_super_linter",
    "bandit": "enable_bandit",
    "dependency_scan": "enable_dependency_scan",
    "custom_rules": "enable_custom_rules",
    "sast_patterns": "enable_sast_patterns",
    "taint_analysis": "enable_taint_analysis",
    "control_flow": "enable_control_flow",
    "config_audit": "enable_config_audit",
    "specialized_security": "enable_specialized_security",
    "diff_audit": "enable_diff_audit",
    "coverage_audit": "enable_coverage_audit",
    "runtime_audit": "enable_runtime_audit",
    "manual_checklist": "enable_manual_checklist",
}


def pipeline_path(job_id: str, data_dir: str) -> Path:
    p = Path(data_dir) / "jobs" / job_id / "pipeline.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stream_path(job_id: str, data_dir: str) -> Path:
    p = Path(data_dir) / "jobs" / job_id / "stream.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def step_log_path(job_id: str, data_dir: str, step_id: str) -> Path:
    p = Path(data_dir) / "jobs" / job_id / "step-logs" / f"{step_id}.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append_stream(job_id: str, data_dir: str, line: str) -> None:
    path = stream_path(job_id, data_dir)
    with _lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")


def read_stream(job_id: str, data_dir: str, offset: int = 0) -> tuple[str, int]:
    path = stream_path(job_id, data_dir)
    if not path.exists():
        return "", 0
    text = path.read_text(encoding="utf-8", errors="replace")
    if offset >= len(text):
        return "", len(text)
    return text[offset:], len(text)


class PipelineTracker:
    def __init__(self, job_id: str, data_dir: str):
        self.job_id = job_id
        self.data_dir = data_dir
        self.path = pipeline_path(job_id, data_dir)
        sp = stream_path(job_id, data_dir)
        if sp.exists():
            sp.unlink()
        append_stream(job_id, data_dir, f"[{ _now() }] 审计流水线初始化")
        self.data = {
            "job_id": job_id,
            "updated_at": _now(),
            "current_step": None,
            "steps": [
                {**step, "status": "pending", "message": "", "findings": 0,
                 "started_at": None, "finished_at": None,
                 "stdout": "", "stderr": "", "error_detail": None, "log_file": None}
                for step in STEP_DEFINITIONS
            ],
        }
        self._save()

    def _save(self) -> None:
        self.data["updated_at"] = _now()
        with _lock:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _step(self, step_id: str) -> dict:
        for s in self.data["steps"]:
            if s["id"] == step_id:
                return s
        raise KeyError(step_id)

    def start(self, step_id: str) -> None:
        s = self._step(step_id)
        s["status"] = "running"
        s["started_at"] = _now()
        s["message"] = "执行中…"
        self.data["current_step"] = step_id
        append_stream(self.job_id, self.data_dir, f"\n>>> [{s['label']}] 开始执行…")
        self._save()

    def skip(self, step_id: str, reason: str) -> None:
        s = self._step(step_id)
        s["status"] = "skipped"
        s["message"] = reason
        s["finished_at"] = _now()
        append_stream(self.job_id, self.data_dir, f"--- [{s['label']}] 已跳过: {reason}")
        self._save()

    def _write_step_log(
        self,
        step_id: str,
        message: str,
        stdout: str,
        stderr: str,
        error_detail: str | None,
    ) -> None:
        parts: list[str] = []
        if message:
            parts.append(f"=== {message} ===")
        if stdout:
            parts.append(f"--- stdout ---\n{stdout.rstrip()}")
        if stderr:
            parts.append(f"--- stderr ---\n{stderr.rstrip()}")
        if error_detail:
            parts.append(f"--- error ---\n{error_detail.rstrip()}")
        if not parts:
            return
        path = step_log_path(self.job_id, self.data_dir, step_id)
        with _lock:
            path.write_text("\n\n".join(parts), encoding="utf-8")

    def finish(
        self,
        step_id: str,
        status: str,
        message: str = "",
        findings: int = 0,
        stdout: str = "",
        stderr: str = "",
        error_detail: str | None = None,
        log_file: str | None = None,
    ) -> None:
        s = self._step(step_id)
        s["status"] = status
        s["message"] = message
        s["findings"] = findings
        s["finished_at"] = _now()
        full_stdout = stdout or ""
        full_stderr = stderr or ""
        self._write_step_log(step_id, message, full_stdout, full_stderr, error_detail)
        s["stdout"] = full_stdout[-8000:]
        s["stderr"] = full_stderr[-8000:]
        s["error_detail"] = error_detail
        s["log_file"] = log_file
        if stdout:
            append_stream(self.job_id, self.data_dir, stdout.rstrip())
        if stderr:
            append_stream(self.job_id, self.data_dir, stderr.rstrip())
        append_stream(
            self.job_id,
            self.data_dir,
            f"<<< [{s['label']}] {status.upper()} — {message or status}",
        )
        if self.data["current_step"] == step_id:
            self.data["current_step"] = None
        self._save()

    def fail_job(self, step_id: str, error: str, stderr: str = "") -> None:
        self.finish(step_id, "error", error, stderr=stderr, error_detail=error)


def load_pipeline(job_id: str, data_dir: str) -> dict | None:
    path = pipeline_path(job_id, data_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
