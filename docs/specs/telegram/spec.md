# 模块 Spec：Telegram 通知

> 联调契约 | 对应：`enable-telegram`、`config/telegram.yaml`、`send-telegram.sh`

---

## 1. 职责

向 Telegram 群推送审计摘要、Bug MD、测试用例 MD、合并日志、**需求清单 MD**（关任务）。

---

## 2. 触发条件

```
always() AND enable_telegram == 'true'
```

`continue-on-error: true` — **TG 失败不阻断 Job**。

---

## 3. 配置接口

### 3.1 优先级

```
workflow with (telegram-*)  >  init 合并后的 INPUT_*  >  config/telegram.yaml
```

### 3.2 telegram.yaml 契约

```yaml
enabled: true
bot_token: "..."
chat_id: "-100xxxxxxxxxx"
bot_username: "@bot"          # 可选，展示用

send_summary_message: true
send_test_cases_md: true
send_bug_report_md: true
send_audit_logs: true
send_requirements_checklist: true   # 关任务需求清单 MD
max_log_size_kb: 5000
```

### 3.3 Action inputs

| 参数 | 说明 |
|------|------|
| `enable-telegram` | 总开关 |
| `telegram-bot-token` | 覆盖 token |
| `telegram-chat-id` | 覆盖 chat_id |
| `telegram-bot-username` | 覆盖用户名 |

---

## 4. 推送内容契约

| 条件 | 消息类型 | 附件 |
|------|----------|------|
| 每次运行 | HTML/Markdown 摘要 | — |
| findings > 0 或 Bug MD 存在 | `[BUG ALERT]` 前缀 | `audit-bugs.md` |
| send_test_cases_md | — | `test-cases.md` |
| send_audit_logs | — | `audit-logs-combined.txt`（超 max 截断） |
| manual_checklist 存在 | 摘要提及 | 可选 checklist MD |

### 摘要字段（最少包含）

- 仓库名、分支/ref、commit sha
- audit-status、findings-count
- Actions run URL
- 测试用例 passed/failed

---

## 5. 诊断输出

**文件**：`$ARTIFACTS_DIR/telegram-diagnostic.json`

```json
{
  "status": "success | skipped | error",
  "detail": "...",
  "http_code": "200",
  "chat_id": "...",
  "config_source": "yaml | workflow"
}
```

---

## 6. 交互

| 场景 | 行为 |
|------|------|
| token/chat_id 为空 | warning + exit 0 |
| API 403 | 记录 diagnostic，exit 0 |
| 无效 token 自测 | 审计结论仍有效 |

---

## 7. 验收标准

| # | 场景 | 预期 |
|---|------|------|
| AC-01 | 有效配置 + invalid-code | 收到摘要 + Bug 附件 |
| AC-02 | 无效 token | telegram-diagnostic status=error，Job 仍由 audit 决定 |
| AC-03 | `enable-telegram: false` | 无 API 调用 |
| AC-04 | 业务仓 Secrets 覆盖 | 推送到独立群 |
| AC-05 | 日志 > max_log_size_kb | 截断并注明 |

---

## 8. 安全说明

- 生产环境 Token 优先 GitHub Secrets 覆盖
- 禁止将 Token 提交到业务仓 workflow 明文（仅本地测试）
