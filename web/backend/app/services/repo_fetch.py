"""拉取 GitHub 仓库 — 存在则更新，已最新则跳过，不存在则克隆。"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

from app.config import settings
from app.services.github_client import verify_repo_access
from app.services.network import apply_proxy_env, git_error_hint


def repo_cache_dir(repo_full_name: str, branch: str) -> Path:
    safe_repo = repo_full_name.replace("/", "__")
    safe_branch = branch.replace("/", "_")
    return Path(settings.data_dir) / "clones" / safe_repo / safe_branch


def _normalize_token(token: str) -> str:
    t = (token or "").strip()
    if not t:
        raise RuntimeError(
            "GitHub Token 为空。请在「新建审计」页填写具有 repo 读权限的 Personal Access Token。"
        )
    return t


def _clean_repo_url(repo_full_name: str) -> str:
    return f"https://github.com/{repo_full_name}.git"


def _auth_repo_url_variants(token: str, repo_full_name: str) -> list[tuple[str, str]]:
    """Git 认证 URL 多种写法；Classic PAT 通常以 token 作为用户名最可靠。"""
    t = quote(_normalize_token(token), safe="")
    host = f"github.com/{repo_full_name}.git"
    return [
        ("token_as_username", f"https://{t}@{host}"),
        ("oauth2", f"https://oauth2:{t}@{host}"),
        ("x-access-token", f"https://x-access-token:{t}@{host}"),
    ]


def _git_env(token: str) -> dict[str, str]:
    return apply_proxy_env(
        {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
        }
    )


def _git_base_args(*, use_bearer_header: bool = False, token: str = "") -> list[str]:
    args = [
        "-c", "credential.helper=",
        "-c", "http.version=HTTP/1.1",
    ]
    if use_bearer_header and token:
        args.extend(["-c", f"http.extraHeader=Authorization: Bearer {_normalize_token(token)}"])
    return args


def _run_git(args: list[str], *, env: dict, cwd: Path | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
    cp = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(cwd) if cwd else None,
    )
    return cp


def _sanitize_log(text: str, token: str) -> str:
    t = (token or "").strip()
    if not t:
        return text
    out = text.replace(t, "***")
    return out.replace(quote(t, safe=""), "***")


def _format_git_log(label: str, cp: subprocess.CompletedProcess, token: str = "") -> str:
    lines = [_sanitize_log(f"$ {label}", token)]
    if cp.stdout and cp.stdout.strip():
        lines.append(_sanitize_log(cp.stdout.rstrip(), token))
    if cp.stderr and cp.stderr.strip():
        lines.append(_sanitize_log(cp.stderr.rstrip(), token))
    lines.append(f"[exit {cp.returncode}]")
    return "\n".join(lines)


def _raise_git_error(stderr: str, fallback: str = "git 操作失败") -> None:
    err = (stderr or fallback).strip()
    raise RuntimeError(f"{git_error_hint(err)}\n\n{err}")


def _local_head_sha(dest: Path, env: dict) -> str:
    cp = _run_git(["rev-parse", "HEAD"], cwd=dest, env=env, timeout=30)
    if cp.returncode != 0:
        return ""
    return cp.stdout.strip()


def _strip_remote_credentials(dest: Path, repo_full_name: str, env: dict) -> None:
    _run_git(
        ["remote", "set-url", "origin", _clean_repo_url(repo_full_name)],
        cwd=dest,
        env=env,
        timeout=30,
    )


def _run_git_with_auth_urls(
    token: str,
    repo_full_name: str,
    env: dict,
    build_args,
    *,
    cwd: Path | None = None,
    timeout: int = 600,
) -> tuple[subprocess.CompletedProcess, str]:
    """依次尝试多种 Git 认证 URL，最后尝试 Bearer Header + 无凭证 URL。"""
    logs: list[str] = []
    last_cp: subprocess.CompletedProcess | None = None

    for mode, repo_url in _auth_repo_url_variants(token, repo_full_name):
        args = build_args(repo_url, use_bearer_header=False)
        cp = _run_git(args, env=env, cwd=cwd, timeout=timeout)
        last_cp = cp
        logs.append(_format_git_log(f"git ({mode}) …", cp, token))
        if cp.returncode == 0:
            return cp, "\n\n".join(logs)

    clean_url = _clean_repo_url(repo_full_name)
    args = build_args(clean_url, use_bearer_header=True)
    cp = _run_git(args, env=env, cwd=cwd, timeout=timeout)
    last_cp = cp
    logs.append(_format_git_log("git (bearer_header) …", cp, token))
    if cp.returncode == 0:
        return cp, "\n\n".join(logs)

    assert last_cp is not None
    return last_cp, "\n\n".join(logs)


def _clone_repo(token: str, repo_full_name: str, branch: str, dest: Path, env: dict) -> str:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    def build_args(repo_url: str, *, use_bearer_header: bool) -> list[str]:
        return [
            *_git_base_args(use_bearer_header=use_bearer_header, token=token),
            "clone",
            "--depth", "1",
            "--branch", branch,
            repo_url,
            str(dest),
        ]

    cp, log = _run_git_with_auth_urls(
        token, repo_full_name, env, build_args, timeout=600,
    )
    if cp.returncode != 0:
        _raise_git_error(cp.stderr or cp.stdout, "git clone 失败")
    _strip_remote_credentials(dest, repo_full_name, env)
    return log


def _update_repo(token: str, repo_full_name: str, branch: str, dest: Path, env: dict) -> tuple[str, str]:
    clean_url = _clean_repo_url(repo_full_name)
    fetch_logs: list[str] = []

    for mode, auth_url in _auth_repo_url_variants(token, repo_full_name):
        _run_git(["remote", "set-url", "origin", auth_url], cwd=dest, env=env, timeout=30)
        fetch_args = [
            *_git_base_args(use_bearer_header=False),
            "fetch", "origin", branch, "--depth", "1",
        ]
        cp_fetch = _run_git(fetch_args, cwd=dest, env=env, timeout=300)
        fetch_logs.append(_format_git_log(f"git fetch ({mode})", cp_fetch, token))
        if cp_fetch.returncode == 0:
            break
    else:
        _run_git(["remote", "set-url", "origin", clean_url], cwd=dest, env=env, timeout=30)
        fetch_args = [
            *_git_base_args(use_bearer_header=True, token=token),
            "fetch", "origin", branch, "--depth", "1",
        ]
        cp_fetch = _run_git(fetch_args, cwd=dest, env=env, timeout=300)
        fetch_logs.append(_format_git_log("git fetch (bearer_header)", cp_fetch, token))

    _run_git(["remote", "set-url", "origin", clean_url], cwd=dest, env=env, timeout=30)

    if cp_fetch.returncode != 0:
        _raise_git_error(cp_fetch.stderr or cp_fetch.stdout, "git fetch 失败")

    cp_reset = _run_git(["reset", "--hard", "FETCH_HEAD"], cwd=dest, env=env, timeout=60)
    reset_log = _format_git_log("git reset --hard FETCH_HEAD", cp_reset, token)
    if cp_reset.returncode != 0:
        err = (cp_reset.stderr or cp_reset.stdout or "git reset 失败").strip()
        raise RuntimeError(err)
    return _local_head_sha(dest, env), "\n\n".join(fetch_logs + [reset_log])


def _ls_remote(token: str, repo_full_name: str, branch: str, env: dict) -> tuple[subprocess.CompletedProcess, str]:
    ref = f"refs/heads/{branch}"

    def build_args(repo_url: str, *, use_bearer_header: bool) -> list[str]:
        return [
            *_git_base_args(use_bearer_header=use_bearer_header, token=token),
            "ls-remote", repo_url, ref,
        ]

    return _run_git_with_auth_urls(token, repo_full_name, env, build_args, timeout=120)


def sync_repository(token: str, repo_full_name: str, branch: str, dest: Path | None = None) -> tuple[str, str, str]:
    """
    返回 (action, message, log)
    action: clone | update | skip
    """
    t = _normalize_token(token)
    verify_repo_access(t, repo_full_name)

    target = dest or repo_cache_dir(repo_full_name, branch)
    target.parent.mkdir(parents=True, exist_ok=True)
    env = _git_env(t)
    logs: list[str] = []

    if not (target / ".git").is_dir():
        logs.append(_clone_repo(t, repo_full_name, branch, target, env))
        sha = _local_head_sha(target, env)[:8]
        return "clone", f"本地无代码，已克隆分支 {branch}（{sha}）", "\n\n".join(logs)

    cp_ls, ls_log = _ls_remote(t, repo_full_name, branch, env)
    logs.append(ls_log)
    if cp_ls.returncode != 0:
        err = (cp_ls.stderr or cp_ls.stdout or "ls-remote 失败").strip()
        if "404" in err or "not found" in err.lower():
            raise RuntimeError(f"分支不存在: {branch}")
        if not _local_head_sha(target, env):
            logs.append(_clone_repo(t, repo_full_name, branch, target, env))
            sha = _local_head_sha(target, env)[:8]
            return "clone", f"仓库损坏已重新克隆分支 {branch}（{sha}）", "\n\n".join(logs)
        _raise_git_error(err, "ls-remote 失败")

    line = cp_ls.stdout.strip().splitlines()[0] if cp_ls.stdout.strip() else ""
    remote_sha = line.split()[0] if line else ""
    local_sha = _local_head_sha(target, env)
    if remote_sha and local_sha and remote_sha == local_sha:
        logs.append(f"本地 HEAD: {local_sha}\n远程 HEAD: {remote_sha}\n无需更新。")
        return "skip", f"本地代码已是最新（{local_sha[:8]}），跳过更新", "\n\n".join(logs)

    new_sha, update_log = _update_repo(t, repo_full_name, branch, target, env)
    logs.append(update_log)
    short = (new_sha or remote_sha)[:8]
    return "update", f"已更新到最新提交（{short}）", "\n\n".join(logs)


def fetch_repository(token: str, repo_full_name: str, branch: str, dest: Path) -> tuple[str, str]:
    """兼容旧接口。"""
    action, message, _log = sync_repository(token, repo_full_name, branch, dest)
    return action, message
