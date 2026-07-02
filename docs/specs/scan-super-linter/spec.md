# 模块 Spec：Super-Linter 多语言规范

> 联调契约 | 对应：`enable-super-linter`、`run-super-linter.sh`

---

## 1. 职责

多语言静态编码规范检查（Python/JS/YAML 等）。

---

## 2. 触发条件

```
enable_super_linter == 'true' AND has_lintable_code == 'true'
```

---

## 3. 配置接口

| 来源 | 键 | 说明 |
|------|-----|------|
| Action input | `super-linter-languages` | 逗号分隔语言列表 |
| 环境 | `GITHUB_TOKEN` | action.yml 注入 `${{ github.token }}` |
| 环境 | `DEFAULT_BRANCH` | 用于 super-linter 基线 |

---

## 4. 输出契约

**文件**：`$RESULTS_DIR/super_linter.json`

---

## 5. 交互

- 耗时较长：大仓可通过 `enable-super-linter: false` 关闭
- findings 通常为 medium 级别规范问题

---

## 6. 验收标准

| # | 场景 | 预期 |
|---|------|------|
| AC-01 | `multi-language` | 执行并产出 report |
| AC-02 | `empty-project` | skipped 或 success(0 findings) |
| AC-03 | 指定 `super-linter-languages: Python` | 仅 Python linter |
| AC-04 | super-linter 失败 | `continue-on-error`，status failure |
