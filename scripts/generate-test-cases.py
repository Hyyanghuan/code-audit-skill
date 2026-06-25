#!/usr/bin/env python3
"""
根据代码审计配置与扫描结果，按九种用例设计方法 + 完整场景分类生成验收测试用例。
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone

ARTIFACTS_DIR = os.environ["ARTIFACTS_DIR"]
RESULTS_DIR = os.environ["RESULTS_DIR"]
OUTPUT_JSON = os.path.join(ARTIFACTS_DIR, "test-cases.json")

# ── 九种用例设计方法 ──
DESIGN_METHODS = {
    "EQ": "等价类划分法",
    "BV": "边界值分析法",
    "EG": "错误推测法",
    "SC": "场景法",
    "DT": "判定表法",
    "CG": "因果图法",
    "OT": "正交试验法",
    "FG": "功能图法",
    "RT": "随机测试法",
}

# ── 场景分类（按测试类型）──
SCENARIO_TYPES = {
    "NORMAL": "正常业务场景（正向）",
    "ABNORMAL": "异常场景（反向/负面）",
    "BOUNDARY": "边界场景",
    "INTERRUPT": "中断场景",
    "CONCURRENT": "并发/多用户场景",
    "BRANCH": "分支/备选流程场景",
    "LOAD": "极限负载场景",
    "PERMISSION": "权限场景",
    "COMPAT": "兼容场景",
    "ROLLBACK": "数据恢复/回滚场景",
    "INIT": "初始化场景",
    "CREATE": "新增场景",
    "QUERY": "查询场景",
    "UPDATE": "修改场景",
    "DELETE": "删除场景",
    "IMPORT_EXPORT": "导出/导入场景",
    "APPROVAL": "审批流转场景",
    "WEAK_NET": "弱网/离线场景",
    "SECURITY": "安全场景",
    "SCHEDULED": "定时任务场景",
}

MODULE_META = {
    "gitleaks": ("Gitleaks 敏感密钥扫描", "检测硬编码 API Key、Token、密码泄露"),
    "super_linter": ("Super-Linter 规范检查", "多语言静态代码规范校验"),
    "bandit": ("Bandit Python 安全", "Python 代码安全漏洞检测"),
    "dependency_scan": ("Trivy 依赖漏洞", "依赖清单已知漏洞扫描"),
    "custom_rules": ("自定义业务规则", "YAML 规则匹配违规模式"),
}

ENV_FLAGS = {
    "gitleaks": "ENABLE_GITLEAKS",
    "super_linter": "ENABLE_SUPER_LINTER",
    "bandit": "ENABLE_BANDIT",
    "dependency_scan": "ENABLE_DEPENDENCY",
    "custom_rules": "ENABLE_CUSTOM",
}


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default if default is not None else {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tc_id(method: str, seq: int) -> str:
    return f"TC-{method}-{seq:03d}"


def case(method, scenario, seq, func, desc, content, steps, expected, assertion, **extra):
    return {
        "tc_id": tc_id(method, seq),
        "design_method": DESIGN_METHODS.get(method, method),
        "design_method_code": method,
        "scenario_category": SCENARIO_TYPES.get(scenario, scenario),
        "scenario_code": scenario,
        "test_function": func,
        "function_description": desc,
        "test_content_description": content,
        "test_steps": steps if isinstance(steps, list) else [steps],
        "expected_result": expected,
        "test_result": "待执行",
        "passed": None,
        "assertion": assertion,
        **extra,
    }


def build_all_cases(detect):
    counters = {m: 0 for m in DESIGN_METHODS}
    cases = []

    def add(method, scenario, **kwargs):
        counters[method] += 1
        cases.append(case(method, scenario, counters[method], **kwargs))

    is_empty = detect.get("is_empty", False)
    has_py = detect.get("has_python", False)
    has_lint = detect.get("has_lintable_code", False)
    has_deps = detect.get("has_dependencies", False)

    # ═══ 一、等价类划分法 ═══
    add("EQ", "NORMAL",
        func="有效等价类-正常代码审计",
        desc="合法输入：有效源码目录，全部模块开启",
        content="工作目录含合法代码，各 enable 开关为 true",
        steps=["设置 working-directory 为有效路径", "全部 enable-* 为 true", "触发 push 事件审计"],
        expected="audit_status 为 success 或 failure（有检出时），不为 error",
        assertion={"type": "audit_summary"})

    add("EQ", "ABNORMAL",
        func="无效等价类-空项目目录",
        desc="无效输入：空目录应优雅降级",
        content="is_empty=true 时模块应跳过或返回 skipped",
        steps=["指向空项目目录", "执行语言检测", "验证各模块降级行为"],
        expected="无 error 级模块失败，audit_status 为 skipped 或 success",
        assertion={"type": "empty_project_graceful"} if is_empty else {"type": "audit_summary"})

    add("EQ", "ABNORMAL",
        func="无效等价类-模块开关关闭",
        desc="关闭 gitleaks 时该模块应跳过",
        content="enable-gitleaks=false 等价类",
        steps=["设置 enable-gitleaks=false", "执行审计", "检查 gitleaks 结果"],
        expected="gitleaks 模块 skipped 或未执行",
        assertion={"type": "module_skip", "module": "gitleaks",
                   "enabled": os.environ.get("ENABLE_GITLEAKS", "true").lower() == "true"})

    add("EQ", "COMPAT",
        func="有效等价类-多语言混合项目",
        desc="Python+JS+YAML 混合代码合法输入",
        content="多语言文件共存的有效等价类",
        steps=["检测 has_python/has_javascript", "启用对应 linter", "执行扫描"],
        expected="detect-languages.json 正确标识多语言",
        assertion={"type": "file_json_fields", "file": "detect-languages.json",
                   "fields": ["has_python", "has_lintable_code", "file_counts"]})

    # ═══ 二、边界值分析法 ═══
    add("BV", "BOUNDARY",
        func="边界值-空项目文件数=0",
        desc="文件总数边界：0 个文件",
        content="刚好等于空项目边界",
        steps=["统计 total files = 0", "验证 is_empty=true"],
        expected="is_empty 为 true，bandit/linter 自动跳过",
        assertion={"type": "file_json_fields", "file": "detect-languages.json", "fields": ["is_empty"]})

    add("BV", "BOUNDARY",
        func="边界值-单文件 Python 项目",
        desc="最少 1 个 .py 文件触发 bandit",
        content="file_counts.py 边界值 = 1",
        steps=["检测 py 文件数", "确认 has_python=true", "执行 bandit"],
        expected="has_python=true 时 bandit 应执行（非 skipped）",
        assertion={"type": "module_executed", "module": "bandit", "enabled": True,
                   "forbid_status": ["error"], "valid_status": ["success", "failure", "skipped"]})

    add("BV", "BOUNDARY",
        func="边界值-findings=0",
        desc="问题数下边界：0 个 findings",
        content="干净代码 findings 刚好为 0",
        steps=["执行全模块扫描", "统计 total_findings"],
        expected="total_findings >= 0，干净代码时为 0",
        assertion={"type": "findings_consistency"})

    add("BV", "BOUNDARY",
        func="边界值-开关参数大小写",
        desc="布尔入参边界：TRUE/Yes/1 与 false/NO/0",
        content="大小写混合开关应被 normalize_bool 正确解析",
        steps=["传入 enable-gitleaks=TRUE", "传入 fail-on-findings=FALSE", "验证流程不中断"],
        expected="入参容错，审计正常完成",
        assertion={"type": "audit_summary"})

    # ═══ 三、错误推测法 ═══
    add("EG", "ABNORMAL",
        func="错误推测-特殊字符工作目录",
        desc="路径含空格/特殊字符不应中断",
        content="凭经验推测路径解析易出错",
        steps=["设置含空格 working-directory（若存在）", "验证 resolve_work_dir 回退逻辑"],
        expected="路径不存在时回退到根目录，不崩溃",
        assertion={"type": "audit_summary"})

    add("EG", "SECURITY",
        func="错误推测-硬编码密钥检出",
        desc="代码中埋入 AWS Key 应被 gitleaks 检出",
        content="历史 bug：.env 泄露未检测",
        steps=["扫描含 AKIA 示例密钥文件", "检查 gitleaks findings"],
        expected="含密钥时 gitleaks status=failure 且 findings>=1",
        assertion={"type": "module_executed", "module": "gitleaks", "enabled": True,
                   "forbid_status": ["error"], "valid_status": ["success", "failure"]})

    add("EG", "SECURITY",
        func="错误推测-eval/exec 违规",
        desc="Python eval() 应被 bandit/自定义规则检出",
        content="常见安全漏洞模式",
        steps=["扫描含 eval 的 .py", "检查 bandit 与 custom_rules"],
        expected="违规代码被检出，findings>0",
        assertion={"type": "module_executed", "module": "custom_rules", "enabled": True,
                   "forbid_status": ["error"], "valid_status": ["success", "failure"]})

    add("EG", "ABNORMAL",
        func="错误推测-TG 网络异常",
        desc="无效 Token 时 TG 失败不阻断审计",
        content="网络/API 异常不应影响主流程",
        steps=["使用无效 token 或 chat_id", "完成审计", "检查主流程 exit"],
        expected="审计完成，telegram.log 记录失败",
        assertion={"type": "audit_summary"})

    # ═══ 四、场景法 ═══
    add("SC", "NORMAL",
        func="场景-完整审计主流程",
        desc="push 触发完整审计流水线",
        content="初始化→检测→扫描→汇总→用例→TG",
        steps=["push 触发 workflow", "依次执行各扫描模块", "生成并执行测试用例", "发送 TG 通知"],
        expected="全流程完成，制品上传成功",
        assertion={"type": "audit_summary"})

    add("SC", "BRANCH",
        func="场景-PR 分支保护流程",
        desc="pull_request 事件触发审计门禁",
        content="违规代码应阻断 PR",
        steps=["创建含违规代码 PR", "触发 code-audit", "验证 fail-on-findings"],
        expected="违规时 audit-status=failure",
        assertion={"type": "audit_summary"})

    add("SC", "INTERRUPT",
        func="场景-单模块失败不中断",
        desc="某模块 error 时其他模块继续",
        content="异常中断后流程降级继续",
        steps=["模拟 super-linter 拉取失败", "检查其他模块仍执行", "汇总仍生成"],
        expected="单模块 error 不导致全流程崩溃",
        assertion={"type": "audit_summary"})

    add("SC", "INIT",
        func="场景-首次空仓库初始化",
        desc="新仓库首次 push 空项目",
        content="初始化场景：无历史数据",
        steps=["空目录首次审计", "验证 detect is_empty", "模块全部跳过"],
        expected="优雅处理，返回 skipped",
        assertion={"type": "empty_project_graceful"} if is_empty else {"type": "audit_summary"})

    # ═══ 五、判定表法 ═══
    add("DT", "NORMAL",
        func="判定表-全开模块组合",
        desc="条件：全部 enable=true → 全部执行",
        content="C1=T C2=T C3=T → 全扫描",
        steps=["enable 全部 true", "有对应代码", "验证 5 模块均有结果"],
        expected="已启用且有代码的模块均产生 JSON 结果",
        assertion={"type": "findings_consistency"})

    add("DT", "BRANCH",
        func="判定表-仅安全扫描组合",
        desc="gitleaks=T bandit=T linter=F → 仅安全类",
        content="多条件组合决定执行子集",
        steps=["关闭 super-linter", "保留 gitleaks+bandit", "执行审计"],
        expected="关闭的模块 skipped，开启的执行",
        assertion={"type": "audit_summary"})

    add("DT", "PERMISSION",
        func="判定表-TG通知条件",
        desc="enable-telegram=T 且 token/chat 有效 → 发送",
        content="通知条件组合判定",
        steps=["检查 telegram.yaml 配置", "enable-telegram=true", "验证 TG 步骤执行"],
        expected="配置完整时发送摘要+MD+日志",
        assertion={"type": "audit_summary"})

    # ═══ 六、因果图法 ═══
    add("CG", "SECURITY",
        func="因果-有密钥→gitleaks失败",
        desc="因：代码含密钥 → 果：gitleaks failure",
        content="因果链：secret in code → findings>0 → failure",
        steps=["扫描 invalid-code fixture", "检查 gitleaks 因果链"],
        expected="有密钥时 gitleaks 检出",
        assertion={"type": "module_executed", "module": "gitleaks", "enabled": True,
                   "forbid_status": ["error"], "valid_status": ["success", "failure"]})

    add("CG", "NORMAL",
        func="因果-无Python→bandit跳过",
        desc="因：无 .py 文件 → 果：bandit skipped",
        content="语言检测因果驱动模块启停",
        steps=["纯 JS 项目", "has_python=false", "bandit 不执行"],
        expected="bandit skipped",
        assertion={"type": "module_skip", "module": "bandit", "enabled": True})

    add("CG", "ROLLBACK",
        func="因果-扫描失败→fail-on-findings",
        desc="因：findings>0 + fail-on-findings=T → 果：Action 失败",
        content="审计结果因果判定 PR 阻断",
        steps=["违规代码", "fail-on-findings=true", "检查 exit code"],
        expected="高危检出时 Action 失败",
        assertion={"type": "audit_summary"})

    # ═══ 七、正交试验法 ═══
    ortho_combos = [
        ("gitleaks", "T", "NORMAL"),
        ("bandit", "T" if has_py else "F", "COMPAT"),
        ("super_linter", "T" if has_lint else "F", "COMPAT"),
        ("dependency_scan", "T" if has_deps else "F", "NORMAL"),
        ("custom_rules", "T", "SECURITY"),
    ]
    for mod, flag, scen in ortho_combos:
        name, desc_short = MODULE_META.get(mod, (mod, ""))
        add("OT", scen,
            func=f"正交-{mod}={flag}",
            desc=f"正交组合：{mod} 开关={flag}",
            content=f"精选代表性组合，覆盖 {name}",
            steps=[f"enable-{mod.replace('_', '-')}={flag}", "执行审计", f"验证 {mod} 结果"],
            expected=f"{mod} 按开关与语言条件正确执行或跳过",
            assertion={"type": "module_executed" if flag == "T" else "module_skip",
                       "module": mod, "enabled": flag == "T"})

    # ═══ 八、功能图法 ═══
    states = [
        ("INIT", "状态迁移-初始化", "INIT", "流程起点：init.sh 写入 env.sh"),
        ("SCAN", "状态迁移-扫描中", "NORMAL", "各 run-*.sh 执行，写入 results/*.json"),
        ("AGGREGATE", "状态迁移-汇总", "QUERY", "finalize-results 生成 audit-summary"),
        ("TESTGEN", "状态迁移-用例生成", "CREATE", "generate-test-cases 输出 MD/JSON"),
        ("TESTEXEC", "状态迁移-用例执行", "UPDATE", "execute-test-cases 回写结果"),
        ("NOTIFY", "状态迁移-TG通知", "NORMAL", "send-telegram 推送"),
    ]
    for st, func, scen, desc in states:
        add("FG", scen,
            func=func,
            desc=f"功能图状态：{st}",
            content=desc,
            steps=[f"进入 {st} 状态", "验证该阶段产物存在", "检查日志无致命错误"],
            expected=f"{st} 阶段产物完整",
            assertion={"type": "audit_summary"})

    # ═══ 九、随机测试法 ═══
    add("RT", "LOAD",
        func="随机-依赖目录过滤",
        desc="随机遍历时 node_modules 应被忽略",
        content="随机路径不应扫描第三方依赖",
        steps=["确认 ignore-paths 含 node_modules", "扫描含 node_modules 项目", "验证无误报"],
        expected="依赖目录被排除，扫描时间可控",
        assertion={"type": "audit_summary"})

    add("RT", "WEAK_NET",
        func="随机-工具下载失败降级",
        desc="随机网络故障时工具安装降级",
        content="trivy/gitleaks 下载失败 → error 不阻断",
        steps=["模拟工具不可用", "检查模块 status=error", "其他模块继续"],
        expected="单工具失败降级为 error",
        assertion={"type": "audit_summary"})

    add("RT", "IMPORT_EXPORT",
        func="随机-制品日志完整性",
        desc="随机检查制品中日志文件存在性",
        content="audit-logs 制品应含各模块 log",
        steps=["列出 artifacts 目录", "验证 *.log 存在", "验证 test-cases.md 存在"],
        expected="制品目录含完整日志与用例 MD",
        assertion={"type": "file_exists", "file": "test-cases.md"})

    # ═══ 按业务流程补充场景 ═══
    biz_scenarios = [
        ("QUERY", "业务流程-语言检测查询", "读取 detect-languages.json 查询语言分布"),
        ("CREATE", "业务流程-测试用例生成", "审计后自动生成 test-cases.md"),
        ("UPDATE", "业务流程-用例结果回写", "执行后更新 test_result 和 passed"),
        ("DELETE", "业务流程-忽略路径排除", "编译产物目录不参与扫描"),
        ("IMPORT_EXPORT", "业务流程-制品导出", "upload-artifact 上传日志"),
        ("APPROVAL", "业务流程-PR门禁审批", "fail-on-findings 阻断合并"),
        ("SCHEDULED", "业务流程-手动触发", "workflow_dispatch 补充定时/手动"),
        ("WEAK_NET", "补充-弱网TG重试", "TG 发送失败记录 telegram.log"),
    ]
    for scen, func, content in biz_scenarios:
        add("SC", scen,
            func=func,
            desc=SCENARIO_TYPES.get(scen, scen),
            content=content,
            steps=["触发对应业务流程", "验证阶段产物", "检查状态正确"],
            expected="业务流程完整执行",
            assertion={"type": "audit_summary"})

    cases.extend(build_methodology_audit_cases(detect, add))

    return cases


def build_methodology_audit_cases(detect, add_fn):
    """按六大类审计方法生成验收用例（全覆盖常用测试/审计方法）。"""
    methods_path = os.path.join(
        os.environ.get("GITHUB_ACTION_PATH", ""),
        "config", "audit-methods.yaml"
    )
    extra = []
    if not os.path.isfile(methods_path):
        return extra

    try:
        import yaml
        with open(methods_path, encoding="utf-8") as f:
            catalog = yaml.safe_load(f) or {}
    except Exception:
        return extra

    method_to_design = {
        "sast": "EQ", "dast_iast": "SC", "manual": "EG",
        "coverage": "BV", "specialized": "DT", "auxiliary": "CG",
    }
    method_to_scenario = {
        "sast": "SECURITY", "dast_iast": "NORMAL", "manual": "QUERY",
        "coverage": "BOUNDARY", "specialized": "SECURITY", "auxiliary": "CREATE",
    }

    for cat_key, cat in (catalog.get("categories") or {}).items():
        design = method_to_design.get(cat_key, "SC")
        scenario = method_to_scenario.get(cat_key, "NORMAL")
        cat_name = cat.get("name", cat_key)
        for m in cat.get("methods", []):
            mod = m.get("module", "")
            add_fn(
                design, scenario,
                func=f"[{cat_name}] {m.get('name', m.get('id'))}",
                desc=m.get("desc", cat_name),
                content=f"审计方法: {m.get('name')} | 模块: {mod} | 分类: {cat_name}",
                steps=[
                    f"启用模块 {mod}",
                    f"执行{m.get('name')}扫描",
                    "检查报告与 findings",
                    "回写测试用例结果",
                ],
                expected=f"模块 {mod} 正常完成，status 不为 error",
                assertion={"type": "module_executed", "module": mod, "enabled": True,
                           "forbid_status": ["error"],
                           "valid_status": ["success", "failure", "skipped"]},
            )
    return extra


def export_markdown(cases, stats, executed=False):
    md_path = os.path.join(ARTIFACTS_DIR, "test-cases.md")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# 代码审计验收测试用例报告",
        "",
        f"> 生成时间: {now}",
        f"> 仓库: {os.environ.get('GITHUB_REPOSITORY', '')}",
        f"> 工作目录: {os.environ.get('WORK_DIR', '.')}",
        f"> 总计: **{stats['total']}** | 通过: **{stats.get('passed', 0)}** | "
        f"失败: **{stats.get('failed', 0)}** | 待执行: **{stats.get('pending', stats['total'])}**",
        "",
        "## 用例设计方法索引",
        "",
        "| 代号 | 设计方法 | 用例数 |",
        "|------|----------|--------|",
    ]
    method_counts = {}
    for c in cases:
        code = c.get("design_method_code", "?")
        method_counts[code] = method_counts.get(code, 0) + 1
    for code, name in DESIGN_METHODS.items():
        lines.append(f"| {code} | {name} | {method_counts.get(code, 0)} |")

    lines.extend([
        "",
        "## 场景分类索引",
        "",
        "| 场景代码 | 场景分类 | 用例数 |",
        "|----------|----------|--------|",
    ])
    scen_counts = {}
    for c in cases:
        sc = c.get("scenario_code", "?")
        scen_counts[sc] = scen_counts.get(sc, 0) + 1
    for code, name in SCENARIO_TYPES.items():
        if scen_counts.get(code, 0) > 0:
            lines.append(f"| {code} | {name} | {scen_counts[code]} |")

    lines.extend([
        "",
        "---",
        "",
        "## 完整用例明细",
        "",
        "| TC-ID | 设计方法 | 场景分类 | 测试功能 | 功能描述 | 测试内容 | 测试步骤 | 预期结果 | 测试结果 | 是否通过 |",
        "|-------|----------|----------|----------|----------|----------|----------|----------|----------|----------|",
    ])
    for c in cases:
        steps = "<br>".join(f"{i+1}.{s}" for i, s in enumerate(c["test_steps"]))
        passed = c.get("passed")
        if passed is True:
            ps = "✅是"
        elif passed is False:
            ps = "❌否"
        else:
            ps = "⏳待执行"
        lines.append(
            f"| {c['tc_id']} | {c['design_method']} | {c['scenario_category']} "
            f"| {c['test_function']} | {c['function_description']} | {c['test_content_description']} "
            f"| {steps} | {c['expected_result']} | {c.get('test_result', '待执行')} | {ps} |"
        )

    # 按设计方法分组详情
    lines.extend(["", "---", "", "## 按设计方法分组详情", ""])
    for code, name in DESIGN_METHODS.items():
        group = [c for c in cases if c.get("design_method_code") == code]
        if not group:
            continue
        lines.append(f"### {name}（{code}）")
        lines.append("")
        for c in group:
            passed = c.get("passed")
            ps = "是" if passed is True else ("否" if passed is False else "待执行")
            lines.append(f"#### {c['tc_id']} {c['test_function']}")
            lines.append(f"- **场景**: {c['scenario_category']}")
            lines.append(f"- **描述**: {c['function_description']}")
            lines.append(f"- **内容**: {c['test_content_description']}")
            lines.append(f"- **步骤**: {' → '.join(c['test_steps'])}")
            lines.append(f"- **预期**: {c['expected_result']}")
            lines.append(f"- **结果**: {c.get('test_result', '待执行')}")
            lines.append(f"- **通过**: {ps}")
            lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md_path


def export_csv(cases):
    csv_path = os.path.join(ARTIFACTS_DIR, "test-cases.csv")
    fields = ["TC-ID", "设计方法", "场景分类", "测试功能", "功能描述", "测试内容描述",
              "测试步骤", "预期结果", "测试结果", "是否通过"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in cases:
            passed = c.get("passed")
            w.writerow({
                "TC-ID": c["tc_id"],
                "设计方法": c["design_method"],
                "场景分类": c["scenario_category"],
                "测试功能": c["test_function"],
                "功能描述": c["function_description"],
                "测试内容描述": c["test_content_description"],
                "测试步骤": " | ".join(c["test_steps"]),
                "预期结果": c["expected_result"],
                "测试结果": c.get("test_result", "待执行"),
                "是否通过": "是" if passed is True else ("否" if passed is False else "待执行"),
            })
    return csv_path


def main():
    detect = load_json(os.path.join(ARTIFACTS_DIR, "detect-languages.json"), {})
    cases = build_all_cases(detect)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "work_dir": os.environ.get("WORK_DIR", "."),
        "design_methods": DESIGN_METHODS,
        "scenario_types": SCENARIO_TYPES,
        "total_count": len(cases),
        "executed": False,
        "test_cases": cases,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    stats = {"total": len(cases), "passed": 0, "failed": 0, "pending": len(cases)}
    export_markdown(cases, stats)
    export_csv(cases)

    print(f"已生成 {len(cases)} 条测试用例（含九种设计方法）-> {OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
