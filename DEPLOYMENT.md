# Code Audit Skill 部署与使用手册

本文档说明如何将 **Code Audit Skill** 上传到 GitHub、完成 Telegram 配置，并在业务仓库中接入使用。

---

## 目录

1. [部署架构说明](#1-部署架构说明)
2. [前置准备](#2-前置准备)
3. [上传到 GitHub](#3-上传到-github)
4. [发布 Action 版本](#4-发布-action-版本)
5. [Telegram Bot 配置](#5-telegram-bot-配置)
6. [填写 Bot Token（Secrets 配置）](#6-填写-bot-tokensecrets-配置)
7. [在本仓库验证（自测）](#7-在本仓库验证自测)
8. [业务仓库接入](#8-业务仓库接入)
9. [配置分支保护](#9-配置分支保护)
10. [日常使用操作](#10-日常使用操作)
11. [全部参数说明](#11-全部参数说明)
12. [制品与 TG 通知说明](#12-制品与-tg-通知说明)
13. [常见问题](#13-常见问题)

---

## 1. 部署架构说明

本方案分为 **两个仓库**：

| 仓库类型 | 作用 | 你需要做什么 |
|----------|------|--------------|
| **Skill 仓库**（本仓库） | 存放 Composite Action 通用审计逻辑 | 上传 GitHub、打 tag、配置 Secrets、跑自测 |
| **业务仓库** | 你的实际项目代码 | 添加几行 workflow 引用 Skill 仓库 |

```
┌─────────────────────┐         uses: YOUR_ORG/code-audit-skill@v1
│   业务仓库           │ ──────────────────────────────────────────►
│  .github/workflows/  │
└─────────────────────┘
                              ┌─────────────────────┐
                              │  code-audit-skill   │
                              │  action.yml         │
                              │  scripts/           │
                              │  config/            │
                              └─────────────────────┘
                                        │
                                        ▼
                              Telegram 群组推送结果
```

---

## 2. 前置准备

### 2.1 账号与工具

- [ ] [GitHub 账号](https://github.com/signup)
- [ ] 本机已安装 [Git](https://git-scm.com/downloads)
- [ ] （可选）[GitHub CLI](https://cli.github.com/)：`gh` 命令

### 2.2 Telegram 准备

- [ ] 已创建 Telegram Bot（通过 @BotFather）
- [ ] 已将 Bot 拉入目标群组
- [ ] 已获取 **Bot Token** 和 **群组 Chat ID**

测试环境参考（你的测试群）：

| 项目 | 值 |
|------|-----|
| Bot 用户名 | `@test_skills_yh_bot` |
| 群组 Chat ID | `-5342457001` |
| Bot Token | 从 @BotFather 获取，**仅填入 GitHub Secrets** |

> ⚠️ **安全要求**：Bot Token 禁止写入代码、workflow 明文或提交到 Git 仓库，只能通过 GitHub Secrets 传入。

---

## 3. 上传到 GitHub

### 方式 A：GitHub 网页创建仓库后推送（推荐）

#### 步骤 1：在 GitHub 创建空仓库

1. 打开 [https://github.com/new](https://github.com/new)
2. **Repository name** 填写：`code-audit-skill`（或你喜欢的名称）
3. 选择 **Public**（Public 仓库才能让其他仓库免费引用 Action）
4. **不要**勾选 "Add a README file"（本地已有代码）
5. 点击 **Create repository**

#### 步骤 2：本地初始化并推送

在项目根目录 `e:\AIskiils` 打开终端，执行：

```bash
# 进入项目目录
cd e:\AIskiils

# 初始化 Git（若尚未初始化）
git init

# 添加所有文件
git add .

# 首次提交
git commit -m "feat: 初始化 Code Audit Skill 可复用审计 Action"

# 关联远程仓库（将 YOUR_USERNAME 替换为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/code-audit-skill.git

# 推送到 main 分支
git branch -M main
git push -u origin main
```

推送时如提示登录，使用 GitHub Personal Access Token 作为密码（非 GitHub 登录密码）。

#### 步骤 3：生成 Personal Access Token（若尚未有）

1. GitHub → 右上角头像 → **Settings**
2. 左侧最底部 **Developer settings**
3. **Personal access tokens** → **Tokens (classic)** → **Generate new token**
4. 勾选 `repo` 权限
5. 生成后**复制保存**（只显示一次）

---

### 方式 B：使用 GitHub CLI 一键创建并推送

```bash
cd e:\AIskiils
git init
git add .
git commit -m "feat: 初始化 Code Audit Skill"

# 登录（首次）
gh auth login

# 创建远程仓库并推送
gh repo create code-audit-skill --public --source=. --remote=origin --push
```

---

### 方式 C：GitHub 网页直接上传（小项目/quick start）

1. 创建空仓库后，点击 **Add file** → **Upload files**
2. 将本地 `e:\AIskiils` 下所有文件拖入
3. 点击 **Commit changes**

> 适合快速体验，后续仍建议用 Git 管理版本。

---

## 4. 发布 Action 版本

业务仓库通过 **tag** 引用本 Action，必须发布版本标签。

### 步骤 1：创建并推送 tag

```bash
cd e:\AIskiils

# 创建版本标签
git tag -a v1.0.0 -m "Release v1.0.0: 代码审计 Skill 首个稳定版"

# 推送标签到 GitHub
git push origin v1.0.0

# 建议同时推送一个主版本标签（方便业务仓库写 @v1）
git tag -a v1 -m "Release v1" -f
git push origin v1 --force
```

### 步骤 2：在 GitHub 创建 Release（可选但推荐）

1. 打开仓库页面 → 右侧 **Releases**
2. 点击 **Create a new release**
3. **Choose a tag** 选择 `v1.0.0`
4. **Release title** 填写：`v1.0.0`
5. 点击 **Publish release**

### 业务仓库引用格式

```yaml
uses: YOUR_USERNAME/code-audit-skill@v1
# 或精确版本：
uses: YOUR_USERNAME/code-audit-skill@v1.0.0
# 或 main 分支（不推荐生产环境）：
uses: YOUR_USERNAME/code-audit-skill@main
```

---

## 5. Telegram Bot 配置

### 5.1 创建 Bot（若尚未创建）

1. 在 Telegram 搜索 **@BotFather**
2. 发送 `/newbot`
3. 按提示设置 Bot 名称和用户名（如 `@test_skills_yh_bot`）
4. BotFather 返回 **Bot Token**，格式类似：
   ```
   1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. **立即保存 Token**，后续填入 GitHub Secrets

### 5.2 将 Bot 加入群组

1. 打开目标 Telegram 群组
2. 点击群组名称 → **Add members**
3. 搜索并添加你的 Bot（如 `@test_skills_yh_bot`）
4. 建议给 Bot **发送消息**权限

### 5.3 获取群组 Chat ID

**方法 1：通过 getUpdates API**

1. 在群组中发送一条消息（如 `hello`）
2. 浏览器访问（将 `YOUR_BOT_TOKEN` 替换为真实 Token，仅本地查看，勿泄露）：
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
3. 在返回 JSON 中找到：
   ```json
   "chat": {
     "id": -5342457001,
     "title": "你的群组名",
     "type": "group"
   }
   ```
4. `id` 即为 **Chat ID**（群组一般为负数）

**方法 2：使用 @userinfobot 或 @getidsbot**

将 Bot 拉入群后，部分第三方 Bot 可直接显示群组 ID。

---

## 6. 填写 Bot Token（Secrets 配置）

Bot Token 和 Chat ID 需要配置在 **GitHub Secrets** 中，workflow 通过 `${{ secrets.XXX }}` 引用。

### 6.1 在 Skill 仓库配置（用于自测）

1. 打开 Skill 仓库：`https://github.com/YOUR_USERNAME/code-audit-skill`
2. 点击 **Settings**（仓库设置，非账号设置）
3. 左侧菜单 **Secrets and variables** → **Actions**
4. 点击 **New repository secret**，依次添加：

| Name（名称，必须完全一致） | Secret（值） | 说明 |
|---------------------------|--------------|------|
| `TG_BOT_TOKEN` | `你的 Bot Token` | 从 @BotFather 获取，形如 `1234567890:AAH...` |
| `TG_CHAT_ID` | `-5342457001` | 群组 ID，负数表示群组 |

![Secrets 位置示意](https://docs.github.com/assets/cb-28266/mw-1440/images/help/repository/actions-secret-repository.webp)

### 6.2 在业务仓库配置（用于实际项目审计）

若业务仓库与 Skill 仓库不同，**业务仓库也需要配置相同的 Secrets**：

1. 打开业务仓库 → **Settings** → **Secrets and variables** → **Actions**
2. 同样添加 `TG_BOT_TOKEN` 和 `TG_CHAT_ID`

### 6.3 workflow 引用（v1.0.0 企业级）

```yaml
- uses: YOUR_ORG/code-audit-skill@v1.0.0
  with:
    audit-preset: security
    enable-sarif: 'true'
    enable-telegram: 'true'
    telegram-bot-token: ${{ secrets.TG_BOT_TOKEN }}
    telegram-chat-id: ${{ secrets.TG_CHAT_ID }}
```

`config/telegram.yaml` 仅保留推送开关；**Token 仅通过 Secrets / 环境变量 / telegram.local.yaml（本地）**。

详见 [SECURITY.md](../SECURITY.md)。

### 6.4 安全清单

- [ ] Token 未出现在任何 `.yml`、`.sh`、`.py` 源文件中
- [ ] Token 未出现在 Git 提交历史中
- [ ] `.gitignore` 已忽略 `.env` 等本地密钥文件
- [ ] 若 Token 曾泄露，立即在 @BotFather 发送 `/revoke` 重新生成

---

## 7. 在本仓库验证（自测）

Skill 仓库上传并配置 Secrets 后，先跑自测确认一切正常。

### 步骤 1：确认自测 workflow 存在

仓库内已有：`.github/workflows/self-test.yml`

### 步骤 2：手动触发全场景测试

1. 打开 Skill 仓库 → **Actions** 标签页
2. 左侧选择 **Self Test - All Scenarios**
3. 点击 **Run workflow**
4. **scenario** 选择 `all`
5. 点击绿色 **Run workflow** 按钮

### 步骤 3：查看运行结果

1. 点击正在运行的 workflow
2. 观察各 scenario job 状态（正常/空项目/多语言/违规代码等）
3. 点击某个 job → 展开步骤日志

### 步骤 4：检查制品

1. 在 run 页面底部 **Artifacts** 区域
2. 下载 `code-audit-logs-{run_id}`
3. 解压查看：
   - `audit-summary.json` — 审计汇总
   - `test-cases.json` / `test-cases.md` — 验收测试用例
   - `gitleaks.log`、`bandit.log` 等 — 各模块日志

### 步骤 5：检查 Telegram 通知

若 Secrets 配置正确，测试群应收到类似消息：

```
✅ 代码审计与验收测试全部通过 🎉

━━━ 审计概览 ━━━
仓库: YOUR_USERNAME/code-audit-skill
...

━━━ 验收测试用例 ━━━
通过率: 8/8
✅ TC-AUDIT-001 语言与结构检测: 是
...
```

---

## 8. 业务仓库接入

### 步骤 1：在业务仓库创建 workflow 文件

在业务仓库创建 `.github/workflows/code-audit.yml`：

```yaml
name: Code Audit

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      working-directory:
        description: '审计目录'
        required: false
        default: '.'

permissions:
  contents: read
  pull-requests: read

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: 检出代码
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: 运行代码审计 Skill
        uses: YOUR_USERNAME/code-audit-skill@v1    # ← 改成你的 Skill 仓库路径
        with:
          working-directory: ${{ github.event.inputs.working-directory || '.' }}
          fail-on-findings: 'true'

          # 扫描模块开关
          enable-gitleaks: 'true'
          enable-super-linter: 'true'
          enable-bandit: 'true'
          enable-dependency-scan: 'true'
          enable-custom-rules: 'true'
          enable-test-cases: 'true'

          # Telegram 通知（Token 从 Secrets 读取）
          enable-telegram: 'true'
          telegram-bot-token: ${{ secrets.TG_BOT_TOKEN }}
          telegram-chat-id: ${{ secrets.TG_CHAT_ID }}
          telegram-bot-username: '@test_skills_yh_bot'
```

> 将 `YOUR_USERNAME` 替换为你的 GitHub 用户名或组织名。

也可直接复制仓库内 [`examples/consumer-workflow.yml`](examples/consumer-workflow.yml) 修改后使用。

### 步骤 2：在业务仓库配置 Secrets

重复 [第 6 节](#6-填写-bot-tokensecrets-配置) 的 Secrets 配置。

### 步骤 3：提交并推送

```bash
cd your-business-repo
git add .github/workflows/code-audit.yml
git commit -m "ci: 接入 Code Audit Skill"
git push
```

### 步骤 4：验证首次运行

1. 推送后自动触发（`on: push`）
2. 打开业务仓库 **Actions** 查看 **Code Audit** workflow
3. 确认运行成功，Telegram 收到通知

### 步骤 5：跨仓库引用权限说明

| Skill 仓库可见性 | 业务仓库能否引用 |
|------------------|------------------|
| **Public** | ✅ 任意仓库可引用 |
| **Private** | 仅同一组织内或需配置 PAT，较复杂 |

**建议**：Skill 仓库设为 **Public**，代码中不含任何密钥。

---

## 9. 配置分支保护

让高危漏洞**阻断 PR 合并**：

### 步骤 1：开启分支保护

1. 业务仓库 → **Settings** → **Branches**
2. 点击 **Add branch protection rule**（或编辑已有规则）
3. **Branch name pattern** 填写：`main`

### 步骤 2：配置 Required checks

1. 勾选 **Require status checks to pass before merging**
2. 勾选 **Require branches to be up to date before merging**（推荐）
3. 在搜索框输入 `audit` 或 `Code Audit`，勾选对应 job
4. 点击 **Save changes**

### 步骤 3：确认 fail-on-findings 已开启

业务 workflow 中确保：

```yaml
fail-on-findings: 'true'
```

当 gitleaks / bandit / 自定义规则等发现高危问题时，Action 失败 → PR 无法合并 → Telegram 收到失败通知。

---

## 10. 日常使用操作

### 10.1 自动触发（push / PR）

| 事件 | 触发条件 | 说明 |
|------|----------|------|
| `push` | 推送到 `main`/`develop` | 自动审计 |
| `pull_request` | 向 `main` 提 PR | 自动审计，可配合分支保护 |
| `workflow_dispatch` | 手动触发 | 见下方 |

### 10.2 手动触发审计

1. 仓库 → **Actions** → 选择 **Code Audit**
2. **Run workflow**
3. 可选填写 **working-directory**（子目录审计）
4. 点击 **Run workflow**

### 10.3 查看审计报告

1. **Actions** → 点击某次运行
2. 底部 **Artifacts** → 下载 `code-audit-logs-{run_id}`
3. 重点文件：

| 文件 | 内容 |
|------|------|
| `audit-summary.json` | 各模块状态、问题总数 |
| `test-cases.md` | 验收测试用例表格 |
| `gitleaks-report.json` | 密钥泄露详情 |
| `bandit-report.json` | Python 安全问题 |
| `trivy-report.json` | 依赖漏洞 |
| `custom-rules-report.json` | 业务规则违规 |

### 10.4 关闭某个扫描模块

在 workflow `with` 中修改：

```yaml
enable-super-linter: 'false'   # 关闭规范检查
enable-telegram: 'false'       # 关闭 TG 通知
enable-test-cases: 'false'     # 关闭验收测试用例
```

### 10.5 更新 Skill 版本

Skill 仓库发布新版本后，业务仓库修改引用：

```yaml
uses: YOUR_USERNAME/code-audit-skill@v1.1.0
```

提交推送即可生效。

---

## 11. 全部参数说明

### 11.1 workflow `with` 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `working-directory` | `.` | 审计目标子目录 |
| `fail-on-findings` | `true` | 发现问题时令 Action 失败 |
| `upload-artifacts` | `true` | 上传日志制品 |
| `artifact-retention-days` | `14` | 制品保留天数 |
| `enable-gitleaks` | `true` | 敏感密钥扫描 |
| `enable-super-linter` | `true` | 多语言规范检查 |
| `enable-bandit` | `true` | Python 安全扫描 |
| `enable-dependency-scan` | `true` | 依赖漏洞检测 |
| `enable-custom-rules` | `true` | 自定义业务规则 |
| `enable-test-cases` | `true` | 验收测试用例生成与执行 |
| `enable-telegram` | `false` | Telegram 通知 |
| `telegram-bot-token` | — | `${{ secrets.TG_BOT_TOKEN }}` |
| `telegram-chat-id` | — | `${{ secrets.TG_CHAT_ID }}` |
| `telegram-bot-username` | — | 如 `@test_skills_yh_bot` |
| `gitleaks-config` | 内置 | 自定义 gitleaks 配置路径 |
| `custom-rules-path` | 内置 | 自定义业务规则 YAML 路径 |
| `ignore-paths-file` | 内置 | 额外忽略路径配置 |
| `super-linter-languages` | 自动检测 | 如 `Python, YAML, JavaScript` |

> 布尔参数支持 `true`/`false`/`1`/`0`/`yes`/`no`，大小写不敏感。

### 11.2 Action 输出

| 输出 | 说明 |
|------|------|
| `audit-status` | `success` / `failure` / `skipped` |
| `findings-count` | 问题总数 |
| `results-json` | 汇总 JSON 路径 |
| `test-cases-passed` | 通过的测试用例数 |
| `test-cases-failed` | 失败的测试用例数 |
| `test-cases-all-passed` | 是否全部通过 |

### 11.3 GitHub Secrets 汇总

| Secret 名称 | 填写位置 | 值来源 |
|-------------|----------|--------|
| `TG_BOT_TOKEN` | Skill 仓库 + 业务仓库 Secrets | @BotFather |
| `TG_CHAT_ID` | Skill 仓库 + 业务仓库 Secrets | getUpdates API / 第三方 Bot |

---

## 12. 制品与 TG 通知说明

### 12.1 执行流程

```
初始化 → 语言检测 → 各模块扫描 → 汇总审计
    → 生成测试用例 → 执行测试用例 → 上传制品 → TG 汇总通知
```

### 12.2 TG 通知内容

通知在**审计 + 测试用例全部完成**后发送，包含：

- 审计状态（通过 / 未通过）
- 各扫描模块结果（gitleaks、bandit 等）
- 验收测试用例通过率
- 每条 TC 的通过/失败状态
- Actions 运行链接

### 12.3 TG 发送失败时

- 不影响审计主流程（已设置 `continue-on-error`）
- 检查 Secrets 是否正确、Bot 是否在群内、Token 是否过期
- 查看制品中 `telegram.log`

---

## 13. 常见问题

### Q1：推送时提示 Authentication failed

使用 Personal Access Token 代替密码，或执行 `gh auth login` 重新登录。

### Q2：业务仓库引用 Action 报错 "Unable to resolve action"

- 确认 Skill 仓库为 **Public**
- 确认 tag `v1` 已推送：`git push origin v1`
- 检查 `uses:` 路径用户名/仓库名是否正确

### Q3：Telegram 收不到消息

**按顺序排查：**

1. **Actions 日志里是否有「推送 Telegram 通知」步骤？**
   - 若没有 → workflow 未设置 `enable-telegram: 'true'`（Action 默认为 `false`）
   - 若步骤被跳过 → 检查 init 日志中 `tg=true` 是否为 true

2. **初始化日志是否出现警告？**
   ```
   Telegram 已启用但 token/chat_id 为空
   ```
   → 去 **Settings → Secrets → Actions** 添加 `TG_BOT_TOKEN`、`TG_CHAT_ID`（名称必须完全一致）

3. **「推送 Telegram 通知」步骤日志**
   - 查看 `TG 诊断: token已设置=... chat_id已设置=...`
   - `token已设置=false` → Secret 未配置或未传入 workflow

4. **下载制品 `code-audit-logs-{run_id}`**
   - `telegram.log` — curl 响应与 http_code
   - `telegram-diagnostic.json` — 结构化诊断

5. **常见 API 错误**
   | error_code | 原因 | 处理 |
   |------------|------|------|
   | 401 | Token 无效 | @BotFather `/revoke` 重新生成，更新 Secret |
   | 400 | Chat ID 错误 | 用 getUpdates 确认群组 ID（负数） |
   | 403 | Bot 无权限 | 将 Bot 拉入群并赋予发言权限 |

6. **Fork PR** — 来自 fork 的 PR 无法读取 Secrets，TG 不会发送

### Q4：空项目或纯 JS 项目报 bandit 错误

正常行为：无 Python 代码时 bandit 自动跳过。查看 `detect-languages.json` 确认 `has_python: false`。

### Q5：如何只审计子目录？

```yaml
working-directory: 'src/backend'
```

或手动触发时填写 `working-directory` 输入框。

### Q6：如何更新 Skill 而不影响业务仓库？

使用主版本 tag 引用 `@v1`，小版本更新时重新打 `v1` tag 指向新 commit；或使用精确版本 `@v1.0.1` 手动升级。

### Q7：Token 误提交到 Git 怎么办？

1. 立即在 @BotFather 执行 `/revoke` 重新生成 Token
2. 更新 GitHub Secrets 为新 Token
3. 使用 `git filter-repo` 或 BFG 清除历史中的密钥

---

## 快速检查清单

部署完成后，逐项确认：

- [ ] Skill 仓库已推送到 GitHub（Public）
- [ ] 已打 tag `v1` / `v1.0.0` 并推送
- [ ] Skill 仓库 Secrets 已配置 `TG_BOT_TOKEN`、`TG_CHAT_ID`
- [ ] 自测 workflow **Self Test - All Scenarios** 全部通过
- [ ] Telegram 测试群收到自测通知
- [ ] 业务仓库已添加 `code-audit.yml`
- [ ] 业务仓库 Secrets 已配置
- [ ] 业务仓库 `uses:` 路径已改为实际 Skill 仓库
- [ ] push 后 Actions 自动运行成功
- [ ] （可选）分支保护已配置 Required checks

---

## 相关文档

- [README.md](README.md) — 功能概览与架构
- [examples/consumer-workflow.yml](examples/consumer-workflow.yml) — 业务仓库接入模板
- [.github/SECRETS.example.md](.github/SECRETS.example.md) — Secrets 简要说明
