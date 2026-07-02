# 模块 Spec：Trivy 依赖漏洞扫描 (SCA)

> 联调契约 | 对应：`enable-dependency-scan`、`run-dependency-scan.sh`

---

## 1. 职责

扫描 `requirements.txt`、`package.json`、`go.mod` 等依赖清单的已知 CVE。

---

## 2. 触发条件

```
enable_dependency_scan == 'true' AND has_dependencies == 'true'
```

---

## 3. 扫描范围

由 `detect-languages.sh` 识别的依赖 manifest 文件。

---

## 4. 输出契约

**文件**：`$RESULTS_DIR/dependency_scan.json`

| 字段 | 说明 |
|------|------|
| `findings` | 漏洞条目数 |
| `details[].severity` | CRITICAL/HIGH/MEDIUM/LOW |

---

## 5. 交互

- CVE 条目进入 bug-report，修复建议指向升级版本
- 与 `coverage_audit` 无直接依赖

---

## 6. 验收标准

| # | Fixture | 预期 |
|---|---------|------|
| AC-01 | `multi-language`（含 requirements.txt） | 执行 trivy |
| AC-02 | `empty-project` | skipped |
| AC-03 | 发现 HIGH CVE | audit-status failure（fail-on-findings 时 Job 失败） |
