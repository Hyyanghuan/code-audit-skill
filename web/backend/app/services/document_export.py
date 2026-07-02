import csv
import io
import json
from pathlib import Path

from openpyxl import Workbook


PREVIEWABLE = {".md", ".txt", ".json", ".log", ".yaml", ".yml", ".toml"}


def list_documents(artifacts_dir: Path) -> list[dict]:
    if not artifacts_dir.exists():
        return []
    docs = []
    for f in sorted(artifacts_dir.iterdir()):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        docs.append(
            {
                "name": f.name,
                "size": f.stat().st_size,
                "ext": ext.lstrip("."),
                "previewable": ext in PREVIEWABLE,
            }
        )
    return docs


def read_preview(artifacts_dir: Path, filename: str) -> str:
    path = _safe_path(artifacts_dir, filename)
    content = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            return json.dumps(json.loads(content), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    return content


def export_document(artifacts_dir: Path, filename: str, fmt: str) -> tuple[bytes, str, str]:
    path = _safe_path(artifacts_dir, filename)
    fmt = fmt.lower()
    stem = path.stem

    if fmt == "md":
        if path.suffix.lower() == ".md":
            data = path.read_bytes()
            return data, f"{stem}.md", "text/markdown; charset=utf-8"
        data = _json_to_markdown(path).encode("utf-8")
        return data, f"{stem}.md", "text/markdown; charset=utf-8"

    if fmt == "csv":
        data = _to_csv(path).encode("utf-8-sig")
        return data, f"{stem}.csv", "text/csv; charset=utf-8"

    if fmt in ("xlsx", "excel"):
        data = _to_xlsx(path)
        return (
            data,
            f"{stem}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    raise ValueError(f"不支持的格式: {fmt}")


def _safe_path(artifacts_dir: Path, filename: str) -> Path:
    path = (artifacts_dir / filename).resolve()
    if not str(path).startswith(str(artifacts_dir.resolve())):
        raise ValueError("非法文件路径")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(filename)
    return path


def _json_to_markdown(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    lines = [f"# {path.name}", ""]
    if isinstance(data, dict) and "modules" in data:
        lines.append(f"- audit_status: {data.get('audit_status')}")
        lines.append(f"- total_findings: {data.get('total_findings')}")
        lines.append("")
        for mod, info in data.get("modules", {}).items():
            lines.append(f"## {mod}")
            lines.append(f"- status: {info.get('status')}")
            lines.append(f"- findings: {info.get('findings')}")
            for item in info.get("items", [])[:50]:
                lines.append(f"  - {item}")
            lines.append("")
    else:
        lines.append("```json")
        lines.append(json.dumps(data, indent=2, ensure_ascii=False))
        lines.append("```")
    return "\n".join(lines)


def _flatten_json(data, prefix="") -> list[dict]:
    rows: list[dict] = []

    def walk(obj, p=""):
        if isinstance(obj, dict):
            if "items" in obj and isinstance(obj["items"], list):
                for i, item in enumerate(obj["items"]):
                    if isinstance(item, dict):
                        row = {"_path": p, "_index": i}
                        row.update({k: v for k, v in item.items() if not isinstance(v, (dict, list))})
                        rows.append(row)
                    else:
                        rows.append({"_path": p, "_index": i, "value": str(item)})
            else:
                for k, v in obj.items():
                    walk(v, f"{p}.{k}" if p else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{p}[{i}]")

    walk(data, prefix)
    if not rows and isinstance(data, dict):
        rows.append({k: v for k, v in data.items() if not isinstance(v, (dict, list))})
    return rows


def _to_csv(path: Path) -> str:
    ext = path.suffix.lower()
    buf = io.StringIO()
    if ext == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = _flatten_json(data)
        if not rows:
            writer = csv.writer(buf)
            writer.writerow(["key", "value"])
            for k, v in data.items() if isinstance(data, dict) else []:
                writer.writerow([k, v])
        else:
            fieldnames = sorted({k for r in rows for k in r.keys()})
            writer = csv.DictWriter(buf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    elif ext == ".md":
        writer = csv.writer(buf)
        writer.writerow(["line_no", "content"])
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            writer.writerow([i, line])
    else:
        writer = csv.writer(buf)
        writer.writerow(["content"])
        writer.writerow([path.read_text(encoding="utf-8", errors="replace")])
    return buf.getvalue()


def _to_xlsx(path: Path) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "data"
    ext = path.suffix.lower()
    if ext == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = _flatten_json(data)
        if rows:
            headers = sorted({k for r in rows for k in r.keys()})
            ws.append(headers)
            for row in rows:
                ws.append([row.get(h, "") for h in headers])
        elif isinstance(data, dict):
            ws.append(["key", "value"])
            for k, v in data.items():
                if not isinstance(v, (dict, list)):
                    ws.append([k, v])
    elif ext == ".md":
        ws.append(["line_no", "content"])
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            ws.append([i, line])
    else:
        ws.append(["content"])
        ws.append([path.read_text(encoding="utf-8", errors="replace")[:32000]])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
