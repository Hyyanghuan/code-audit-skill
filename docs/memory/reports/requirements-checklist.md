# 需求清单与验证结果

> 生成时间：2026-07-01 09:56 UTC  
> 排序：**需求完成时间倒序**（新 → 旧）  
> 数据源：`docs/memory/requirements-registry.yaml`

---

## 总览

| 指标 | 数量 |
|------|------|
| 需求条目 | 6 |
| 功能点合计 | 28 |
| 已实现 | 26 |
| 已验证 | 28 |
| 待验证 | 0 |

**本次关任务**：`H01` 🆕

---

## REQ-H01 — 需求清单与TG推送 🆕

| 项 | 值 |
|----|-----|
| 类型 | **新需求** |
| 任务 ID | `H01` |
| Epic | Epic H |
| 创建 | 2026-07-01 |
| 完成 | 2026-07-01 |
| 状态 | completed |
| 原文摘要 | 完成任务后生成完整的需求清单以及验证结果，清单包含新需求的功能以及历史功能需求，按照需求时间倒序生成md文档发送tg |

**报告**：`docs/memory/intake/H01.md`

### 功能清单与验证

| 功能 ID | 功能 | 计划 | 实现 | 验证 | 证据 |
|---------|------|------|------|------|------|
| F-01 | requirements-registry.yaml | ✅ | ✅ | ✅ | 历史+新需求单一数据源 |
| F-02 | 清单 MD 时间倒序 | ✅ | ✅ | ✅ | 新→旧排列 |
| F-03 | 功能+验证结果表 | ✅ | ✅ | ✅ | 计划/实现/验证列 |
| F-04 | 关任务自动 upsert | ✅ | ✅ | ✅ | 接 generate-memory-report |
| F-05 | TG 发送清单 | ✅ | ✅ | ✅ | sendDocument + 摘要 |
| F-06 | telegram.yaml 开关 | ✅ | ✅ | ✅ | send_requirements_checklist |
| F-07 | 仅发新需求不发历史 | ❌ | ❌ | ✅ | 用户要求含历史 |

---

## REQ-G01 — 需求理解六棱镜与逻辑比对 📦

| 项 | 值 |
|----|-----|
| 类型 | **历史需求** |
| 任务 ID | `G01` |
| Epic | Epic G |
| 创建 | 2026-07-01 |
| 完成 | 2026-07-01 |
| 状态 | completed |
| 原文摘要 | 优化需求理解的多样性，功能的探索和需求的完整性，需求的逻辑缜密性比对完成工作 |

**报告**：`docs/memory/intake/G01.md` · `docs/memory/reports/2026-07-01-G01-需求理解六棱镜与逻辑比对-requirement-audit.md` · `docs/memory/reports/2026-07-01-G01-需求理解六棱镜与逻辑比对-completion.md`

### 功能清单与验证

| 功能 ID | 功能 | 计划 | 实现 | 验证 | 证据 |
|---------|------|------|------|------|------|
| F-01 | 六棱镜 YAML 定义 | ✅ | ✅ | ✅ | docs/memory/requirement-lens.yaml |
| F-02 | intake 模板 | ✅ | ✅ | ✅ | docs/memory/templates/requirement-intake.template.md |
| F-03 | requirement-audit 模板 | ✅ | ✅ | ✅ | docs/memory/templates/requirement-audit.template.md |
| F-04 | 脚本 init-intake / audit | ✅ | ✅ | ✅ | scripts/generate-memory-report.py |
| F-05 | REQUIREMENT-GUIDE | ✅ | ✅ | ✅ | docs/memory/REQUIREMENT-GUIDE.md |
| F-06 | completion 关联 audit | ✅ | ✅ | ✅ | completion §6 |
| F-07 | AI 自动填 intake | ❌ | ❌ | ✅ | Out of Scope 未做 |

---

## REQ-E04 — 文档四件套 📦

| 项 | 值 |
|----|-----|
| 类型 | **历史需求** |
| 任务 ID | `E04` |
| Epic | Epic E |
| 创建 | 2026-07-01 |
| 完成 | 2026-07-01 |
| 状态 | completed |
| 原文摘要 | proposal / design / specs / tasks 项目文档体系 |

