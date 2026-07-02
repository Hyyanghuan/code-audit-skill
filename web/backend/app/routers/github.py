from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas import GitHubBranchesRequest, GitHubReposRequest, GitHubReposResponse, RepoInfo
from app.services import github_client

router = APIRouter(prefix="/github", tags=["github"])


@router.post("/repos", response_model=GitHubReposResponse)
async def list_repos(body: GitHubReposRequest, _: str = Depends(get_current_user)):
    try:
        repos, total = await github_client.list_user_repos(
            body.token, body.page, body.per_page
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    items = [
        RepoInfo(
            id=r["id"],
            full_name=r["full_name"],
            name=r["name"],
            private=r.get("private", False),
            default_branch=r.get("default_branch", "main"),
            description=r.get("description"),
            html_url=r.get("html_url", ""),
        )
        for r in repos
    ]
    return GitHubReposResponse(repos=items, total=total)


@router.post("/branches")
async def list_branches(body: GitHubBranchesRequest, _: str = Depends(get_current_user)):
    try:
        branches = await github_client.list_repo_branches(body.token, body.repo_full_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"branches": branches, "total": len(branches)}
