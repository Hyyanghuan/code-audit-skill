#!/usr/bin/env python3
"""扫描项目源码，生成功能测试用例与接口测试用例。"""
from __future__ import annotations

import os
import re
from pathlib import Path

IGNORE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
    "artifacts", "results", "coverage", ".tox", ".mypy_cache", "target",
    "vendor", ".idea", ".vscode",
}
SOURCE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".vue"}
MAX_FILES = 800
MAX_FEATURES = 120
MAX_APIS = 80

PY_API_PATTERNS = [
    (re.compile(r'@(?:app|router|api|bp)\.(get|post|put|delete|patch|route)\(\s*["\']([^"\']+)'), 1, 2),
    (re.compile(r'@app\.route\(\s*["\']([^"\']+)'), None, 1),
    (re.compile(r'path\(\s*["\']([^"\']+)["\']'), None, 1),
]
JS_API_PATTERNS = [
    (re.compile(r'(?:app|router)\.(get|post|put|delete|patch)\(\s*[`\'"]([^`\'"]+)'), 1, 2),
    (re.compile(r'\.(?:get|post|put|delete|patch)\(\s*[`\'"]([^`\'"]+)'), None, 1),
]
GO_API_PATTERNS = [
    (re.compile(r'HandleFunc\(\s*"([^"]+)"'), None, 1),
    (re.compile(r'\.(?:Get|Post|Put|Delete|Patch)\(\s*"([^"]+)"'), None, 1),
]

