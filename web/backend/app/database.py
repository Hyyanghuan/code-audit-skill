import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from app.config import settings

DB_PATH = Path(settings.data_dir) / "web.db"
_lock = threading.Lock()


def init_db() -> None:
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    (Path(settings.data_dir) / "jobs").mkdir(exist_ok=True)
    (Path(settings.data_dir) / "clones").mkdir(exist_ok=True)
    (Path(settings.data_dir) / "cancel_flags").mkdir(exist_ok=True)
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS audit_jobs (
                id TEXT PRIMARY KEY,
                repo_full_name TEXT NOT NULL,
                branch TEXT NOT NULL,
                preset TEXT NOT NULL,
                status TEXT NOT NULL,
                audit_status TEXT,
                total_findings INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TEXT NOT NULL,
                finished_at TEXT,
                artifacts_path TEXT
            );
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )


@contextmanager
def _connect():
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def create_job(
    job_id: str,
    repo_full_name: str,
    branch: str,
    preset: str,
) -> None:
    from datetime import datetime, timezone

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_jobs (id, repo_full_name, branch, preset, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (
                job_id,
                repo_full_name,
                branch,
                preset,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def update_job(job_id: str, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [job_id]
    with _connect() as conn:
        conn.execute(f"UPDATE audit_jobs SET {cols} WHERE id=?", vals)


def get_job(job_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM audit_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_jobs(limit: int = 50, branch: str | None = None) -> list[dict]:
    with _connect() as conn:
        if branch:
            rows = conn.execute(
                "SELECT * FROM audit_jobs WHERE branch = ? ORDER BY created_at DESC LIMIT ?",
                (branch, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def list_jobs_page(page: int = 1, per_page: int = 20, branch: str | None = None) -> tuple[list[dict], int]:
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page
    with _connect() as conn:
        if branch:
            total = conn.execute(
                "SELECT COUNT(*) FROM audit_jobs WHERE branch = ?",
                (branch,),
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM audit_jobs WHERE branch = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (branch, per_page, offset),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM audit_jobs").fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM audit_jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (per_page, offset),
            ).fetchall()
        return [dict(r) for r in rows], int(total)


def list_job_branches() -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT branch FROM audit_jobs ORDER BY branch ASC"
        ).fetchall()
        return [r["branch"] for r in rows if r["branch"]]


def delete_job(job_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM audit_jobs WHERE id=?", (job_id,))


def get_setting(key: str, default=None):
    with _connect() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        if not row:
            return default
        return json.loads(row["value"])


def set_setting(key: str, value) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, json.dumps(value, ensure_ascii=False)),
        )
