from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    skill_path: str = "/skill"
    data_dir: str = "/data"
    jwt_secret: str = "code-audit-web-dev-secret-change-in-prod"
    jwt_expire_hours: int = 24
    job_retention_hours: int = 72
    cors_origins: str = "*"

    # 写死账户（按需求）
    auth_username: str = "2634564881@qq.com"
    auth_password: str = "Admin123"

    class Config:
        env_prefix = "WEB_"


settings = Settings()
