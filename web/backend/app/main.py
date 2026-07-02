from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import audits, auth, github, settings as settings_router
from app.services.audit_settings import get_effective_retention_hours
from app.services.cleanup import cleanup_expired_jobs
from app.services.job_recovery import recover_stale_running_jobs
from app.services.script_normalizer import get_normalized_scripts_dir


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    try:
        cache = get_normalized_scripts_dir(force=True)
        print(f"[startup] skill scripts normalized -> {cache}")
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] WARN: script normalize failed: {exc}")
    cleanup_expired_jobs()
    n = recover_stale_running_jobs()
    if n:
        print(f"[startup] recovered {n} interrupted audit job(s)")
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_expired_jobs, "interval", hours=1)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Code Audit Web", version="1.0.0", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(github.router, prefix="/api")
app.include_router(audits.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "retention_hours": get_effective_retention_hours(),
    }
