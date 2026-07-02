# 模块 Spec：审计制品 (Artifacts)

> 联调契约 | 对应：`upload-artifacts`、`bundle-audit-logs.sh`

---

## 1. 职责

收集审计全链路输出，上传 GitHub Actions Artifacts，供下载与 TG 附件使用。

---

## 2. 触发条件

```
upload_artifacts == 'true'
```

---

## 3. 目录结构

```
$AUDIT_DIR/
├── results/           # 各模块 JSON（中间态）
│   ├── gitleaks.json
│   └── ...
└── artifacts/         # 上传目录 ★
    ├── audit-summary.json
    ├── audit-bugs.md / .json
    ├── test-cases.md / .json
    ├── test-cases-results.json
    ├── manual-audit-checklist.md
    ├── audit-logs-combined.txt
    ├── telegram.log
    ├── telegram-diagnostic.json
    ├── gitleaks-report.json
    ├── bandit-report.json
    └── *-report.json
```

---

## 4. upload-artifact 契约

| 属性 | 值 |
|------|-----|
| name | `code-audit-logs-{run_id}` |
| path | `$AUDIT_DIR/artifacts/` |
| retention-days | input `artifact-retention-days`（默认 14） |
| if-no-files-found | warn |

---

## 5. audit-summary.json 契约

```json
{
  "audit_status": "success | failure | skipped",
  "total_findings": 0,
  "modules": { "gitleaks": { "...": "..." } },
  "passed": [],
  "failed": [],
  "skipped": [],
  "errors": [],
  "timestamp": "ISO8601",
  "repository": "org/repo",
  "ref": "refs/heads/main",
  "sha": "...",
  "run_url": "https://github.com/.../actions/runs/..."
}
```

---

## 6. 交互

| 消费者 | 文件 |
|--------|------|
| 开发者 | audit-bugs.md |
| TG | summary + 附件子集 |
| 外部系统 | audit-summary.json / audit-bugs.json |
| Action output `results-json` | 指向 summary 或等价路径 |

---

## 7. 验收标准

| # | 场景 | 预期 |
|---|------|------|
| AC-01 | 正常完整运行 | Artifacts 可下载，含 summary |
| AC-02 | `upload-artifacts: false` | 无 artifact step |
| AC-03 | 仅部分模块运行 | summary.modules 仅含 executed |
| AC-04 | retention-days=7 | GitHub UI 显示 7 天保留 |

---

## 8. 日志合并 (bundle-audit-logs.sh)

- 合并各 step 日志到 `audit-logs-combined.txt`
- 供 TG 发送；体积受 `max_log_size_kb` 约束
