# Code Audit Skill

可复用的 GitHub Actions **Composite Action** 代码审计 Skill，独立仓库存放，业务仓库仅需几行配置即可接入。

## 架构

```
code-audit-skill/          ← 独立仓库（本仓库）
├── action.yml             ← Composite Action 入口
├── scripts/               ← 审计逻辑（与配置解耦）
├── config/                ← gitleaks / 自定义规则 / 忽略路径
├── examples/              ← 业务仓库接入示例
└── test-fixtures/         ← 全场景测试夹具

your-business-repo/        ← 业务仓库
└── .github/workflows/
    └── code-audit.yml     ← 3~10 行引用本 Action
```

## 能力覆盖

| 模块 | 工具 | 说明 | 开关 |
|------|------|------|------|
| 敏感密钥 | gitleaks v8.21.2 | 检测硬编码 Token/密钥 | `enable-gitleaks` |
| 多语言规范 | super-linter slim-v7.2.1 | Python/JS/YAML/Shell 等 | `enable-super-linter` |
| Python 安全 | bandit 1.7.10 | SQL 注入、eval 等 | `enable-bandit` |
| 依赖漏洞 | trivy 0.58.1 | HIGH/CRITICAL 漏洞 | `enable-dependency-scan` |
| 业务规则 | 自定义 YAML | eval/硬编码密码/SQL 拼接等 | `enable-custom-rules` |
| 验收测试 | 自动生成+执行 | 审计完成后生成并执行 TC 用例 | `enable-test-cases` |
| 通知 | Telegram Bot API | 审计+测试用例汇总推送 | `enable-telegram` |

## 执行流程

```
代码扫描 → 汇总审计 → 生成测试用例 → 执行测试用例 → 上传制品 → TG 汇总通知
  gitleaks      audit-summary    test-cases.json    回写结果/是否通过    含 TC 报告
  bandit...                      test-cases.md
                                 test-cases.csv
```

## 验收测试用例

审计完成后自动基于扫描配置与结果生成验收测试用例，字段包含：

| 字段 | 说明 |
|------|------|
| TC-ID | 用例编号，如 `TC-AUDIT-001` |
| 测试功能 | 被验证的审计能力名称 |
| 功能描述 | 该能力的业务说明 |
| 测试内容描述 | 具体验证内容 |
| 测试步骤 | 分步操作说明 |
| 预期结果 | 期望的审计/降级行为 |
| 测试结果 | 执行后回写的实际结果 |
| 是否通过 | 执行后回写：`是` / `否` |

**制品输出**（在 `code-audit-logs-{run_id}` 中）：
- `test-cases.json` — 完整用例（含断言与执行结果）
- `test-cases.md` — Markdown 表格
- `test-cases.csv` — Excel 可导入
- `test-cases-report.json` — 执行统计报告

**TG 通知**在审计与测试用例全部完成后发送，包含扫描模块详情和每条 TC 的通过/失败状态。

## 快速接入（业务仓库）

### 1. 配置 Secrets

在 GitHub 仓库 **Settings → Secrets → Actions** 添加：

| Secret | 说明 |
|--------|------|
| `TG_BOT_TOKEN` | Telegram Bot Token |
| `TG_CHAT_ID` | 群组 Chat ID（如 `-5342457001`） |

详见 [`.github/SECRETS.example.md`](.github/SECRETS.example.md)。

### 2. 添加 Workflow

```yaml
# .github/workflows/code-audit.yml
name: Code Audit
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: YOUR_ORG/code-audit-skill@v1
        with:
          fail-on-findings: 'true'
          enable-telegram: 'true'
          telegram-bot-token: ${{ secrets.TG_BOT_TOKEN }}
          telegram-chat-id: ${{ secrets.TG_CHAT_ID }}
          telegram-bot-username: '@test_skills_yh_bot'
```

完整示例见 [`examples/consumer-workflow.yml`](examples/consumer-workflow.yml)。

> 📖 **完整部署步骤**（上传 GitHub、Bot Token 配置、业务仓库接入、分支保护等）请参阅 **[DEPLOYMENT.md](DEPLOYMENT.md)**。

## 分支保护（阻断违规 PR）

1. 进入 **Settings → Branches → Branch protection rules**
2. 勾选 **Require status checks to pass before merging**
3. 添加 Required check：`Code Audit`（或你的 job 名称）
4. 设置 `fail-on-findings: 'true'`（默认）

