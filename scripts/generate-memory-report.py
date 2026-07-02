#!/usr/bin/env python3
"""
记忆层报告：intake / diff / completion / requirement-audit

用法:
  # 开任务 — 六棱镜 intake
  python scripts/generate-memory-report.py G01 "标题" --init-intake [--raw "用户原话"]

  # 关任务 — 全套报告 + 逻辑比对
  python scripts/generate-memory-report.py G01 "标题" [--goal "..."] [--base HEAD]

  # 仅逻辑比对（需已有 intake + 最近 diff）
  python scripts/generate-memory-report.py G01 "标题" --audit-only
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "docs" / "memory"
MODULE_MAP = MEMORY / "module-map.yaml"
LENS_YAML = MEMORY / "requirement-lens.yaml"
INTAKE_DIR = MEMORY / "intake"
REPORTS = MEMORY / "reports"
TEMPLATES = MEMORY / "templates"


def ensure_yaml():
    try:
        import yaml  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml"])


def load_yaml(path: Path) -> dict:
    ensure_yaml()
    import yaml
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_module_map() -> dict:
    return load_yaml(MODULE_MAP)


def load_requirement_lens() -> dict:
    return load_yaml(LENS_YAML)


def git(*args: str) -> str:
    r = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0 and args[0] not in ("diff", "rev-parse"):
        print(r.stderr, file=sys.stderr)
    return (r.stdout or "").strip()


def task_slug(title: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff-]", "-", title.lower())[:40].strip("-")


def report_base_name(task_id: str, title: str, date_str: str | None = None) -> str:
    d = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{d}-{task_id.upper()}-{task_slug(title)}"


def intake_path(task_id: str) -> Path:
    return INTAKE_DIR / f"{task_id.upper()}.md"


def changed_files(base: str, head: str) -> list[tuple[str, str]]:
    if head.upper() == "WORKTREE":
        seen = {}
        for extra in ([], ["--cached"]):
            out = git("diff", "--name-status", *extra, base)
            for line in out.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    seen[parts[-1]] = parts[0][0]
        for p in git("ls-files", "--others", "--exclude-standard").splitlines():
            if p.strip():
                seen[p.strip().strip('"')] = "A"
        return [(st, p) for p, st in sorted(seen.items())]
    out = git("diff", "--name-status", base, head)
    return [(ln.split("\t")[0][0], ln.split("\t")[-1]) for ln in out.splitlines() if "\t" in ln]


def diff_stat(base: str, head: str) -> str:
    if head.upper() == "WORKTREE":
        s = (git("diff", "--stat", base) + "\n" + git("diff", "--stat", "--cached", base)).strip()
        return s or "(无已跟踪文件变更)"
    return git("diff", "--stat", base, head) or "(无差异)"


def diff_patch(base: str, head: str, max_lines: int = 400) -> str:
    if head.upper() == "WORKTREE":
        patch = git("diff", base) or git("diff", "--cached", base)
    else:
        patch = git("diff", base, head)
    lines = patch.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... (截断，共 {len(patch.splitlines())} 行)"]
    return "\n".join(lines) or "(空)"


def count_stat(stat: str, file_rows: list) -> tuple[int, int, int]:
    ins = dels = 0
    for line in stat.splitlines():
        if "|" in line:
            m = re.search(r"(\d+)\s+insertion", line)
            if m:
                ins += int(m.group(1))
            m = re.search(r"(\d+)\s+deletion", line)
            if m:
                dels += int(m.group(1))
    return len(file_rows) or len([l for l in stat.splitlines() if "|" in l]), ins, dels


def match_module(path: str, modules_cfg: dict) -> tuple[str, str, str]:
    path_norm = path.replace("\\", "/")
    best = ("documentation", "docs/proposal.md", "文档（默认）")
    best_len = -1
    for mod_id, info in (modules_cfg.get("modules") or {}).items():
        for pattern in info.get("paths") or []:
            pat = pattern.replace("\\", "/")
            if pat.endswith("/**"):
                prefix = pat[:-3]
                if path_norm.startswith(prefix) and len(prefix) > best_len:
                    best_len, best = len(prefix), (mod_id, info.get("spec", ""), info.get("impact", ""))
            elif (fnmatch.fnmatch(path_norm, pat) or path_norm == pat) and len(pat) > best_len:
                best_len, best = len(pat), (mod_id, info.get("spec", ""), info.get("impact", ""))
    return best


STATUS_CN = {"A": "新增", "M": "修改", "D": "删除", "R": "重命名"}


def build_file_table(rows: list[tuple[str, str]], modules_cfg: dict):
    lines, impacts = [], {}
    for st, path in rows:
        mod_id, spec, _ = match_module(path, modules_cfg)
        link = f"[{mod_id}](../../{spec})" if spec else mod_id
        lines.append(f"| `{path}` | {STATUS_CN.get(st, st)} | {mod_id} | {link} |")
        impacts.setdefault(mod_id, []).append(path)
    table = "\n".join(lines) or "| — | — | — | — |"
    return table, impacts


def build_impact_section(impacts: dict, modules_cfg: dict) -> str:
    if not impacts:
        return "_无文件变更_\n"
    parts = []
    for mod_id, paths in sorted(impacts.items()):
        info = (modules_cfg.get("modules") or {}).get(mod_id, {})
        parts.append(
            f"### {mod_id}\n\n- **影响**：{info.get('impact', '见 spec')}\n"
            f"- **涉及文件**：{', '.join(f'`{p}`' for p in paths)}\n"
            f"- **Spec**：`{info.get('spec', '')}`\n"
        )
    return "\n".join(parts)


def infer_runtime_level(impacts: dict) -> dict[str, tuple[str, str]]:
    non_runtime = {"documentation", "memory-layer", "ci-self-test"}
    runtime = set(impacts) - non_runtime
    scan_mods = runtime - {"action-core", "artifacts", "telegram", "bug-report", "test-cases"}
    if not runtime:
        return {
            "Action 编排": ("无", "纯文档/记忆层"),
            "扫描结果": ("无", "—"),
            "制品/TG": ("无", "—"),
            "业务仓接入": ("低" if "documentation" in impacts else "无", "文档入口"),
        }
    return {
        "Action 编排": ("高" if "action-core" in runtime else "无", "—"),
        "扫描结果": ("高" if scan_mods else "无", ", ".join(sorted(scan_mods)) or "—"),
        "制品/TG": ("中" if set(runtime) & {"telegram", "artifacts", "bug-report"} else "无", "—"),
        "业务仓接入": ("高" if "action-core" in runtime else "中", "—"),
    }


def fill_template(path: Path, mapping: dict) -> str:
    text = path.read_text(encoding="utf-8")
    for k, v in mapping.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def parse_intake(text: str) -> dict:
    """从 intake 提取填写状态。"""
    checked = len(re.findall(r"- \[x\]", text, re.I))
    unchecked = len(re.findall(r"- \[ \]", text))
    filled_cells = len(re.findall(r"\|\s*[^|\s][^|]*\|\s*$", text, re.M))
    empty_feature_rows = len(re.findall(r"\|\s*F-\d+\s*\|[^|]*\|\s*[^|]*\|\s*[^|]*\|\s*\|\s*\|", text))
    has_raw = bool(re.search(r"## 0\. 需求原文", text)) and "``" not in text[text.find("## 0"):text.find("## 1")] if "## 0" in text else False
    confirmed = bool(re.search(r"- \[x\].*六棱镜已填完", text, re.I))
    return {
        "checked": checked,
        "unchecked": unchecked,
        "filled_cells": filled_cells,
        "empty_features": empty_feature_rows,
        "confirmed": confirmed,
        "has_content": len(text) > 500,
    }


def lens_trace_rows(lens_cfg: dict, intake_info: dict, impacts: dict, file_count: int) -> str:
    rows = []
    intake_status = "✅" if intake_info.get("confirmed") else ("⚠️" if intake_info.get("has_content") else "❌")
    evidence = f"diff {file_count} 文件" if file_count else "无代码变更"
    for lid, meta in (lens_cfg.get("lenses") or {}).items():
        if lid == "functional":
            align = "✅" if impacts else "➖"
            ev = ", ".join(sorted(impacts.keys())) or "见 intake"
        elif lid == "technical":
            align = "✅" if file_count else "➖"
            ev = evidence
        elif lid in ("product", "user"):
            align = intake_status
            ev = "见 intake §1"
        else:
            align = intake_status if intake_info.get("has_content") else "❌"
            ev = "见 intake §1"
        rows.append(f"| {meta.get('name', lid)} | intake §1.{list(lens_cfg.get('lenses', {})).index(lid)+1 if lid in (lens_cfg.get('lenses') or {}) else '?'} | {ev} | {align} |")
    return "\n".join(rows)


def completeness_rows(lens_cfg: dict, intake_info: dict, has_diff: bool, has_intake: bool) -> str:
    rows = []
    total, passed = 0, 0
    for dim_id, dim in (lens_cfg.get("completeness_dimensions") or {}).items():
        for check in dim.get("checks") or []:
            total += 1
            if "spec" in check and has_diff:
                ok, ev = True, "diff 已生成"
            elif "proposal" in check and has_intake:
                ok, ev = intake_info.get("has_content", False), "intake 已建"
            elif "test-fixtures" in check:
                ok, ev = False, "待人工勾选"
            elif "CONTEXT" in check or "tasks" in check:
                ok, ev = False, "关任务后更新"
            elif "AC" in check:
                ok, ev = has_diff, "completion 报告"
            elif "跳过" in check or "降级" in check:
                ok, ev = False, "见 intake 边界镜"
            else:
                ok, ev = has_intake, "—"
            if ok:
                passed += 1
            mark = "✅" if ok else "☐"
            rows.append(f"| {dim.get('label', dim_id)} | {check} | {mark} | {ev} |")
    return "\n".join(rows), (passed / total if total else 0)


def logic_rows(lens_cfg: dict, intake_info: dict, file_count: int, has_intake: bool, impacts: dict) -> tuple[str, float]:
    rows = []
    passed = 0
    auto = {
        "L01": (file_count > 0 or not has_intake, "有 diff 文件" if file_count else "无变更"),
        "L02": (False, "人工对照 spec AC"),
        "L03": (False, "人工对照 proposal Out of Scope"),
        "L04": (bool(impacts or file_count == 0), "module-map 已映射"),
        "L05": (False, "人工对照边界镜"),
        "L06": ("action-core" not in impacts, "未改 action 编排" if "action-core" not in impacts else "已改 action，需验证接入"),
        "L07": (file_count >= 0, "diff 与 completion 同批生成"),
        "L08": (True, "后续行动节已留"),
    }
    for item in lens_cfg.get("logic_checks") or []:
        iid = item.get("id", "")
        ok, note = auto.get(iid, (False, "人工确认"))
        if ok:
            passed += 1
        mark = "✅" if ok else "☐"
        rows.append(f"| {iid} | {item.get('name', '')} | {mark} | {note} |")
    total = len(lens_cfg.get("logic_checks") or []) or 1
    return "\n".join(rows), passed / total


def build_requirement_audit(
    task_id: str, title: str, ts: str, base_name: str,
    lens_cfg: dict, intake_text: str | None,
    impacts: dict, file_count: int, rows: list,
) -> str:
    intake_info = parse_intake(intake_text or "")
    has_intake = bool(intake_text and intake_info["has_content"])
    intake_fname = f"{task_id.upper()}.md"

    comp_rows, completeness_score = completeness_rows(lens_cfg, intake_info, file_count > 0, has_intake)
    logic_table, logic_score = logic_rows(lens_cfg, intake_info, file_count, has_intake, impacts)
    lens_rows = lens_trace_rows(lens_cfg, intake_info, impacts, file_count)

    feature_rows = "| — | 见 intake §2 | — | ☐ |"
    if intake_text and "| F-" in intake_text:
        feature_rows = "| 见 intake §2 功能矩阵 | 逐项填写 | diff 文件清单 | ☐ 人工比对 |"

    thr_c = (lens_cfg.get("scoring") or {}).get("completeness_pass_threshold", 0.8)
    thr_l = (lens_cfg.get("scoring") or {}).get("logic_pass_threshold", 1.0)

    c_verdict = "通过" if completeness_score >= thr_c else "待补充"
    l_verdict = "通过" if logic_score >= thr_l else "待人工确认"
    overall = "✅ 可关任务" if (completeness_score >= thr_c and logic_score >= 0.5) else "⚠️ 需补 intake/人工勾选"

    gaps = "_无 intake 或未解析到遗漏_" if not has_intake else "（对照 intake §2 中 ❌ 项与 diff 是否一致）"
    over = "（对照 proposal Out of Scope 是否误做）"
    contra = "（对照 intake §0 改写 vs completion §2 是否矛盾）"

    if not has_intake:
        gaps = "⚠️ 未创建 intake，无法自动比对需求遗漏 — 请先 `--init-intake`"

    mapping = {
        "TASK_ID": task_id.upper(),
        "TITLE": title,
        "TIMESTAMP": ts,
        "INTAKE_FILENAME": intake_fname,
        "DIFF_REPORT_FILENAME": f"{base_name}-diff.md",
        "COMPLETION_REPORT_FILENAME": f"{base_name}-completion.md",
        "COMPLETENESS_SCORE": f"{completeness_score:.0%}",
        "COMPLETENESS_VERDICT": c_verdict,
        "LOGIC_SCORE": f"{logic_score:.0%}",
        "LOGIC_VERDICT": l_verdict,
        "OVERALL_VERDICT": overall,
        "LENS_TRACE_ROWS": lens_rows,
        "FEATURE_TRACE_ROWS": feature_rows,
        "COMPLETENESS_ROWS": comp_rows,
        "LOGIC_ROWS": logic_table,
        "GAPS": gaps,
        "OVER_DELIVERY": over,
        "CONTRADICTIONS": contra,
    }
    return fill_template(TEMPLATES / "requirement-audit.template.md", mapping)


def generate_intake(task_id: str, title: str, raw: str, base_name: str, ts: str) -> Path:
    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    path = intake_path(task_id)
    if path.is_file():
        print(f"intake 已存在: {path.relative_to(ROOT)}（跳过覆盖）")
        return path
    content = fill_template(TEMPLATES / "requirement-intake.template.md", {
        "TASK_ID": task_id.upper(),
        "TITLE": title,
        "TIMESTAMP": ts,
        "RAW_REQUIREMENT": raw or "（请粘贴用户/产品原文）",
        "AUDIT_REPORT_FILENAME": f"{base_name}-requirement-audit.md",
    })
    path.write_text(content, encoding="utf-8")
    print(f"intake 已创建: {path.relative_to(ROOT)}")
    print("请填写六棱镜与功能矩阵后再实施 → 见 docs/memory/REQUIREMENT-GUIDE.md")
    return path


def apply_runtime_rows(content: str, runtime: dict, impact_summary: str) -> str:
    content = re.sub(
        r"\| Action 编排 \| \{LEVEL\} \| \{NOTE\} \|",
        f"| Action 编排 | {runtime['Action 编排'][0]} | {runtime['Action 编排'][1] or impact_summary} |",
        content,
    )
    for key, pat in [
        ("扫描结果", r"\| 扫描结果 \| \{LEVEL\} \| \{NOTE\} \|"),
        ("制品/TG", r"\| 制品/TG \| \{LEVEL\} \| \{NOTE\} \|"),
        ("业务仓接入", r"\| 业务仓接入 \| \{LEVEL\} \| \{NOTE\} \|"),
    ]:
        note = impact_summary if runtime[key][0] != "无" else "—"
        if key == "制品/TG":
            note = "—"
        if key == "业务仓接入":
            note = runtime[key][1] or "—"
        content = re.sub(pat, f"| {key} | {runtime[key][0]} | {note} |", content)
    return content


def main():
    parser = argparse.ArgumentParser(description="记忆层报告 + 需求六棱镜")
    parser.add_argument("task_id", help="任务 ID，如 G01")
    parser.add_argument("title", help="任务标题")
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--head", default="WORKTREE")
    parser.add_argument("--epic", default="")
    parser.add_argument("--goal", default="")
    parser.add_argument("--raw", default="", help="用户需求原文（init-intake 时写入）")
    parser.add_argument("--init-intake", action="store_true", help="仅生成 intake 模板")
    parser.add_argument("--audit-only", action="store_true", help="仅生成 requirement-audit（需已有 diff）")
    parser.add_argument("--send-tg", action="store_true", help="发送需求清单到 Telegram（关任务默认发送）")
    parser.add_argument("--no-send-tg", action="store_true", help="关任务时不发送 TG 需求清单")
    args = parser.parse_args()

    task_id = args.task_id.upper()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    base_name = report_base_name(task_id, args.title)
    lens_cfg = load_requirement_lens()

    if args.init_intake:
        generate_intake(task_id, args.title, args.raw, base_name, ts)
        return

    REPORTS.mkdir(parents=True, exist_ok=True)
    modules_cfg = load_module_map()
    intake_text = intake_path(task_id).read_text(encoding="utf-8") if intake_path(task_id).is_file() else None

    rows = changed_files(args.base, args.head)
    stat = diff_stat(args.base, args.head)
    file_count, insertions, deletions = count_stat(stat, rows)
    file_table, impacts = build_file_table(rows, modules_cfg)
    impact_section = build_impact_section(impacts, modules_cfg)
    impact_summary = "; ".join(f"**{m}**({len(p)} 文件)" for m, p in sorted(impacts.items())) or "无代码变更"
    runtime = infer_runtime_level(impacts)

    diff_name = f"{base_name}-diff.md"
    comp_name = f"{base_name}-completion.md"
    audit_name = f"{base_name}-requirement-audit.md"

    if not args.audit_only:
        diff_mapping = {
            "TASK_ID": task_id, "TITLE": args.title, "TIMESTAMP": ts,
            "BASE_REF": args.base, "HEAD_REF": args.head,
            "FILE_COUNT": file_count, "INSERTIONS": insertions, "DELETIONS": deletions,
            "DIFF_STAT": stat, "FILE_TABLE_ROWS": file_table,
            "IMPACT_SECTION": impact_section, "NOTE": impact_summary,
            "SPEC_LINKS": ", ".join(sorted(set(
                (modules_cfg.get("modules") or {}).get(m, {}).get("spec", "") for m in impacts
            ))),
            "DIFF_PATCH": diff_patch(args.base, args.head),
            "EXPECTED": "文档/脚本变更不影响 self-test" if "action-core" not in impacts else "需跑 Self Test",
            "LEVEL": "低",
        }
        diff_content = apply_runtime_rows(
            fill_template(TEMPLATES / "diff-report.template.md", diff_mapping), runtime, impact_summary
        )

        ac_rows = "\n".join([
            "| AC-01 | 变更已记录于差异报告 | ✅ | diff §1 |",
            "| AC-02 | 功能影响已映射 module-map | ✅ | diff §3 |",
            "| AC-03 | 需求逻辑比对 | 🔄 | requirement-audit |",
            "| AC-04 | intake 六棱镜已确认 | " + ("✅" if intake_text and parse_intake(intake_text).get("confirmed") else "☐") + " | intake |",
            "| AC-05 | CONTEXT 已更新 | ☐ | 人工 |",
        ])
        comp_mapping = {
            "TASK_ID": task_id, "TITLE": args.title, "TIMESTAMP": ts,
            "DIFF_REPORT_FILENAME": diff_name,
            "AUDIT_REPORT_FILENAME": audit_name,
            "EPIC": args.epic or "见 tasks.md",
            "GOAL_DESCRIPTION": args.goal or args.title,
            "RESULT_SUMMARY": f"共变更 {file_count} 个文件（+{insertions}/-{deletions}）。{impact_summary}",
            "AC_ROWS": ac_rows,
            "ARTIFACT_ROWS": "\n".join(f"| {STATUS_CN.get(st, st)} | `{p}` |" for st, p in rows) or "| — | — |",
            "IMPACT_SUMMARY": impact_summary,
            "REQUIREMENT_AUDIT_SUMMARY": "见 requirement-audit 总体结论",
            "FOLLOW_UP_ITEMS": "勾选 requirement-audit §7 门禁",
            "NOTES": "无 intake 时请先 --init-intake" if not intake_text else "",
        }
        comp_content = fill_template(TEMPLATES / "completion-report.template.md", comp_mapping)
        comp_content = comp_content.replace("| 状态 | ✅ 完成 / 🔄 部分 / ⏸ 阻塞 |", "| 状态 | 🔄 待 audit 门禁 |")

        (REPORTS / diff_name).write_text(diff_content, encoding="utf-8")
        (REPORTS / comp_name).write_text(comp_content, encoding="utf-8")
        print(f"差异报告: {(REPORTS / diff_name).relative_to(ROOT)}")

    audit_content = build_requirement_audit(
        task_id, args.title, ts, base_name, lens_cfg, intake_text, impacts, file_count, rows
    )
    (REPORTS / audit_name).write_text(audit_content, encoding="utf-8")
    print(f"逻辑比对: {(REPORTS / audit_name).relative_to(ROOT)}")
    if not args.audit_only:
        print(f"完成报告: {(REPORTS / comp_name).relative_to(ROOT)}")
    print(f"变更: {file_count} 文件 | 模块: {', '.join(sorted(impacts)) or '无'}")
    if not intake_text:
        print("⚠️  建议开任务时运行: --init-intake")

    # 需求清单 + TG（新需求 + 历史，时间倒序）
    if not args.audit_only:
        scripts_dir = ROOT / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        try:
            from generate_requirements_checklist import finalize_task_checklist
            send_tg = not args.no_send_tg
            if args.send_tg:
                send_tg = True
            checklist_path = finalize_task_checklist(
                task_id,
                args.title,
                args.epic,
                intake_path(task_id) if intake_path(task_id).is_file() else None,
                REPORTS / audit_name,
                REPORTS / comp_name,
                send_tg=send_tg,
            )
            print(f"需求清单: {checklist_path.relative_to(ROOT)}")
        except Exception as exc:
            print(f"需求清单/TG 失败: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
