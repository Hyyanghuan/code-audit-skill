# Security Policy

## 支持的版本

| 版本 | 支持 |
|------|------|
| 1.0.x | ✅ |
| < 1.0 | ❌ |

## 报告漏洞

请勿在公开 Issue 中提交可利用的安全漏洞。请通过私有渠道联系维护者。

## 密钥与凭证（企业必读）

### 禁止提交

- Telegram Bot Token
- Chat ID 与 Token 组合的可复现凭证
- 任何 `.env`、`*secret*`、`*token*` 文件

### 推荐配置（优先级从高到低）

1. **GitHub Actions Secrets**（生产必选）

   在 Skill 仓或业务仓：`Settings → Secrets → Actions`

   | Secret | 说明 |
   |--------|------|
   | `TG_BOT_TOKEN` | @BotFather 获取 |
   | `TG_CHAT_ID` | 群组 ID（负数） |

   ```yaml
   - uses: YOUR_ORG/code-audit-skill@v1.0.0
     with:
       telegram-bot-token: ${{ secrets.TG_BOT_TOKEN }}
       telegram-chat-id: ${{ secrets.TG_CHAT_ID }}
   ```

2. **本地开发**：复制 `config/telegram.yaml.example` → `config/telegram.local.yaml`（已 gitignore）

3. **环境变量**：`TG_BOT_TOKEN`、`TG_CHAT_ID`

4. **config/telegram.yaml**：仅保留 `enabled` 与推送开关，**bot_token/chat_id 留空**

### Token 泄露处置

1. @BotFather → `/revoke` 轮换 Token  
2. 从 Git 历史清除（如 `git filter-repo`）  
3. 检查 Telegram 群异常消息  

## 权限最小化

业务仓 workflow 建议：

```yaml
permissions:
  contents: read
  pull-requests: read
  # security-events: write  # 仅在上传 SARIF 到 Code Scanning 时需要
```

## 依赖与供应链

- 运行时依赖：gitleaks、trivy、bandit、super-linter（Actions 运行时安装）
- 定期更新 `config/gitleaks.toml` 与 `sast-patterns.yaml`
- 生产引用 **tag/SHA**，避免裸 `@main`

## 安全相关文件

- [config/telegram.yaml.example](../config/telegram.yaml.example)
- [docs/GUIDANCE.md](docs/GUIDANCE.md) §四 风险清单
