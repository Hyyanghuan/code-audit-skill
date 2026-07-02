"""网络与代理 — Docker 内访问 GitHub。"""
from __future__ import annotations

import os

from app.config import settings
from app.services.audit_settings import get_audit_settings


def get_proxy_url() -> str | None:
    cfg = get_audit_settings()
    for key in ("https_proxy", "http_proxy"):
        val = (cfg.get(key) or "").strip()
        if val:
            return val
    for env_key in ("WEB_HTTPS_PROXY", "WEB_HTTP_PROXY", "HTTPS_PROXY", "HTTP_PROXY"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    return None


def apply_proxy_env(env: dict[str, str]) -> dict[str, str]:
    out = {**env}
    proxy = get_proxy_url()
    if proxy:
        out["HTTPS_PROXY"] = proxy
        out["HTTP_PROXY"] = os.environ.get("HTTP_PROXY") or os.environ.get("WEB_HTTP_PROXY") or proxy
        out["ALL_PROXY"] = proxy
        no_proxy = os.environ.get("NO_PROXY", "localhost,127.0.0.1")
        out["NO_PROXY"] = no_proxy
    # 规避 curl (18) HTTP/2 stream was not closed cleanly（常见于代理或 GitHub 大文件下载）
    out["CURL_HTTP_VERSION"] = "1_1"
    return out


def proxy_hint() -> str:
    return (
        "Docker 容器无法连接 github.com:443。\n"
        "请任选一种方式：\n"
        "1. 在「系统配置 → Web 控制台」填写 HTTPS 代理，例如 http://host.docker.internal:7890\n"
        "2. 在 web/docker-compose.yml 的 backend.environment 取消注释并设置：\n"
        "   WEB_HTTPS_PROXY: http://host.docker.internal:7890\n"
        "3. 在 Docker Desktop → Settings → Resources → Proxies 配置代理\n"
        "4. 确认本机代理软件已开启并允许局域网连接"
    )


def auth_hint() -> str:
    return (
        "GitHub 认证失败（git 无法使用 Token 访问仓库）。\n"
        "请检查：\n"
        "1. 「新建审计」中填写的 GitHub Token 是否有效、未过期\n"
        "2. Classic PAT 需勾选 repo 权限；Fine-grained PAT 需授权目标仓库且 Contents=Read\n"
        "3. 组织私有库需在 Token 设置页点击 Enable SSO\n"
        "4. 若 API 能列出仓库但 git 仍失败，请配置 HTTPS 代理后重试\n"
        "5. 重新审计时在 Token 输入框粘贴最新 Token"
    )


def git_error_hint(stderr: str = "") -> str:
    err = (stderr or "").lower()
    auth_markers = (
        "username",
        "authentication failed",
        "invalid username or password",
        "401",
        "403",
        "permission denied",
        "repository not found",
    )
    network_markers = (
        "could not resolve host",
        "connection refused",
        "connection timed out",
        "failed to connect",
        "unable to access",
        "network is unreachable",
        "proxy",
        "ssl",
        "443",
    )
    if any(m in err for m in auth_markers):
        return auth_hint()
    if any(m in err for m in network_markers):
        return proxy_hint()
    if get_proxy_url():
        return auth_hint()
    return proxy_hint()


def network_hint(stderr: str = "") -> str:
    """兼容旧调用；根据 git 错误输出选择代理或认证提示。"""
    return git_error_hint(stderr)