PY_FUNC = re.compile(r"^(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*\(", re.MULTILINE)
PY_CLASS = re.compile(r"^class\s+([a-zA-Z_]\w*)\s*[:\(]", re.MULTILINE)
JS_FUNC = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_]\w*)\s*\(", re.MULTILINE)
JS_ARROW = re.compile(r"(?:export\s+)?const\s+([a-zA-Z_]\w*)\s*=\s*(?:async\s*)?\(", re.MULTILINE)


def _should_skip_dir(name: str) -> bool:
    return name in IGNORE_DIRS or name.startswith(".")


def _iter_source_files(root: Path):
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        for fn in filenames:
            if count >= MAX_FILES:
                return
            ext = Path(fn).suffix.lower()
            if ext not in SOURCE_EXTS:
                continue
            if fn.startswith("."):
                continue
            full = Path(dirpath) / fn
            try:
                rel = full.relative_to(root).as_posix()
            except ValueError:
                continue
            count += 1
            yield rel, full, ext


def _read_text(path: Path, limit: int = 400_000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[:limit]
    except OSError:
        return ""


def _scan_apis(rel: str, text: str, ext: str) -> list[dict]:
    found: list[dict] = []
    patterns = PY_API_PATTERNS if ext == ".py" else JS_API_PATTERNS if ext in {".js", ".ts", ".jsx", ".tsx", ".vue"} else GO_API_PATTERNS
    seen = set()
    for pat, method_g, path_g in patterns:
        for m in pat.finditer(text):
            method = (m.group(method_g) or "GET").upper() if method_g else "GET"
            route = m.group(path_g).strip()
            if not route or len(route) > 200:
                continue
            key = (method, route, rel)
            if key in seen:
                continue
            seen.add(key)
            found.append({"method": method, "path": route, "file": rel})
            if len(found) >= MAX_APIS:
                return found
    return found


def _scan_features(rel: str, text: str, ext: str) -> list[dict]:
    symbols: list[dict] = []
    if ext == ".py":
        for m in PY_CLASS.finditer(text):
            name = m.group(1)
            if name.startswith("_"):
                continue
            symbols.append({"kind": "class", "name": name, "file": rel})
        for m in PY_FUNC.finditer(text):
            name = m.group(1)
            if name.startswith("_") or name in {"main", "setUp", "tearDown"}:
                continue
            symbols.append({"kind": "function", "name": name, "file": rel})
    elif ext in {".js", ".ts", ".jsx", ".tsx", ".vue"}:
        for m in JS_FUNC.finditer(text):
            symbols.append({"kind": "function", "name": m.group(1), "file": rel})
        for m in JS_ARROW.finditer(text):
            symbols.append({"kind": "function", "name": m.group(1), "file": rel})
    elif ext == ".go":
        for m in re.finditer(r"^func\s+(?:\([^)]+\)\s+)?([A-Z]\w*)\s*\(", text, re.MULTILINE):
            symbols.append({"kind": "function", "name": m.group(1), "file": rel})
    elif ext == ".java":
        for m in re.finditer(r"(?:public|protected)\s+(?:static\s+)?[\w<>,\[\]\s]+\s+(\w+)\s*\(", text):
            name = m.group(1)
            if name not in {"if", "for", "while", "switch"}:
                symbols.append({"kind": "method", "name": name, "file": rel})
    return symbols[:50]


def scan_codebase(work_dir: str | Path) -> dict:
    root = Path(work_dir).resolve()
    if not root.is_dir():
        return {"functional": [], "api": [], "stats": {"files_scanned": 0, "features": 0, "apis": 0}}

    apis: list[dict] = []
    features: list[dict] = []
    files_scanned = 0

    for rel, full, ext in _iter_source_files(root):
        files_scanned += 1
        text = _read_text(full)
        if not text.strip():
            continue
        apis.extend(_scan_apis(rel, text, ext))
        features.extend(_scan_features(rel, text, ext))
        if len(features) >= MAX_FEATURES and len(apis) >= MAX_APIS:
            break

    # 去重
    feat_seen = set()
    uniq_features = []
    for f in features:
        key = (f["file"], f["name"])
        if key in feat_seen:
            continue
        feat_seen.add(key)
        uniq_features.append(f)
        if len(uniq_features) >= MAX_FEATURES:
            break

    api_seen = set()
    uniq_apis = []
    for a in apis:
        key = (a["method"], a["path"], a["file"])
        if key in api_seen:
            continue
        api_seen.add(key)
        uniq_apis.append(a)
        if len(uniq_apis) >= MAX_APIS:
            break

    return {
        "functional": uniq_features,
        "api": uniq_apis,
        "stats": {
            "files_scanned": files_scanned,
            "features": len(uniq_features),
            "apis": len(uniq_apis),
        },
    }


def build_functional_cases(features: list[dict], case_fn) -> list:
    """case_fn(method, scenario, seq_counter_key, **kwargs) -> case dict"""
    cases = []
    scenarios = [
        ("NORMAL", "正常输入与预期输出"),
        ("ABNORMAL", "异常输入与错误处理"),
        ("BOUNDARY", "边界值与空值处理"),
    ]
    for feat in features:
        kind = feat.get("kind", "function")
        name = feat["name"]
        rel = feat["file"]
        desc = f"{kind} {name} 位于 {rel}"
        for scen_code, scen_hint in scenarios:
            case_fn(
                "SC" if scen_code == "NORMAL" else ("EG" if scen_code == "ABNORMAL" else "BV"),
                scen_code,
                func=f"[功能] {name}",
                desc=desc,
                content=f"{scen_hint} · 验证 {kind} `{name}` 行为符合预期",
                steps=[
                    f"定位源文件 {rel}",
                    f"准备{scen_hint}测试数据",
                    f"调用/触发 {name}",
                    "比对实际结果与预期",
                ],
                expected=f"{kind} `{name}` 在{scen_hint}下行为正确",
                assertion={
                    "type": "source_symbol_exists",
                    "file": rel,
                    "symbol": name,
                    "kind": kind,
                },
                case_category="functional",
                source_file=rel,
                source_symbol=name,
            )
    return cases


def build_api_cases(apis: list[dict], case_fn) -> list:
    cases = []
    templates = [
        ("NORMAL", "GET", "合法请求应返回成功状态码"),
        ("ABNORMAL", "POST", "非法参数应返回 4xx 错误"),
        ("SECURITY", "GET", "未授权访问应被拒绝"),
    ]
    for api in apis:
        method = api["method"]
        path = api["path"]
        rel = api["file"]
        for scen_code, default_method, hint in templates:
            m = method if scen_code == "NORMAL" else default_method
            case_fn(
                "SC" if scen_code == "NORMAL" else "EG",
                scen_code,
                func=f"[接口] {m} {path}",
                desc=f"接口定义于 {rel}",
                content=f"{hint} · {m} {path}",
                steps=[
                    f"确认路由 {m} {path} 已在 {rel} 定义",
                    "构造请求参数与 Header",
                    "发送 HTTP 请求（静态验收：检查路由声明）",
                    "验证响应码与响应体结构",
                ],
                expected=f"接口 {m} {path} 路由存在且参数校验逻辑完整",
                assertion={
                    "type": "api_route_in_source",
                    "file": rel,
                    "method": m,
                    "path": path,
                },
                case_category="api",
                source_file=rel,
                api_method=m,
                api_path=path,
            )
    return cases
