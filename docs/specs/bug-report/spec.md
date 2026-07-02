# 模块 Spec：Bug 报告

> 联调契约 | 对应：`generate-bug-report.py`、`generate-bug-report.sh`

---

## 1. 职责

汇总各扫描模块 findings 与失败测试用例，生成统一 Bug 报告（Markdown + JSON）。

---

## 2. 触发条件

```
always()  # 即使扫描失败也执行
```

---

## 3. 输出契约

| 文件 | 用途 |
|------|------|
| `$ARTIFACTS_DIR/audit-bugs.md` | 人类阅读、TG 附件 |
| `$ARTIFACTS_DIR/audit-bugs.json` | 程序化消费 |

### 单条 Bug 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `bug_id` | ✅ | 如 `BUG-0001` |
| `module` | ✅ | 来源模块 id |
| `feature` | ✅ | 模块中文名 |
| `description` | ✅ | 功能描述 |
| `file` | 推荐 | 文件路径 |
| `line` | 推荐 | 行号 |
| `code` | 推荐 | 错误代码片段 |
| `reason` | ✅ | 问题原因 |
| `severity` | ✅ | `critical` / `high` / `medium` / `info` |
| `fix_suggestion` | ✅ | 自动修复指引 |
| `category` | 可选 | 映射 FIX_HINTS 键 |

### Markdown 结构

```markdown
# 代码审计 Bug 报告
## BUG-0001 [high] Gitleaks 敏感密钥扫描
- **文件**: ...
- **原因**: ...
- **修复建议**: ...
```

---

## 4. 交互

| 方向 | 说明 |
|------|------|
| ← `*-report.json` / test-cases-results | 输入 |
| → telegram | `send_bug_report_md: true` 且有 Bug 时发 `[BUG ALERT]` |
| → 开发者 | 按 BUG-ID 跟踪修复 |

---

## 5. 严重级别规则

| 来源 severity | 映射 |
|---------------|------|
| critical / CRITICAL | critical |
| high / HIGH | high |
| medium / MEDIUM | medium |
| 其他 | info |

---

## 6. 验收标准

| # | 场景 | 预期 |
|---|------|------|
| AC-01 | 0 findings | 空报告或「未发现 Bug」章节 |
| AC-02 | 多模块 findings | BUG-ID 连续递增 |
| AC-03 | 失败测试用例 | module=`test_case` 条目 |
| AC-04 | MD 与 JSON 条数一致 | 自动化可 diff |

---

## 7. FIX_HINTS 类别（节选）

`sql_injection` | `command_injection` | `hardcoded_secret` | `xss` | `taint_sink` | `config` | `file_upload` | `business_risk` | `log_desensitize` | `general`