**报告**：`docs/memory/reports/2026-07-01-E04-文档四件套与记忆层-completion.md`

### 功能清单与验证

| 功能 ID | 功能 | 计划 | 实现 | 验证 | 证据 |
|---------|------|------|------|------|------|
| F-01 | proposal.md 产品提案 | ✅ | ✅ | ✅ | docs/proposal.md |
| F-02 | design.md 架构设计 | ✅ | ✅ | ✅ | docs/design.md |
| F-03 | specs 模块契约 11 份 | ✅ | ✅ | ✅ | docs/specs/ |
| F-04 | tasks.md 任务拆解 | ✅ | ✅ | ✅ | docs/tasks.md |

---

## REQ-HIST-M3 — 测试用例 / Bug 报告 / Telegram 推送 📦

| 项 | 值 |
|----|-----|
| 类型 | **历史需求** |
| 任务 ID | `M3` |
| Epic | 产品核心 |
| 创建 | 2025-12-01 |
| 完成 | 2025-12-15 |
| 状态 | completed |
| 原文摘要 | 审计后处理链路：汇总、测试用例、Bug MD、TG 通知 |

### 功能清单与验证

| 功能 ID | 功能 | 计划 | 实现 | 验证 | 证据 |
|---------|------|------|------|------|------|
| F-01 | 验收测试用例生成与执行 | ✅ | ✅ | ✅ | scripts/generate-test-cases.py |
| F-02 | Bug 报告 MD/JSON | ✅ | ✅ | ✅ | scripts/generate-bug-report.py |
| F-03 | Telegram 摘要与附件推送 | ✅ | ✅ | ✅ | scripts/send-telegram.sh |
| F-04 | Actions 制品上传 | ✅ | ✅ | ✅ | action.yml upload-artifact |

---

## REQ-HIST-M2 — 14 扫描模块 + audit-engine 📦

| 项 | 值 |
|----|-----|
| 类型 | **历史需求** |
| 任务 ID | `M2` |
| Epic | 产品核心 |
| 创建 | 2025-11-01 |
| 完成 | 2025-11-20 |
| 状态 | completed |
| 原文摘要 | 全覆盖 SAST/SCA/专项/差分/覆盖率/运行时建议/人工清单 |

### 功能清单与验证

| 功能 ID | 功能 | 计划 | 实现 | 验证 | 证据 |
|---------|------|------|------|------|------|
| F-01 | gitleaks/bandit/trivy/super-linter | ✅ | ✅ | ✅ | scripts/run-*.sh |
| F-02 | audit-engine 九子模块 | ✅ | ✅ | ✅ | scripts/audit-engine.py |
| F-03 | 自定义 YAML 业务规则 | ✅ | ✅ | ✅ | config/custom-rules/ |

---

## REQ-HIST-M1 — Composite Action 骨架 + 基础扫描 📦

| 项 | 值 |
|----|-----|
| 类型 | **历史需求** |
| 任务 ID | `M1` |
| Epic | 产品核心 |
| 创建 | 2025-10-01 |
| 完成 | 2025-10-15 |
| 状态 | completed |
| 原文摘要 | 业务仓 uses 接入，init/finalize 链路 |

### 功能清单与验证

| 功能 ID | 功能 | 计划 | 实现 | 验证 | 证据 |
|---------|------|------|------|------|------|
| F-01 | action.yml Composite Action | ✅ | ✅ | ✅ | action.yml |
| F-02 | init 环境与开关解析 | ✅ | ✅ | ✅ | scripts/init.sh |
| F-03 | fail-on-findings 门禁 | ✅ | ✅ | ✅ | action.yml |

---

## 验证说明

| 符号 | 含义 |
|------|------|
| ✅ | 通过 / 已实现 |
| ❌ | 未通过 / 明确不做 |
| ☐ | 待确认 |

🆕 = 本次关任务 · 📦 = 历史归档
