import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.database import create_job, get_job, update_job
from app.services.audit_settings import audit_settings_to_env, get_audit_settings
from app.services.job_control import (
    AuditCancelled,
    clear_cancel,
    ensure_not_cancelled,
    is_cancelled,
    kill_job_process,
    register_process,
    request_cancel,
    unregister_process,
)
from app.services.network import apply_proxy_env
from app.services.pipeline_tracker import MODULE_ENABLE_MAP, PipelineTracker
from app.services.repo_fetch import repo_cache_dir, sync_repository
from app.services.script_normalizer import scripts_dir_for_job
from app.settings_catalog import load_preset_modules


def _job_dir(job_id: str) -> Path:
    return Path(settings.data_dir) / "jobs" / job_id


def _job_artifacts_dir(job_id: str) -> Path:
    return _job_dir(job_id) / "artifacts"


def _audit_tmp(job_id: str) -> Path:
    return Path(settings.data_dir) / "tmp" / f"code-audit-{job_id}"


def _is_enabled(cfg: dict, enable_key: str | None, step_id: str) -> bool:
    if not enable_key:
        enable_key = MODULE_ENABLE_MAP.get(step_id)
    if not enable_key:
        return True
    preset = str(cfg.get("audit_preset", "security"))
    val = cfg.get(enable_key, True)
    if preset not in ("full", "custom", ""):
        overrides = load_preset_modules(preset)
        yaml_key = enable_key
        if yaml_key in overrides:
            return bool(overrides[yaml_key])
    return bool(val)


def _read_module_result(job_id: str, module: str) -> dict:
    path = _audit_tmp(job_id) / "results" / f"{module}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def start_audit_job(token: str, repo_full_name: str, branch: str) -> str:
    cfg = get_audit_settings()
    preset = str(cfg.get("audit_preset", "security"))
    job_id = f"web-{uuid.uuid4().hex[:12]}"
    create_job(job_id, repo_full_name, branch, preset)
    update_job(job_id, status="queued")
    clear_cancel(job_id)

    import threading

    threading.Thread(
        target=_run_audit_sync,
        args=(job_id, token, repo_full_name, branch),
        daemon=True,
    ).start()
    return job_id


