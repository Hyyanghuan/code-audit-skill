# 模块 Spec：自定义业务规则扫描

> 联调契约 | 对应：`enable-custom-rules`、`run-custom-rules.sh`

---

## 1. 职责

按 YAML 定义的业务规则（eval、硬编码密码、SQL 拼接等）匹配源码。

---

## 2. 触发条件

```
enable_custom_rules == 'true'
```

---

## 3. 配置接口

| 来源 | 路径 |
|------|------|
| 默认 | `config/custom-rules/business-rules.yaml` |
| 覆盖 | Action input `custom-rules-path` |

规则结构示例：

```yaml
rules:
  - id: no-eval
    pattern: '\beval\s*\('
    severity: high
    message: "禁止使用 eval"
    file_globs: ["**/*.py", "**/*.js"]
```

---

## 4. 输出契约

**文件**：`$RESULTS_DIR/custom_rules.json`

---

## 5. 验收标准

| # | 场景 | 预期 |
|---|------|------|
| AC-01 | `invalid-code/bad_app.py` 命中 eval 规则 | failure |
| AC-02 | 自定义 rules 路径无效 | error 或 skipped + warning |
| AC-03 | 规则 pattern 正则非法 | 跳过该条规则，不崩溃 |
