import httpx

from app.services.network import get_proxy_url


def _client(timeout: float = 30.0) -> httpx.AsyncClient:
    proxy = get_proxy_url()
    kwargs: dict = {"timeout": timeout}
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.AsyncClient(**kwargs)


async def list_user_repos(token: str, page: int = 1, per_page: int = 30) -> tuple[list[dict], int]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with _client() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers=headers,
            params={
                "sort": "updated",
                "direction": "desc",
                "page": page,
                "per_page": per_page,
                "affiliation": "owner,collaborator,organization_member",
            },
        )
        if resp.status_code == 401:
            raise ValueError("GitHub Token 无效或已过期")
        if resp.status_code != 200:
            raise ValueError(f"GitHub API 错误: {resp.status_code} {resp.text[:200]}")
        repos = resp.json()
        total = int(resp.headers.get("X-Total-Count", len(repos)))
        return repos, total


async def get_repo_default_branch(token: str, repo_full_name: str) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    async with _client(20.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}",
            headers=headers,
        )
        if resp.status_code != 200:
            return "main"
        return resp.json().get("default_branch", "main")


async def list_repo_branches(token: str, repo_full_name: str, per_page: int = 100) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    branches = []
    page = 1
    async with _client() as client:
        while True:
            resp = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/branches",
                headers=headers,
                params={"per_page": per_page, "page": page},
            )
            if resp.status_code == 401:
                raise ValueError("GitHub Token 无效或已过期")
            if resp.status_code == 404:
                raise ValueError(f"仓库不存在或无权限: {repo_full_name}")
            if resp.status_code != 200:
                raise ValueError(f"GitHub API 错误: {resp.status_code}")
            batch = resp.json()
            if not batch:
                break
            for b in batch:
                branches.append({
                    "name": b.get("name", ""),
                    "protected": b.get("protected", False),
                    "sha": (b.get("commit") or {}).get("sha", "")[:8],
                })
            if len(batch) < per_page:
                break
            page += 1
    return branches


def verify_repo_access(token: str, repo_full_name: str) -> None:
    """克隆前用 GitHub API 校验 Token 对目标仓库的读权限。"""
    from app.services.network import proxy_hint

    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    proxy = get_proxy_url()
    try:
        with httpx.Client(proxy=proxy, timeout=30.0) as client:
            resp = client.get(f"https://api.github.com/repos/{repo_full_name}", headers=headers)
    except httpx.RequestError as exc:
        raise RuntimeError(f"{proxy_hint()}\n\n{exc}") from exc
    if resp.status_code == 401:
        raise RuntimeError(
            "GitHub Token 无效或已过期。请在「新建审计」页重新填写 Token（Classic PAT 需 repo 权限）。"
        )
    if resp.status_code == 404:
        raise RuntimeError(
            f"仓库 {repo_full_name} 不存在，或当前 Token 无 read 权限。"
            "Fine-grained PAT 需在 Token 设置中授权该仓库。"
        )
    if resp.status_code == 403:
        try:
            payload = resp.json()
        except ValueError:
            payload = {}
        msg = str(payload.get("message", resp.text[:200]))
        if "sso" in msg.lower():
            raise RuntimeError(
                "组织仓库需 SSO 授权：GitHub → Settings → Developer settings → Personal access tokens，"
                "找到该 Token 并点击 Enable SSO。"
            )
        raise RuntimeError(f"GitHub API 拒绝访问（403）：{msg}")
    if resp.status_code != 200:
        raise RuntimeError(f"GitHub API 错误: {resp.status_code} {resp.text[:200]}")