当 gitleaks / bandit / 自定义规则等发现高危问题时，Action 失败，PR 无法合并。

## 输入参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `working-directory` | `.` | 审计目标目录 |
| `fail-on-findings` | `true` | 发现问题时令 Action 失败 |
| `upload-artifacts` | `true` | 上传扫描日志制品 |
| `artifact-retention-days` | `14` | 制品保留天数 |
| `enable-gitleaks` | `true` | 模块开关（支持 TRUE/yes/1 等） |
| `enable-super-linter` | `true` | 同上 |
| `enable-bandit` | `true` | 同上 |
| `enable-dependency-scan` | `true` | 同上 |
| `enable-custom-rules` | `true` | 同上 |
| `enable-test-cases` | `true` | 审计后自动生成并执行验收测试用例 |
| `enable-telegram` | `false` | 同上 |
| `telegram-bot-token` | — | 通过 secrets 传入 |
| `telegram-chat-id` | — | 群组 ID |
| `gitleaks-config` | 内置 | 自定义 gitleaks 配置路径 |
| `custom-rules-path` | 内置 | 自定义业务规则 YAML |
| `super-linter-languages` | 自动检测 | 如 `Python, YAML, JavaScript` |

## 输出

| 输出 | 说明 |
|------|------|
| `audit-status` | `success` / `failure` / `skipped` |
| `findings-count` | 问题总数 |
| `results-json` | 汇总 JSON 路径 |
| `test-cases-passed` | 通过的测试用例数 |
| `test-cases-failed` | 失败的测试用例数 |
| `test-cases-all-passed` | 全部测试用例是否通过 |

## 设计特性

- **脚本与 Action 解耦**：`action.yml` 仅编排步骤，逻辑在 `scripts/`
- **入参容错**：空值、大小写、特殊字符不中断流程
- **工具降级**：无对应语言/代码自动跳过；工具安装失败降级为 error 不阻断
- **敏感配置外部传入**：Token 禁止硬编码，第三方工具固定版本
- **TG 失败不阻断**：`continue-on-error: true`，审计主流程不受影响
- **制品持久化**：所有模块日志上传至 `code-audit-logs-{run_id}`
- **性能优化**：自动忽略 `node_modules`、`dist`、`build`、`vendor` 等目录

## 测试场景

本仓库内置 [`/.github/workflows/self-test.yml`](.github/workflows/self-test.yml)，覆盖：

| 场景 | Fixture | 预期 |
|------|---------|------|
| 正常项目 | `test-fixtures/normal-project` | 通过 |
| 空项目 | `test-fixtures/empty-project` | 全部跳过 |
| 多语言 | `test-fixtures/multi-language` | 多模块运行 |
| 无 Python | `test-fixtures/no-python` | bandit 跳过 |
| 违规代码 | `test-fixtures/invalid-code` | failure + TG 通知 |
| 网络异常 | 无效 TG Token | 审计完成，TG 失败不阻断 |
| 入参容错 | 大小写混合开关 | 正常执行 |

手动触发：`Actions → Self Test - All Scenarios → Run workflow`

## 自定义业务规则

编辑 [`config/custom-rules/business-rules.yaml`](config/custom-rules/business-rules.yaml)：

```yaml
rules:
  - id: my-rule
    pattern: 'dangerous_function\s*\('
    severity: high
    message: "禁止调用 dangerous_function"
    paths:
      - "**/*.py"
```

## 目录结构

```
.
├── action.yml
├── scripts/
│   ├── common.sh              # 公共工具
│   ├── init.sh                # 初始化
│   ├── detect-languages.sh    # 语言检测
│   ├── run-gitleaks.sh
│   ├── run-super-linter.sh
│   ├── run-bandit.sh
│   ├── run-dependency-scan.sh
│   ├── run-custom-rules.sh
│   ├── finalize-results.sh
│   ├── generate-test-cases.py   # 用例生成
│   ├── generate-test-cases.sh
│   ├── execute-test-cases.py    # 用例执行+回写
│   ├── execute-test-cases.sh
│   └── send-telegram.sh
├── config/
│   ├── gitleaks.toml
│   ├── ignore-paths.txt
│   └── custom-rules/business-rules.yaml
├── examples/consumer-workflow.yml
├── test-fixtures/
└── .github/workflows/
    ├── self-test.yml
    └── pr-gate.yml
```

## 发布版本

建议使用 Git tag 发布：`v1.0.0`，业务仓库引用 `@v1` 或 `@v1.0.0`。

## License

MIT
