"""将 /skill/scripts 复制到可写目录并统一 LF（Windows 挂载 CRLF 兼容）。"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from app.config import settings

CACHE_DIR = Path(settings.data_dir) / "skill-scripts-cache"
STAMP_FILE = CACHE_DIR / ".source-stamp"


def _source_stamp(src: Path) -> str:
    parts: list[str] = []
    for f in sorted(src.glob("*")):
        if f.is_file():
            parts.append(f"{f.name}:{f.stat().st_mtime_ns}:{f.stat().st_size}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def get_normalized_scripts_dir(force: bool = False) -> Path:
    src = Path(settings.skill_path) / "scripts"
    if not src.is_dir():
        raise FileNotFoundError(f"Skill scripts 目录不存在: {src}")

    stamp = _source_stamp(src)
    if not force and CACHE_DIR.is_dir() and STAMP_FILE.exists():
        if STAMP_FILE.read_text(encoding="utf-8").strip() == stamp:
            return CACHE_DIR

    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        if not item.is_file():
            continue
        data = item.read_bytes()
        if item.suffix == ".sh" or item.name.endswith(".sh"):
            data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        (CACHE_DIR / item.name).write_bytes(data)

    for sh in CACHE_DIR.glob("*.sh"):
        sh.chmod(sh.stat().st_mode | 0o111)

    STAMP_FILE.write_text(stamp, encoding="utf-8")
    return CACHE_DIR


def scripts_dir_for_job(job_id: str) -> Path:
    """每任务独立副本，避免并发写冲突。"""
    base = get_normalized_scripts_dir()
    dst = Path(settings.data_dir) / "tmp" / f"scripts-run-{job_id}"
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(base, dst)
    return dst
