# 模块 Spec：Bandit Python 安全扫描

> 联调契约 | 对应：`enable-bandit`、`run-bandit.sh`

---

## 1. 职责

对 Python 源码执行 bandit 安全规则（eval、SQL 注入模式等）。

---

## 2. 触发条件

```
enable_bandit == 'true' AND has_python == 'true'
```

`has_python` 由 `detect-languages.sh` 输出。

---

## 3. 扫描范围

- 根目录：`ABS_WORK_DIR`
- 排除：`config/ignore-paths.txt` + 内置 SKIP_DIRS

---

## 4. 输出契约

**文件**：`$RESULTS_DIR/bandit.json`

```json
{
  "module": "bandit",
  "status": "success | failure | skipped",
  "findings": 0,
  "details": []
}
```

**明细**：`$ARTIFACTS_DIR/bandit-report.json`

---

## 5. 交互

| 方向 | 说明 |
|------|------|
| detect → bandit | 无 Python 时跳过 |
| → bug-report | severity 映射 high/medium |

---

## 6. 验收标准

| # | Fixture | 预期 |
|---|---------|------|
| AC-01 | `no-python` | 模块 skipped，不计入 failure |
| AC-02 | `invalid-code/bad_app.py` | failure，含高危 finding |
| AC-03 | `multi-language` | 扫描 .py 文件 |
| AC-04 | `enable-bandit: false` | 不执行 |
