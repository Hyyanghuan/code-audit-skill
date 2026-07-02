# 模块 Spec：Action 核心（编排 / 初始化 / 汇总）

> 联调契约 | 对应：`action.yml`、`init.sh`、`finalize-results.sh`

---

## 1. 模块职责

Composite Action 入口：解析业务仓 workflow 参数，初始化环境，调度扫描模块，汇总结果并输出 Action outputs。

---

## 2. 对外接口（业务仓 → Action）

### 2.1 必填/推荐 workflow 配置

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0          # 差分审计必需

- uses: ORG/code-audit-skill@v1.0.0
  with:
    audit-preset: security
    enable-sarif: 'true'
    fail-on-findings: 'true'
```

### 2.2 Inputs 契约

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `working-directory` | string | `.` | 审计根目录（相对仓库根） |
| `fail-on-findings` | bool string | `true` | 汇总 failure 时是否 `exit 1` |
| `upload-artifacts` | bool string | `true` | 是否上传制品 |
| `artifact-retention-days` | string | `14` | 制品保留天数 |
| `enable-*` | bool string | `true` | 14 模块 + test-cases + telegram 开关 |
| `telegram-*` | string | 空 | 留空读 `config/telegram.yaml` |
| `gitleaks-config` | string | 空 | 自定义 gitleaks 配置 |
| `custom-rules-path` | string | 空 | 自定义业务规则 |
| `ignore-paths-file` | string | 空 | 额外忽略路径 |
| `super-linter-languages` | string | 空 | 如 `Python, JavaScript` |
| `audit-preset` | string | `full` | `minimal` \| `security` \| `python` \| `ci-fast` |
| `enable-sarif` | bool string | `true` | 生成 SARIF 制品 |

**布尔解析**：`true/false/1/0/yes/no`，大小写不敏感。

### 2.3 Outputs 契约

| 输出 | 值域 | 消费方 |
|------|------|--------|
| `audit-status` | `success` \| `failure` \| `skipped` | 分支保护 / 下游 job |
| `findings-count` | 非负整数 | 通知 / 门禁 |
| `results-json` | 路径 | 自定义后处理 |
| `test-cases-passed` | 整数 | 质量看板 |
| `test-cases-failed` | 整数 | 质量看板 |
| `test-cases-all-passed` | `true` \| `false` \| `skipped` | 门禁 |
| `sarif-path` | 路径 | Code Scanning 上传 |

---

## 3. 内部交互

### 3.1 init 输出（GitHub Step Outputs）

| Output | 用途 |
|--------|------|
| `enable_gitleaks` 等 | 各扫描 step 的 `if` 条件 |
| `audit_dir` | 制品与结果根路径 |
| `fail_on_findings` | 最终判定 step |
| `upload_artifacts` | upload-artifact step |

### 3.2 环境变量（`$AUDIT_DIR/env.sh`）

后续所有脚本通过 `load_audit_env` 加载：

- `AUDIT_DIR`、`ARTIFACTS_DIR`、`RESULTS_DIR`
- `ABS_WORK_DIR`、`WORK_DIR`
- 各 `ENABLE_*` 开关

---

## 4. 执行顺序（不可乱序）

```
init → detect → [14 扫描模块并行语义顺序] → finalize
→ manual_checklist → generate_tests → execute_tests
→ generate_bugs → upload-artifact → telegram → 失败判定
```

---

## 5. 验收标准

| # | 场景 | 预期 |
|---|------|------|
| AC-01 | 最小 workflow 3 行 with | Job 成功，制品存在 |
| AC-02 | `fail-on-findings: false` + 有 findings | Job 成功，output 仍为 failure |
| AC-03 | 全部模块关闭 | `audit-status: skipped` |
| AC-04 | `enable-telegram: false` | 无 TG 请求，审计正常 |
| AC-05 | 开关 `TRUE` / `Yes` / `1` | 与 `true` 等价 |
| AC-06 | `working-directory: test-fixtures/normal-project` | 仅扫描子目录 |

---

## 6. 错误码与日志

| 情况 | 行为 |
|------|------|
| 扫描模块失败 | `continue-on-error`，写入 `status: failure` |
| finalize 后 failure + fail-on-findings | `::error::` + `exit 1` |
| init 目录创建失败 | step 失败，后续不执行 |

---

## 7. 依赖

- 上游：业务仓 checkout
- 下游：所有 [scan-*](../) 与 [telegram](../telegram/spec.md) 模块
