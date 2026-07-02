# 项目热快照（记忆层 · 优先阅读）

> **v1.0.0 企业级** | Secrets 优先 · audit-preset · SARIF · CI 测试

---

## 一句话

Code Audit Skill v1.0.0：14 模块 CI 审计 + 企业预设 + SARIF + Secrets 治理。

---

## 当前状态（2026-07-01）

| 项 | 值 |
|----|-----|
| 版本 | **1.0.0**（见 VERSION / CHANGELOG.md） |
| 企业级 | ✅ preset / SARIF / SECURITY / enterprise-ci |
| 接入 | `@v1.0.0` + Secrets `TG_BOT_TOKEN` / `TG_CHAT_ID` |
| 文档 | [GUIDANCE.md](../GUIDANCE.md) 可行性已落地 |

---

## 企业接入速查

```yaml
uses: YOUR_ORG/code-audit-skill@v1.0.0
with:
  audit-preset: security
  enable-sarif: 'true'
  telegram-bot-token: ${{ secrets.TG_BOT_TOKEN }}
  telegram-chat-id: ${{ secrets.TG_CHAT_ID }}
```

完整示例：`examples/consumer-workflow-enterprise.yml`

---

## 关任务

```bash
python scripts/generate-memory-report.py <ID> "<标题>" --no-send-tg
```
