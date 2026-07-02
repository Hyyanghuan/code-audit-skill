# Code Audit Skill — 产品提案

> 角色：产品 | 状态：已落地 v1 | 最后更新：2026-07-01

---

## 一、为什么做？

### 背景与痛点

| 痛点 | 现状 | 期望 |
|------|------|------|
| 审计能力分散 | 各业务仓自行拼装 gitleaks/bandit/trivy 等，配置重复、版本不一致 | 一次接入，统一能力 |
| CI 接入成本高 | 每个项目复制大量 shell 脚本与 workflow | 业务仓 **3~10 行** workflow 即可 |
| 结果不可行动 | 扫描日志散落，开发难以定位与修复 | 结构化 Bug 报告 + 验收测试用例 |
| 缺少门禁 | 高危问题仍可合并 PR | `fail-on-findings` + 分支保护阻断 |
| 通知滞后 | 需登录 Actions 查看结果 | Telegram 群实时推送摘要与附件 |

### 目标用户

- **业务仓库维护者**：希望零/低配置接入代码审计 CI
- **安全/质量负责人**：需要覆盖 SAST、SCA、专项安全、差分审计等方法论
- **Skill 仓库维护者**：集中演进规则、脚本与推送能力

### 成功指标

| 指标 | 目标 |
|------|------|
| 业务仓接入步骤 | ≤ 5 步，workflow 行数 ≤ 15 |
| 扫描模块 | 14 个可独立开关 |
| 无对应代码时 | 自动跳过，不阻断流水线 |
| 工具安装失败 | 降级继续，主流程不崩溃 |
| TG 推送失败 | 不阻断审计结论 |

---

## 二、做什么？

### 核心能力（In Scope）

1. **Composite Action 形态**
   - 独立 Skill 仓库存放 `action.yml` + `scripts/` + `config/`
   - 业务仓通过 `uses: ORG/code-audit-skill@main` 引用

2. **14 个扫描模块**（均可 `enable-*` 开关）
   - 外部工具：gitleaks、super-linter、bandit、trivy、自定义 YAML 规则
   - 内置引擎：SAST 词法/污点/控制流、配置审计、专项安全、差分、覆盖率、运行时建议、人工清单

3. **审计后处理链路**
   - 汇总 → 人工清单 → 验收测试用例生成/执行 → Bug MD/JSON → 制品上传 → Telegram 推送 → 失败判定

4. **Telegram 通知**
   - Skill 仓 `config/telegram.yaml` 写死默认配置
   - 业务仓 workflow 参数可覆盖（Secrets 或明文）

5. **分支保护配合**
   - `audit-status: failure` + `fail-on-findings: true` → Action 失败，阻断 PR

6. **自测体系**
   - `test-fixtures/` 多场景夹具 + `.github/workflows/self-test.yml`

### 交付物

| 交付物 | 说明 |
|--------|------|
| Composite Action | `action.yml` |
| 审计制品 | `audit-summary.json`、`audit-bugs.md`、`test-cases.md` 等 |
| 接入模板 | `examples/consumer-workflow.yml` |
| 项目文档 | 本目录 `proposal / design / specs / tasks / memory` |

### 用户故事（摘要）

- 作为业务开发者，我希望 push/PR 时自动跑审计，以便在合并前发现密钥泄露与高危漏洞。
- 作为 Team Lead，我希望 TG 群收到 `[BUG ALERT]` 与附件，以便快速分派修复。
- 作为 Skill 维护者，我希望改规则后 push 到 main，所有引用方下次运行即生效。

---

## 三、不做什么？（Out of Scope）

| 不做 | 原因 | 替代方案 |
|------|------|----------|
| 完整 DAST/IAST 运行时扫描 | CI 内无预发环境与流量 | `runtime_audit` 仅输出**建议报告** |
| 自动修复代码 | 风险高，需人工确认 | Bug 报告含修复建议字段 |
| 私有 Skill 仓的零配置跨 org 引用 | GitHub 权限模型限制 | 公开仓库或 org 内授权 |
| Fork PR 读取业务仓 Secrets | GitHub 安全策略 | 文档说明限制，Skill 仓统一 TG |
| 替代专业 SAST 商业产品 | 定位为可复用 CI Skill，非 IDE 插件 | 可叠加 SonarQube 等 |
| 多通道通知（Slack/钉钉/邮件） | v1 聚焦 TG | 后续版本扩展 |
| 审计结果持久化数据库 | 无后端服务 | Actions 制品 + TG 附件 |
| 业务仓内嵌 TG Token | 安全与维护成本 | Skill 仓统一配置 + 可选覆盖 |

---

## 四、里程碑（产品视角）

| 阶段 | 内容 | 状态 |
|------|------|------|
| M1 | Composite Action 骨架 + gitleaks/bandit | ✅ 已完成 |
| M2 | 14 模块 + audit-engine | ✅ 已完成 |
| M3 | 测试用例/Bug 报告/TG 推送 | ✅ 已完成 |
| M4 | 文档体系（proposal/design/specs/tasks） | 🔄 进行中 |
| M5 | 版本 tag 锁定 + 变更日志 | 📋 待规划 |

---

## 五、相关文档

- 架构与决策 → [design.md](./design.md)
- 模块联调契约 → [specs/](./specs/)
- 任务与进度 → [tasks.md](./tasks.md)
- **会话续接** → [memory/CONTEXT.md](./memory/CONTEXT.md)
- **可行性/扩展** → [GUIDANCE.md](./GUIDANCE.md)
- **变更报告** → [memory/reports/](./memory/reports/)