def cancel_audit_job(job_id: str) -> bool:
    job = get_job(job_id)
    if not job:
        return False
    if job["status"] not in ("running", "queued"):
        return False
    request_cancel(job_id)
    kill_job_process(job_id)
    if job["status"] == "queued":
        update_job(
            job_id,
            status="cancelled",
            error_message="用户已取消审计（排队中）",
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    return True


def _run_bash(script: str, env: dict, job_id: str, timeout: int = 1800) -> subprocess.CompletedProcess:
    ensure_not_cancelled(job_id)
    script_path = Path(script)
    if script_path.suffix == ".sh" and script_path.exists():
        raw = script_path.read_bytes()
        clean = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if clean != raw:
            script_path.write_bytes(clean)
    proc = subprocess.Popen(
        ["bash", str(script_path)],
        env=env,
        cwd=str(script_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    register_process(job_id, proc)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        ensure_not_cancelled(job_id)
        return subprocess.CompletedProcess(
            args=proc.args,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired:
        kill_job_process(job_id)
        proc.kill()
        proc.communicate()
        raise
    finally:
        unregister_process(job_id)


def _handle_cancelled(job_id: str, tracker: PipelineTracker | None, step_id: str | None = None) -> None:
    msg = "用户已取消审计"
    if tracker and step_id:
        try:
            tracker.fail_job(step_id, msg, msg)
        except KeyError:
            pass
    elif tracker and tracker.data.get("current_step"):
        try:
            tracker.fail_job(tracker.data["current_step"], msg, msg)
        except KeyError:
            pass
    update_job(
        job_id,
        status="cancelled",
        error_message=msg,
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
    clear_cancel(job_id)


def _run_audit_sync(job_id: str, token: str, repo_full_name: str, branch: str) -> None:
    cache_path = repo_cache_dir(repo_full_name, branch)
    artifacts_dst = _job_artifacts_dir(job_id)
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    audit_cfg = get_audit_settings()
    tracker = PipelineTracker(job_id, settings.data_dir)

    env_base: dict[str, str] = {}
    try:
        if is_cancelled(job_id):
            update_job(job_id, status="cancelled", error_message="用户已取消审计（排队中）",
                       finished_at=datetime.now(timezone.utc).isoformat())
            clear_cancel(job_id)
            return

        update_job(job_id, status="running")

        tracker.start("clone")
        try:
            action, msg, sync_log = sync_repository(token, repo_full_name, branch, cache_path)
            status = "skipped" if action == "skip" else "success"
            tracker.finish("clone", status, f"{msg}（操作: {action}）", stdout=sync_log)
        except subprocess.TimeoutExpired:
            tracker.fail_job("clone", "同步仓库超时（>10分钟）")
            raise
        except RuntimeError as exc:
            tracker.fail_job("clone", str(exc)[:800], str(exc))
            raise

        ensure_not_cancelled(job_id)

        work_subdir = str(audit_cfg.get("working_directory") or ".").strip() or "."
        if work_subdir != "." and not (cache_path / work_subdir).exists():
            raise FileNotFoundError(f"审计目录不存在: {work_subdir}")

        env_base = apply_proxy_env({
            **os.environ,
            "GITHUB_WORKSPACE": str(cache_path),
            "GITHUB_ACTION_PATH": settings.skill_path,
            "GITHUB_RUN_ID": job_id,
            "RUNNER_TEMP": str(Path(settings.data_dir) / "tmp"),
            "GITHUB_REPOSITORY": repo_full_name,
            "GITHUB_REF": f"refs/heads/{branch}",
            "GITHUB_SHA": "web-audit",
            "GITHUB_EVENT_NAME": "web",
            **audit_settings_to_env(audit_cfg),
            "INPUT_ENABLE_TELEGRAM": "false",
        })

        scripts = scripts_dir_for_job(job_id)

        def run_step(step_id: str, script_name: str, enable_key: str | None = None, extra_env: dict | None = None):
            ensure_not_cancelled(job_id)
            if enable_key is None:
                enable_key = MODULE_ENABLE_MAP.get(step_id)
            if enable_key and not _is_enabled(audit_cfg, enable_key, step_id):
                tracker.skip(step_id, "模块已在配置中关闭")
                return True
            tracker.start(step_id)
            env = {**env_base, **(extra_env or {})}
            try:
                cp = _run_bash(str(scripts / script_name), env, job_id)
            except AuditCancelled:
                raise
            except subprocess.TimeoutExpired:
                tracker.fail_job(step_id, "步骤执行超时")
                return False
            if is_cancelled(job_id):
                raise AuditCancelled("用户已取消审计")
            mod = step_id
            result = _read_module_result(job_id, mod)
            findings = int(result.get("findings", 0)) if result else 0
            status = result.get("status") if result else None
            msg = result.get("message", "") if result else ""
            log_file = result.get("log_file") if result else None

            if cp.returncode != 0 and status not in ("skipped", "success"):
                st = "error" if status == "error" else "failure"
                detail = (cp.stderr or cp.stdout or msg or "脚本返回非零")[:2000]
                tracker.finish(step_id, st, msg or "执行失败", findings, cp.stdout, cp.stderr, detail, log_file)
                return st != "error"
            if status == "skipped":
                tracker.finish(step_id, "skipped", msg or "已跳过", findings, cp.stdout, cp.stderr, log_file=log_file)
            elif status == "failure" or findings > 0:
                tracker.finish(step_id, "failure", msg or f"发现 {findings} 个问题", findings, cp.stdout, cp.stderr, log_file=log_file)
            elif status == "error":
                tracker.finish(step_id, "error", msg or "模块错误", findings, cp.stdout, cp.stderr, cp.stderr[:2000], log_file)
            else:
                tracker.finish(step_id, "success", msg or "通过", findings, cp.stdout, cp.stderr, log_file=log_file)
            return True

        run_step("init", "init.sh")
        run_step("detect_languages", "detect-languages.sh")
        run_step("gitleaks", "run-gitleaks.sh")
        if _is_enabled(audit_cfg, "enable_super_linter", "super_linter"):
            run_step("super_linter", "run-super-linter.sh", extra_env={"GITHUB_TOKEN": env_base.get("GITHUB_TOKEN", "dummy")})
        else:
            tracker.skip("super_linter", "Super-Linter 已关闭")
        run_step("bandit", "run-bandit.sh")
        run_step("dependency_scan", "run-dependency-scan.sh")
        run_step("custom_rules", "run-custom-rules.sh")

        audit_modules = [
            ("sast_patterns", "sast_patterns"),
            ("taint_analysis", "taint_analysis"),
            ("control_flow", "control_flow"),
            ("config_audit", "config_audit"),
            ("specialized_security", "specialized_security"),
            ("diff_audit", "diff_audit"),
            ("coverage_audit", "coverage_audit"),
            ("runtime_audit", "runtime_audit"),
            ("manual_checklist", "manual_checklist"),
        ]
        for step_id, mod in audit_modules:
            ensure_not_cancelled(job_id)
            ek = MODULE_ENABLE_MAP.get(step_id)
            if not _is_enabled(audit_cfg, ek, step_id):
                tracker.skip(step_id, "模块已在配置中关闭")
                continue
            tracker.start(step_id)
            env = {**env_base, "AUDIT_MODULE": mod}
            try:
                cp = _run_bash(str(scripts / "run-audit-module.sh"), env, job_id)
            except AuditCancelled:
                raise
            except subprocess.TimeoutExpired:
                tracker.fail_job(step_id, "步骤执行超时")
                continue
            if is_cancelled(job_id):
                raise AuditCancelled("用户已取消审计")
            result = _read_module_result(job_id, mod)
            findings = int(result.get("findings", 0))
            status = result.get("status", "success")
            msg = result.get("message", "")
            if status == "skipped":
                tracker.finish(step_id, "skipped", msg or "已跳过", findings, cp.stdout, cp.stderr)
            elif status in ("failure", "error") or findings > 0:
                tracker.finish(step_id, status if status in ("failure", "error") else "failure",
                               msg or f"发现 {findings} 个问题", findings, cp.stdout, cp.stderr,
                               (cp.stderr or msg)[:2000])
            else:
                tracker.finish(step_id, "success", msg or "通过", findings, cp.stdout, cp.stderr)

        ensure_not_cancelled(job_id)
        run_step("finalize", "finalize-results.sh")
        run_step("generate_bug_report", "generate-bug-report.sh")
        if _is_enabled(audit_cfg, "enable_test_cases", "generate_test_cases"):
            run_step("generate_test_cases", "generate-test-cases.sh", "enable_test_cases")
            run_step("execute_test_cases", "execute-test-cases.sh", "enable_test_cases")
        else:
            tracker.skip("generate_test_cases", "测试用例生成已关闭")
            tracker.skip("execute_test_cases", "测试用例生成已关闭")

        art_src = _audit_tmp(job_id) / "artifacts"
        if artifacts_dst.exists():
            shutil.rmtree(artifacts_dst, ignore_errors=True)
        if art_src.exists():
            shutil.copytree(art_src, artifacts_dst)
        else:
            artifacts_dst.mkdir(parents=True, exist_ok=True)
            (artifacts_dst / "audit-error.txt").write_text("未生成 artifacts", encoding="utf-8")

        audit_status = "unknown"
        total_findings = 0
        summary_path = artifacts_dst / "audit-summary.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            audit_status = summary.get("audit_status", "unknown")
            total_findings = int(summary.get("total_findings", 0))

        update_job(
            job_id,
            status="completed",
            audit_status=audit_status,
            total_findings=total_findings,
            finished_at=datetime.now(timezone.utc).isoformat(),
            artifacts_path=str(artifacts_dst),
        )
        clear_cancel(job_id)

        if audit_cfg.get("auto_send_telegram"):
            import asyncio
            from app.services.telegram_client import send_audit_documents
            asyncio.run(send_audit_documents(artifacts_dst, repo_full_name, job_id))

    except AuditCancelled:
        _handle_cancelled(job_id, tracker)
    except subprocess.CalledProcessError as exc:
        update_job(job_id, status="failed", error_message=(exc.stderr or str(exc))[:2000],
                   finished_at=datetime.now(timezone.utc).isoformat())
        clear_cancel(job_id)
    except Exception as exc:  # noqa: BLE001
        if is_cancelled(job_id):
            _handle_cancelled(job_id, tracker)
        else:
            update_job(job_id, status="failed", error_message=str(exc)[:2000],
                       finished_at=datetime.now(timezone.utc).isoformat())
            clear_cancel(job_id)
    finally:
        kill_job_process(job_id)
        unregister_process(job_id)
        run_scripts = Path(settings.data_dir) / "tmp" / f"scripts-run-{job_id}"
        shutil.rmtree(run_scripts, ignore_errors=True)
