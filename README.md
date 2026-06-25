# Code Audit Skill

可复用的 GitHub Actions **Composite Action** 代码审计 Skill。独立仓库存放通用审计逻辑，业务仓库仅需几行 workflow 即可接入；支持 **14 个扫描模块**、**验收测试用例自动生成**、**Bug MD 报告** 与 **Telegram 群推送**。

---

## 目录

- [架构说明](#架构说明)
- [快速接入（5 步）](#快速接入5-步)
- [Telegram 写死配置方案](#telegram-写死配置方案)
- [第三方引用时如何配置 TG](#第三方引用时如何配置-tg)
- [完整配置参考](#完整配置参考)
- [审计能力覆盖](#审计能力覆盖)
- [执行流程](#执行流程)
- [制品与 TG 推送内容](#制品与-tg-推送内容)
- [分支保护与触发条件](#分支保护与触发条件)
- [目录结构](#目录结构)
- [本地自测](#本地自测)
- [更多文档](#更多文档)

---

## 架构说明

```
┌─────────────────────┐      uses: YOUR_ORG/code-audit-skill@main
│   业务仓库           │ ─────────────────────────────────────────►
│  .github/workflows/  │              仅需 3~10 行配置
└─────────────────────┘
                              ┌──────────────────────────┐
                              │   code-audit-skill 仓库   │
                              │   action.yml              │
                              │   scripts/  config/         │
                              └──────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              14 模块扫描          测试用例/Bug 报告      Telegram 群
```

| 仓库 | 作用 |
|------|------|
| **Skill 仓库**（本仓库） | 存放 Composite Action、规则、脚本 |
| **业务仓库** | 添加 workflow 引用 Skill，无需复制脚本 |

> **版本引用**：统一使用 `@main` 跟踪主干最新能力。生产环境若需锁定版本，可改用 commit SHA。

---

## 快速接入（5 步）

### 第 1 步：确保 Skill 仓库已发布到 GitHub

将本仓库推送到 GitHub，并设为 **Public**（公开仓库可被任意项目免费引用 Action）。

```bash
git remote add origin https://github.com/YOUR_USERNAME/code-audit-skill.git
git branch -M main
git push -u origin main
```

### 第 2 步：配置 Telegram（Skill 仓库内写死）

编辑 Skill 仓库中的 [`config/telegram.yaml`](config/telegram.yaml)（详见 [Telegram 写死配置方案](#telegram-写死配置方案)）。

> 业务仓库引用本 Action 时，TG 配置从 **Skill 仓库** 的 `config/telegram.yaml` 读取，业务仓**无需**再配 Secrets。

### 第 3 步：业务仓库添加 workflow

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
        description: '审计子目录'
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
          fetch-depth: 0   # 差分审计需要完整 git 历史

      - name: 运行代码审计 Skill
        uses: YOUR_USERNAME/code-audit-skill@main   # ← 改用户名，引用主干
        with:
          working-directory: ${{ github.event.inputs.working-directory || '.' }}
          fail-on-findings: 'true'
          enable-telegram: 'true'
```

将 `YOUR_USERNAME` 替换为你的 GitHub 用户名或组织名。

### 第 4 步：推送并验证

```bash
git add .github/workflows/code-audit.yml
git commit -m "ci: 接入 Code Audit Skill"
git push
```

打开 **Actions** 标签页，确认 `Code Audit` workflow 运行成功；Telegram 群应收到审计摘要通知。

### 第 5 步：（可选）配置分支保护

**Settings → Branches → Branch protection rules**：

1. 勾选 **Require status checks to pass before merging**
2. 添加 Required check：`audit`（与 job 名一致）
3. 保持 `fail-on-findings: 'true'`，高危漏洞将阻断 PR 合并

---

## Telegram 写死配置方案

本 Skill 将 TG 配置**直接写在 Skill 仓库代码中**，无需 GitHub Secrets，改配置后 push 即生效。

### 配置文件位置

```
config/telegram.yaml
```

### 配置示例

```yaml
# 是否启用 TG 通知
enabled: true

# Bot Token（从 @BotFather 获取）
bot_token: "你的BotToken"

# 群组/频道 Chat ID（群组一般为负数）
chat_id: "-1004400849148"

# Bot 用户名（仅展示用，可选）
bot_username: "@test_skills_yh_bot"

# ── 推送选项 ──
send_summary_message: true    # 文字摘要
send_test_cases_md: true      # 测试用例 MD 文档
send_bug_report_md: true      # 有 Bug 时发送 audit-bugs.md
send_audit_logs: true         # 合并运行日志
max_log_size_kb: 5000         # 日志体积上限（KB），超出截断
```

### 配置优先级

```
workflow with 参数  >  环境变量  >  config/telegram.yaml 写死值
```

业务仓库 workflow 中**可不传** `telegram-bot-token` / `telegram-chat-id`，自动读取 Skill 仓库内 yaml。

若需临时覆盖（如测试群），可在 workflow 中显式传入：

```yaml
with:
  telegram-bot-token: '临时Token'
  telegram-chat-id: '-123456789'
```

### 获取 Chat ID 方法

1. 将 Bot 拉入目标群组
2. 在群内发一条消息
3. 浏览器访问：`https://api.telegram.org/bot<TOKEN>/getUpdates`
4. 在返回 JSON 中找到 `"chat":{"id": -100xxxxxxxxxx}`

### TG 推送内容一览

| 条件 | 推送内容 |
|------|----------|
| 每次运行 | 文字摘要（仓库、分支、审计状态、问题数、Bug 数） |
| 有 Bug | `[BUG ALERT]` 告警 + `audit-bugs.md` 附件 |
| 默认开启 | `test-cases.md` 测试用例报告 |
| 默认开启 | `manual-audit-checklist.md` 人工审计清单 |
| 默认开启 | `audit-logs-combined.txt` 全量运行日志 |

---

## 第三方引用时如何配置 TG

业务仓库通过 `uses: YOUR_ORG/code-audit-skill@main` 引用本 Skill 时，TG 配置的读取与填写方式如下。

### 核心原理

Composite Action 运行时，`config/telegram.yaml` 从 **Skill 仓库**加载（路径由 `GITHUB_ACTION_PATH` 决定），**不是**从业务仓库加载：

```
业务仓库 workflow
  uses: YOUR_ORG/code-audit-skill@main
         ↓
  实际读取 Skill 仓库内的 config/telegram.yaml
```

因此：**在 Skill 仓库配好 TG，所有第三方引用方默认共用同一套配置**，业务仓通常无需额外配置。

### 配置优先级

```
workflow with 参数（业务仓传入）  >  config/telegram.yaml（Skill 仓写死值）
```

### 方式一：零配置（推荐，Skill 仓统一通知群）

**适用**：全公司 / 全团队共用一个 TG 通知群。

**步骤 1**：在 **Skill 仓库**编辑 [`config/telegram.yaml`](config/telegram.yaml) 并 push 到 `main`：

```yaml
enabled: true
bot_token: "你的BotToken"
chat_id: "-1004400849148"
bot_username: "@test_skills_yh_bot"
```

**步骤 2**：业务仓库 workflow **只写**：

```yaml
- uses: YOUR_ORG/code-audit-skill@main
  with:
    enable-telegram: 'true'   # 可省略，默认已是 true
```

无需在业务仓配置 Secrets，无需传 `telegram-bot-token`。

### 方式二：业务仓单独覆盖（每个项目不同 TG 群）

**适用**：某个业务项目要推送到**自己的** Telegram 群。

**步骤 1**：在 **业务仓库**配置 Secrets：

`Settings → Secrets and variables → Actions → New repository secret`

| Secret 名称 | 值 |
|-------------|-----|
| `TG_BOT_TOKEN` | 从 @BotFather 获取的 Bot Token |
| `TG_CHAT_ID` | 群组 Chat ID（群组一般为负数） |

**步骤 2**：业务仓库 workflow 显式传入（会覆盖 Skill 仓写死配置）：

```yaml
- uses: YOUR_ORG/code-audit-skill@main
  with:
    enable-telegram: 'true'
    telegram-bot-token: ${{ secrets.TG_BOT_TOKEN }}
    telegram-chat-id: ${{ secrets.TG_CHAT_ID }}
    telegram-bot-username: '@your_bot'
```

### 方式三：workflow 明文传入（仅本地测试）

```yaml
with:
  enable-telegram: 'true'
  telegram-bot-token: '1234567890:AAH...'
  telegram-chat-id: '-1004400849148'
```

> 不推荐用于生产环境，Token 可能暴露在 workflow 文件或日志中。

### 配置方式对照表

| 场景 | 谁配置 TG | 业务仓 workflow | 业务仓 Secrets |
|------|-----------|-----------------|----------------|
| 全团队统一通知群 | **Skill 仓** `config/telegram.yaml` | 仅 `enable-telegram: true` | 不需要 |
| 每个项目独立通知群 | 业务仓 Secrets | 传 `telegram-bot-token` / `chat-id` | 需要 |
| 临时测试群 | workflow 参数 | 明文或 Secrets 传入 | 可选 |
| 关闭 TG 通知 | 业务仓 workflow | `enable-telegram: 'false'` | — |

### 业务仓完整示例（两种方案）

```yaml
name: Code Audit

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      # 方案 A：使用 Skill 仓统一 TG（推荐，零配置）
      - uses: YOUR_ORG/code-audit-skill@main
        with:
          fail-on-findings: 'true'
          enable-telegram: 'true'

      # 方案 B：本项目使用独立 TG 群（需先配置 Secrets）
      # - uses: YOUR_ORG/code-audit-skill@main
      #   with:
      #     fail-on-findings: 'true'
      #     enable-telegram: 'true'
      #     telegram-bot-token: ${{ secrets.TG_BOT_TOKEN }}
      #     telegram-chat-id: ${{ secrets.TG_CHAT_ID }}
```

### 注意事项

1. **Bot 必须加入目标群**：将 Bot 拉入群组并赋予发消息权限，否则 API 返回 403。
2. **Skill 仓库建议 Public**：公开仓库可被任意项目引用；私有仓库需额外授权。
3. **Fork PR 限制**：来自 fork 的 PR 无法读取业务仓 Secrets，方式二在 fork PR 场景下 TG 可能发送失败。
4. **修改生效**：改 Skill 仓 `config/telegram.yaml` 后 push 到 `main`，所有引用 `@main` 的项目下次运行即生效。

---

## 完整配置参考

### workflow `with` 参数（全部）

#### 基础参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `working-directory` | `.` | 审计目标子目录 |
| `fail-on-findings` | `true` | 发现问题时令 Action 失败（配合分支保护） |
| `upload-artifacts` | `true` | 上传审计日志制品 |
| `artifact-retention-days` | `14` | 制品保留天数 |

#### 扫描模块开关（均为 `true`，支持 `true/false/1/0/yes/no`，大小写不敏感）

| 参数 | 模块 |
|------|------|
| `enable-gitleaks` | Gitleaks 敏感密钥扫描 |
| `enable-super-linter` | Super-Linter 多语言规范 |
| `enable-bandit` | Bandit Python 安全 |
| `enable-dependency-scan` | Trivy 依赖漏洞 SCA |
| `enable-custom-rules` | 自定义业务规则 YAML |
| `enable-sast-patterns` | SAST 词法/语法扫描 |
| `enable-taint-analysis` | SAST 污点分析 Source→Sink |
| `enable-control-flow` | SAST 控制流分析 |
| `enable-config-audit` | 配置文件审计（yml/Dockerfile） |
| `enable-specialized-security` | 专项安全（越权/上传/业务风险） |
| `enable-diff-audit` | git diff 版本差分审计 |
| `enable-coverage-audit` | 覆盖率驱动审计 |
| `enable-runtime-audit` | DAST/IAST 运行时建议 |
| `enable-manual-checklist` | 人工深度审计清单 |
| `enable-test-cases` | 验收测试用例生成与执行 |

#### Telegram 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `enable-telegram` | `true` | 启用 TG 推送 |
| `telegram-bot-token` | 空 | 留空则读 `config/telegram.yaml` |
| `telegram-chat-id` | 空 | 留空则读 `config/telegram.yaml` |
| `telegram-bot-username` | 空 | 留空则读 `config/telegram.yaml` |

#### 工具配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `gitleaks-config` | 内置 | 自定义 gitleaks 配置路径 |
| `custom-rules-path` | 内置 | 自定义业务规则 YAML 路径 |
| `ignore-paths-file` | 内置 | 额外忽略路径配置 |
| `super-linter-languages` | 自动检测 | 如 `Python, YAML, JavaScript` |

### Action 输出

| 输出 | 说明 |
|------|------|
| `audit-status` | `success` / `failure` / `skipped` |
| `findings-count` | 问题总数 |
| `results-json` | 汇总 JSON 路径 |
| `test-cases-passed` | 通过的测试用例数 |
| `test-cases-failed` | 失败的测试用例数 |
| `test-cases-all-passed` | 是否全部通过 |

### 仓库内配置文件

| 文件 | 作用 |
|------|------|
| [`config/telegram.yaml`](config/telegram.yaml) | **TG 写死配置**（Token/ChatID/推送开关） |
| [`config/audit-methods.yaml`](config/audit-methods.yaml) | 六大类审计方法目录与模块映射 |
| [`config/sast-patterns.yaml`](config/sast-patterns.yaml) | 词法规则、污点 Source/Sink、控制流、专项安全规则 |
| [`config/custom-rules/business-rules.yaml`](config/custom-rules/business-rules.yaml) | 自定义业务规则（eval/硬编码密码/SQL 拼接等） |
| [`config/gitleaks.toml`](config/gitleaks.toml) | Gitleaks 密钥扫描规则 |
| [`config/ignore-paths.txt`](config/ignore-paths.txt) | 默认忽略目录（node_modules/dist 等） |

### 最小接入 vs 完整接入

**最小接入**（推荐）：

```yaml
- uses: YOUR_USERNAME/code-audit-skill@main
  with:
    fail-on-findings: 'true'
    enable-telegram: 'true'
```

**完整接入**（按需关闭模块）：

```yaml
- uses: YOUR_USERNAME/code-audit-skill@main
  with:
    working-directory: '.'
    fail-on-findings: 'true'
    enable-gitleaks: 'true'
    enable-bandit: 'true'
    enable-sast-patterns: 'true'
    enable-taint-analysis: 'true'
    enable-diff-audit: 'true'
    enable-test-cases: 'true'
    enable-telegram: 'true'
    super-linter-languages: 'Python, JavaScript, YAML'
```

---

## 审计能力覆盖

### 一、静态代码审计 SAST

| 模块 | 方法 | 工具 |
|------|------|------|
| 词法/语法扫描 | 危险函数、SQL 拼接、硬编码密钥 | `sast_patterns` |
| 污点分析 | Source→Sink 污染链 | `taint_analysis` |
| 控制流分析 | 异常吞没、鉴权空实现 | `control_flow` |
| 依赖组件 SCA | 第三方库 CVE | trivy `dependency_scan` |
| 配置文件审计 | yml/Dockerfile 明文密码 | `config_audit` |
| 代码规范 | 多语言 lint | super-linter |
| 敏感密钥 | API Key/Token 泄露 | gitleaks |
| Python 安全 | eval/SQL 注入等 | bandit |
| 业务规则 | 自定义 YAML 规则 | `custom_rules` |

### 二、动态代码审计 DAST/IAST

| 模块 | 说明 |
|------|------|
| `runtime_audit` | IAST/DAST/流量联动建议报告（CI 内生成建议，完整动态测试需预发环境） |

### 三、人工深度审计

| 模块 | 说明 |
|------|------|
| `manual_checklist` | 生成 `manual-audit-checklist.md` 可勾选清单 |

### 四、覆盖率驱动审计

| 模块 | 说明 |
|------|------|
| `coverage_audit` | 解析 `coverage.xml` / `lcov.info`，低覆盖率告警 |

### 五、专项安全审计

| 模块 | 说明 |
|------|------|
| `specialized_security` | 越权、文件上传、业务风险、日志脱敏 |

### 六、辅助配套审计

| 模块 | 说明 |
|------|------|
| `diff_audit` | git diff 增量变更审计 |
| 预提交门禁 | `fail-on-findings` + 分支保护阻断 PR |

---

## 执行流程

```
初始化 → 语言检测
    → 14 模块扫描（gitleaks/bandit/trivy/SAST/专项/差分/覆盖率/运行时）
    → 汇总审计结果
    → 人工审计清单
    → 生成验收测试用例 → 执行用例 → 回写结果
    → 生成 Bug 报告（audit-bugs.md）
    → 上传制品
    → Telegram 推送（摘要 + Bug MD + 测试用例 MD + 日志）
    → 失败判定（fail-on-findings）
```

**无对应代码自动跳过**：如无 Python 则跳过 bandit，空项目则跳过多数字模块，工具安装失败则降级不阻断主流程。

---

## 制品与 TG 推送内容

### Actions 制品（`code-audit-logs-{run_id}`）

| 文件 | 说明 |
|------|------|
| `audit-summary.json` | 各模块状态与问题汇总 |
| `audit-bugs.md` / `audit-bugs.json` | Bug 报告（含错误功能/代码/原因/修复建议） |
| `test-cases.md` / `test-cases.json` | 验收测试用例（九种设计方法 + 场景分类） |
| `manual-audit-checklist.md` | 人工深度审计清单 |
| `audit-logs-combined.txt` | 全量合并运行日志 |
| `gitleaks-report.json` | 密钥扫描明细 |
| `bandit-report.json` | Python 安全明细 |
| `*-report.json` | 各模块详细报告 |

### Bug 报告字段

| 字段 | 说明 |
|------|------|
| BUG-ID | 如 `BUG-0001` |
| 错误功能 | 检出问题的审计模块 |
| 功能描述 | 模块业务说明 |
| 错误代码 | 问题代码片段 |
| 错误原因 | 具体问题描述 |
| 严重级别 | high / medium / critical |
| 修复建议 | 自动生成的修复指引 |

---

## 分支保护与触发条件

### 自动触发

| 事件 | 说明 |
|------|------|
| `push` | 推送到指定分支 |
| `pull_request` | 向目标分支提 PR |
| `workflow_dispatch` | Actions 页手动触发 |

### 仅审计子目录

```yaml
workflow_dispatch:
  inputs:
    working-directory:
      default: 'src/backend'

# 或固定子目录
with:
  working-directory: 'src/backend'
```

### 关闭某个模块

```yaml
with:
  enable-super-linter: 'false'
  enable-runtime-audit: 'false'
```

---

## 目录结构

```
code-audit-skill/
├── action.yml                          # Composite Action 入口
├── README.md
├── DEPLOYMENT.md                       # 详细部署手册
├── config/
│   ├── telegram.yaml                   # ★ TG 写死配置
│   ├── audit-methods.yaml              # 六大类审计方法
│   ├── sast-patterns.yaml              # SAST/污点/专项规则
│   ├── gitleaks.toml
│   ├── ignore-paths.txt
│   └── custom-rules/business-rules.yaml
├── scripts/
│   ├── init.sh                         # 初始化
│   ├── detect-languages.sh
│   ├── run-gitleaks.sh / run-bandit.sh / run-dependency-scan.sh
│   ├── run-super-linter.sh / run-custom-rules.sh
│   ├── audit-engine.py                 # SAST/专项/差分/覆盖率引擎
│   ├── run-audit-module.sh
│   ├── finalize-results.sh
│   ├── generate-test-cases.py          # 测试用例生成
│   ├── execute-test-cases.py           # 测试用例执行
│   ├── generate-bug-report.py          # Bug 报告生成
│   ├── send-telegram.sh                # TG 推送
│   ├── load-telegram-config.sh
│   └── bundle-audit-logs.sh
├── examples/
│   └── consumer-workflow.yml           # 业务仓库接入模板
├── test-fixtures/                      # 全场景测试夹具
└── .github/workflows/
    ├── self-test.yml                   # 自测（引用 ./）
    └── pr-gate.yml                     # PR 门禁示例
```

---

## 本地自测

Skill 仓库推送后，在 **Actions → Self Test - All Scenarios** 手动触发，覆盖：

| 场景 | Fixture | 预期 |
|------|---------|------|
| 正常项目 | `test-fixtures/normal-project` | 通过 |
| 空项目 | `test-fixtures/empty-project` | 模块跳过 |
| 多语言 | `test-fixtures/multi-language` | 多模块运行 |
| 无 Python | `test-fixtures/no-python` | bandit 跳过 |
| 违规代码 | `test-fixtures/invalid-code` | failure + Bug MD 推送 TG |
| 网络异常 | 无效 TG Token | 审计完成，TG 失败不阻断 |
| 入参容错 | 大小写混合开关 | 正常执行 |

---

## 更多文档

- [DEPLOYMENT.md](DEPLOYMENT.md) — 上传 GitHub、发布、分支保护、故障排查
- [examples/consumer-workflow.yml](examples/consumer-workflow.yml) — 业务仓库 workflow 模板
- [.github/SECRETS.example.md](.github/SECRETS.example.md) — TG 配置说明（已改为写死方案，无需 Secrets）

---

## License

MIT
