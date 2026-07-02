# 模块 Spec：验收测试用例

> 联调契约 | 对应：`enable-test-cases`、`generate-test-cases.py`、`execute-test-cases.py`

---

## 1. 职责

基于审计结果自动生成验收测试用例（九种设计方法），执行后将结果回写并影响 Action outputs。

---

## 2. 触发条件

```
enable_test_cases == 'true'
```

在 `finalize` **之后**执行（依赖 audit-summary）。

---

## 3. 输出契约

| 文件 | 格式 |
|------|------|
| `$ARTIFACTS_DIR/test-cases.md` | 人类可读，含场景分类 |
| `$ARTIFACTS_DIR/test-cases.json` | 机器可读，含用例 ID、方法、步骤、预期 |
| `$ARTIFACTS_DIR/test-cases-results.json` | 执行结果 |

### test-cases.json 用例结构

```json
{
  "id": "TC-001",
  "method": "等价类划分",
  "scenario": "密钥扫描",
  "title": "仓库不含硬编码 Token",
  "steps": ["运行 gitleaks", "检查 findings"],
  "expected": "findings == 0",
  "related_module": "gitleaks"
}
```

---

## 4. Action Outputs

| 输出 | 来源 step |
|------|-----------|
| `test-cases-passed` | execute_tests |
| `test-cases-failed` | execute_tests |
| `test-cases-all-passed` | execute_tests |

---

## 5. 交互

| 方向 | 说明 |
|------|------|
| ← audit-summary | 驱动用例生成 |
| → bug-report | 失败用例转为 `test_case` 模块 BUG |
| → telegram | `send_test_cases_md: true` 时发送 MD 附件 |

---

## 6. 验收标准

| # | 场景 | 预期 |
|---|------|------|
| AC-01 | 正常项目 | 用例生成且 majority passed |
| AC-02 | `invalid-code` | 存在 failed 用例，计入 bug-report |
| AC-03 | `enable-test-cases: false` | outputs 为 0 / skipped |
| AC-04 | 执行脚本异常 | `continue-on-error`，不阻断 TG |

---

## 7. 设计方法覆盖（生成器承诺）

等价类、边界值、判定表、因果图、正交试验、场景法、错误猜测、状态迁移、探索性 — 每类至少 1 条模板用例（无审计发现时生成通用用例）。
