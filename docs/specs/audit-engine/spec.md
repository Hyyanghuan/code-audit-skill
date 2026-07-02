# 模块 Spec：内置审计引擎 (audit-engine)

> 联调契约 | 对应：`run-audit-module.sh`、`audit-engine.py`、`config/sast-patterns.yaml`

---

## 1. 职责

统一 Python 引擎，通过 `AUDIT_MODULE` 环境变量 dispatch 以下子模块：

| AUDIT_MODULE | Action input | 说明 |
|--------------|--------------|------|
| `sast_patterns` | `enable-sast-patterns` | 词法/语法危险模式 |
| `taint_analysis` | `enable-taint-analysis` | Source→Sink 污点链 |
| `control_flow` | `enable-control-flow` | 异常吞没、空鉴权 |
| `config_audit` | `enable-config-audit` | yml/Dockerfile 明文密码 |
| `specialized_security` | `enable-specialized-security` | 越权/上传/业务风险 |
| `diff_audit` | `enable-diff-audit` | git diff 增量 |
| `coverage_audit` | `enable-coverage-audit` | coverage.xml / lcov |
| `runtime_audit` | `enable-runtime-audit` | DAST/IAST **建议**（非执行） |
| `manual_checklist` | `enable-manual-checklist` | 人工审计 MD 清单 |

---

## 2. 调用接口

```bash
AUDIT_MODULE=sast_patterns bash run-audit-module.sh
```

**前置环境**（由 init 注入）：

- `ABS_WORK_DIR`、`ARTIFACTS_DIR`、`RESULTS_DIR`
- `GITHUB_ACTION_PATH`（读取 config）

---

## 3. 配置源

| 文件 | 用途 |
|------|------|
| `config/sast-patterns.yaml` | 词法规则、taint sources/sinks、控制流启发式 |
| `config/audit-methods.yaml` | 方法论分类（文档/映射） |
| `config/ignore-paths.txt` | 路径过滤 |

---

## 4. 输出契约

**文件**：`$RESULTS_DIR/{module}.json`

```json
{
  "module": "sast_patterns",
  "status": "success | failure | skipped",
  "findings": 2,
  "details": [
    {
      "file": "src/app.py",
      "line": 42,
      "severity": "high",
      "category": "sql_injection",
      "message": "检测到 SQL 字符串拼接",
      "snippet": "query = \"SELECT ...\" + user_input"
    }
  ]
}
```

**人工清单额外输出**：`$ARTIFACTS_DIR/manual-audit-checklist.md`

---

## 5. 子模块行为摘要

### sast_patterns
- 按 `pattern` 正则逐行匹配
- 默认 globs：`**/*.py`, `**/*.js`, `**/*.ts` 等

### taint_analysis
- 标记 taint_source 行
- 追踪变量是否到达 taint_sink（启发式，非完整数据流）

### control_flow
- 检测 `except: pass`、空 `def check_auth` 等

### config_audit
- 扫描 `*.yml`, `Dockerfile*`, `.env*` 明文 password/secret

### specialized_security
- 越权关键词、路径遍历上传、日志打印敏感字段

### diff_audit
- **依赖** `fetch-depth: 0`
- 对 `git diff` 变更文件跑精简规则集

### coverage_audit
- 解析 `coverage.xml` 或 `lcov.info`
- 低于阈值 → findings（info/medium）

### runtime_audit
- 输出建议清单 MD 片段，**不产生真实动态扫描**
- 明确标注需预发环境

### manual_checklist
- 按 audit-methods.yaml 生成可勾选 Markdown
- findings 可为 0，status 仍为 success

---

## 6. 交互

```
detect-languages ──► diff_audit（需 git 历史）
扫描结果 ──► finalize ──► bug-report / test-cases
manual_checklist ──► artifacts ──► telegram 附件
```

---

## 7. 验收标准

| # | 场景 | 预期 |
|---|------|------|
| AC-01 | `invalid-code` + sast 全开 | 多个 engine 模块 failure |
| AC-02 | 无 coverage 文件 | coverage_audit skipped 或 0 findings |
| AC-03 | shallow checkout | diff_audit 降级 warning，不 crash |
| AC-04 | manual_checklist 开启 | 制品含 checklist MD |
| AC-05 | runtime_audit | 仅建议文本，无 HTTP 探测 |

---

## 8. 扩展指南

新增 engine 子模块步骤：

1. `audit-engine.py` 增加 `run_xxx()` 与 main dispatch
2. `action.yml` 增加 step + input
3. `init.sh` / `finalize-results.sh` MODULES 数组注册
4. 本 spec 追加一行 + `generate-bug-report.py` MODULE_INFO
