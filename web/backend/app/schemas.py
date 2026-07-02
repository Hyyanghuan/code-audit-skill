from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class GitHubReposRequest(BaseModel):
    token: str = Field(..., min_length=1)
    page: int = 1
    per_page: int = 30


class RepoInfo(BaseModel):
    id: int
    full_name: str
    name: str
    private: bool
    default_branch: str
    description: str | None = None
    html_url: str


class GitHubReposResponse(BaseModel):
    repos: list[RepoInfo]
    total: int


class GitHubBranchesRequest(BaseModel):
    token: str = Field(..., min_length=1)
    repo_full_name: str = Field(..., min_length=3)


class CreateAuditRequest(BaseModel):
    token: str = Field(..., min_length=1)
    repo_full_name: str = Field(..., min_length=3)
    branch: str = "main"


class RerunAuditRequest(BaseModel):
    token: str = Field(..., min_length=1)
    branch: str | None = None


class AuditJobResponse(BaseModel):
    id: str
    repo_full_name: str
    branch: str
    preset: str
    status: str
    audit_status: str | None = None
    total_findings: int = 0
    error_message: str | None = None
    created_at: str
    finished_at: str | None = None


class AuditJobListResponse(BaseModel):
    items: list[AuditJobResponse]
    total: int
    page: int
    per_page: int
    branches: list[str] = []


class AuditStreamResponse(BaseModel):
    content: str
    offset: int = 0
    running: bool = False
    current_step: str | None = None


class AuditProgressInfo(BaseModel):
    percent: int = 0
    eta_seconds: int | None = None
    completed: int = 0
    total: int = 0
    current_step: str | None = None
    current_label: str = ""


class AuditScanLogResponse(BaseModel):
    content: str
    running: bool = False
    progress: AuditProgressInfo


class DocumentInfo(BaseModel):
    name: str
    size: int
    ext: str
    previewable: bool


class AuditSettingsBody(BaseModel):
    values: dict


class ApplyPresetBody(BaseModel):
    preset: str


class TelegramSettingsBody(BaseModel):
    values: dict


class SendTelegramRequest(BaseModel):
    filenames: list[str] | None = None
    send_summary: bool | None = None
