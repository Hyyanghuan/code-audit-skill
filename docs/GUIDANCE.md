# Code Audit Skill — 可行性评估与扩展指导意见

> 角色：技术负责人 / 架构评审 | 版本：1.0 | 日期：2026-07-01  
> 适用范围：Skill 仓库维护者、业务仓接入方、产品与安全负责人

---

## 一、结论摘要

| 维度 | 评级 | 一句话 |
|------|------|--------|
| **技术可行性** | 🟢 高 | Composite Action + 14 模块 + 自测夹具，架构闭环，可跑通 CI |
| **产品可行性** | 🟢 高 | 「3 行接入 + 统一规则 + TG 通知」痛点清晰，适合中小团队 |
| **工程成熟度** | 🟡 中 | 核心能力已落地，缺 v1 tag、文档不一致、密钥治理待加强 |
| **扩展潜力** | 🟢 高 | 规则 YAML 化、双仓解耦、memory 需求层均可横向扩展 |
| **综合建议** | — | **可推广试用**；生产接入前完成 E-05/E-06 + Token 迁 Secrets |

**总体判断**：项目**可行且值得继续投入**。当前形态适合作为「组织级 CI 审计 Skill 模板」；不宜替代商业 SAST/SCA 平台，但与 proposal 定位一致。

---

## 二、项目现状快照

### 2.1 能力版图

```
业务仓 workflow (3~15 行)
        │
        ▼
┌───────────────────────────────────────────┐
│ L0  action.yml 编排                        │
│ L1  init / detect / finalize              │
│ L2  14 扫描模块 (CLI + audit-engine.py)    │
│ L3  汇总 / Bug / 测试用例                   │
│ L4  制品 upload-artifact                   │
│ L5  Telegram 推送                          │
└───────────────────────────────────────────┘
        │
        ▼
docs/ 四件套 + memory/ 需求层（Agent 协作）
```

### 2.2 已完成 vs 待办

| 区域 | 状态 | 说明 |
|------|------|------|
| M1~M3 审计核心 | ✅ | Action、14 模块、Bug/TG/自测 |
| M4 文档体系 | 🔄 90% | proposal/design/specs/tasks/memory |
| Epic F~H 记忆/需求 | ✅ | 六棱镜、清单 registry、TG 清单 |
| M5 正式发布 | 📋 | 无 v1 tag、无 CHANGELOG |
| E-06 文档对齐 | 📋 | DEPLOYMENT 仍偏 Secrets 叙述 |
| 需求清单 TG | ⚠️ | 脚本就绪；需本机/CI 可访问 Telegram API |

### 2.3 仓库规模（约）

| 类型 | 数量 |
|------|------|
| Shell/Python 脚本 | ~25 |
| 配置 YAML/TOML | ~8 |
| 模块 spec | 11 |
| test-fixtures 场景 | 6+ |
| memory 报告/模板 | 20+ |

---

## 三、可行性分维评估

### 3.1 技术可行性 🟢

#### 优势

1. **Composite Action 选型正确**  
   业务仓单 step 接入，逻辑内聚于 Skill 仓，符合 [design.md ADR-001](./design.md#四关键架构决策adr-摘要)。

2. **降级策略成熟**  
   模块 `continue-on-error` + 语言/依赖条件跳过 + TG 失败不阻断，满足 proposal 成功指标。

3. **规则可配置**  
   `sast-patterns.yaml`、`business-rules.yaml`、`gitleaks.toml` 等支持无代码改规则。

4. **自测可重复**  
   `.github/workflows/self-test.yml` 覆盖 normal/empty/invalid 等场景，回归成本可控。

#### 局限（需认知，非阻塞）

| 局限 | 影响 | 接受方式 |
|------|------|----------|
| `audit-engine.py` 为启发式 SAST | 污点/控制流非完整数据流 | 定位为「CI 轻量门禁」，非 IDE 级分析 |
| `runtime_audit` 仅建议报告 | 无真实 DAST | proposal Out of Scope，文档已说明 |
| super-linter 耗时长 | 大仓 CI 超时 | 默认关或按语言收窄 |
| 差分审计依赖 `fetch-depth: 0` | 浅克隆降级 | README 已强调 checkout 配置 |

#### 技术风险

| 风险 | 严重度 | 缓解 |
|------|--------|------|
| `@main` 漂移 | 中 | E-05 打 tag，生产用 SHA |
| 工具安装失败（网络） | 低 | 已有 continue-on-error |
| Python 运行时 pip 装 pyyaml | 低 | 可预装或 pin Actions 镜像 |

**结论**：作为 **CI 门禁型审计 Skill**，技术路径**完全可行**。

---

### 3.2 产品可行性 🟢

#### 目标用户匹配

| 用户 | 价值 | 可行性 |
|------|------|--------|
| 业务仓维护者 | 3 步接入、零复制脚本 | 高 — `examples/consumer-workflow.yml` 可直接用 |
| 安全/质量负责人 | 方法论覆盖（六大类 audit-methods） | 中高 — 内置引擎为轻量版 |
| Skill 维护者 | 集中改规则、全局生效 | 高 — push main 即更新 |

#### 与竞品/替代方案

| 方案 | 对比 |
|------|------|
| 各仓自建 workflow | 本 Skill **配置复用、能力统一**，胜出 |
| SonarQube / Snyk SaaS | 深度与生态更强；本 Skill **零 SaaS 费、GitHub 原生** |
| Reusable Workflow | 仍需复制 job；Composite Action **更短** |

#### 产品边界（务必遵守）

- ✅ CI 内静态/SCA/规则门禁 + 可行动报告  
- ❌ 完整 DAST、自动修代码、IDE 插件、多租户 TG 隔离  

**结论**：在「GitHub Actions + 中小团队」细分场景，**产品定位清晰、可行**。

---

### 3.3 工程与运维可行性 🟡

#### 已具备

- 双仓架构（Skill / 业务）文档完整  
- TG 配置优先级链：workflow > yaml  
- 制品保留、Bug MD、测试用例一条龙  

#### 待加强

| 项 | 问题 | 建议 |
|----|------|------|
| **密钥治理** | `config/telegram.yaml` 含 Bot Token 明文 | **P0**：迁 GitHub Secrets 或环境变量；yaml 仅 `enabled` 与开关 |
| **DEPLOYMENT.md** | 与 proposal「写死 yaml」方案矛盾 | E-06 统一为「Skill 仓 yaml 默认 + Secrets 覆盖」 |
| **版本发布** | 无 tag / CHANGELOG | E-05 `v1.0.0` + 语义化版本 |
| **需求清单 TG** | 本地/CI 需能访问 `api.telegram.org` | 文档说明代理/Region；失败不阻断关任务 |
| **memory 脚本** | 关任务多脚本、无单测 | 中期加 `tests/test_memory_scripts.py` |

**结论**：**可运维**，发布与密钥治理完成前建议仅 **内部试用**。

---

### 3.4 文档与协作可行性 🟢

项目已建立较完整的 **「文档驱动 + Agent 友好」** 体系：

| 层级 | 文件 | 作用 |
|------|------|------|
| 产品 | [proposal.md](./proposal.md) | 边界 |
| 架构 | [design.md](./design.md) | 分层与 ADR |
| 契约 | [specs/](./specs/) | 联调 AC |
| 任务 | [tasks.md](./tasks.md) | 进度 |
| 会话 | [memory/CONTEXT.md](./memory/CONTEXT.md) | 省 Token |
| 需求 | [memory/REQUIREMENT-GUIDE.md](./memory/REQUIREMENT-GUIDE.md) | 六棱镜 + 清单 |

**结论**：对 **人 + AI 协作** 友好，可作为其他 Skill 仓库的文档模板**复制**。

---

## 四、关键风险清单

| # | 风险 | 概率 | 影响 | 处置优先级 |
|---|------|------|------|------------|
| R1 | Token 泄露（yaml 进 Git） | 中 | 高 | **P0** 立即轮换 + 迁 Secrets |
| R2 | `@main` Breaking Change | 中 | 中 | P1 tag + 发布说明 |
| R3 | 误报/漏报导致开发者信任下降 | 中 | 中 | P1 调规则 severity；大仓关 super-linter |
| R4 | Fork PR 无法读 Secrets | 低 | 低 | 文档说明；统一 Skill 仓 TG |
| R5 | 需求 registry 与代码漂移 | 低 | 低 | 关任务强制跑 memory-report |
| R6 | Telegram 区域网络不可达 | 中 | 低 | 清单 MD 仍落盘；TG 可选 |

---

## 五、扩展方向（指导意见）

### 5.1 短期（1~4 周）— 夯实可发布

| 方向 | 内容 | 价值 | 工作量 |
|------|------|------|--------|
| **E-05 正式发布** | `v1.0.0` tag、CHANGELOG、README 推荐 SHA | 生产可锁定 | 小 |
| **E-06 文档统一** | DEPLOYMENT 与 proposal 对齐 | 降低接入错误 | 小 |
| **密钥治理** | Token 迁 Secrets；yaml 留开关 | 安全合规 | 小 |
| **规则调优** | 按 test-fixtures/invalid-code 校准 severity | 减少误报 | 中 |
| **清单 TG 验证** | CI job 或文档化 `send-requirements-tg.sh` | 闭环 H01 | 小 |

### 5.2 中期（1~3 月）— 能力增强

| 方向 | 内容 | 架构触点 | 建议优先级 |
|------|------|----------|------------|
| **通知多通道** | Slack / 钉钉 / 企业微信 适配层 | L5 新脚本，不改 L2 | P2 |
| **规则包版本化** | `config/rules/v1/` + input 选版本 | config + init | P2 |
| **SARIF 输出** | 对接 GitHub Code Scanning | finalize + artifacts | P2 |
| **模块性能** | super-linter 默认关；并行 step（需改 action 结构） | L0 编排 | P3 |
| **业务仓覆盖** | 按语言 preset：`preset-python` / `preset-node` | action inputs | P2 |
| **memory 自动化** | CI 关 PR 时跑 checklist（可选 job） | `.github/workflows/` | P3 |

### 5.3 长期（3~6 月+）— 战略扩展

| 方向 | 说明 | 可行性 | 注意 |
|------|------|--------|------|
| **Skill 市场/模板仓** | 多 Skill  monorepo 或 org 下多 repo | 高 | 保持单 Skill 职责单一 |
| **规则贡献流程** | CONTRIBUTING + 规则 PR 评审 | 高 | 需 severity 治理 |
| **与 OpenSSF Scorecard 集成** | 互补非替代 | 中 | 避免能力重复 |
| **轻量 DAST** | 预发 webhook 触发 ZAP baseline | 中 | 超出当前 Action 边界，独立 workflow |
| **AI 辅助 intake** | 从 PR 描述生成 intake 草稿 | 中 | G01 已标 Out of Scope，可独立工具 |
| **多租户 TG** | 业务仓 mapping 表 | 低~中 | 需后端或加密配置服务 |

### 5.4 不建议扩展的方向

| 方向 | 原因 |
|------|------|
| 替代 SonarQube 做全量代码质量平台 | 定位冲突，投入过大 |
| 在 Action 内跑完整 IAST/DAST | CI 时长与基础设施不满足 |
| 自动修复并 push 代码 | 安全与合规风险高 |
| memory 层替代 issue/项目管理 | 应接 Linear/Jira，registry 仅作导出 |

---

## 六、扩展架构原则（新增能力时遵守）

1. **L2 扫描与 L5 通知解耦** — 新扫描不加 TG 逻辑；新通知不改 scan。  
2. **先 spec 后代码** — 新模块必须补 `docs/specs/{模块}/spec.md` + `module-map.yaml`。  
3. **关任务走 memory 流程** — intake → 实施 → diff/audit/checklist → CONTEXT。  
4. **默认不破坏零配置接入** — 新 input 默认与现行为一致。  
5. **Breaking Change 仅 major tag** — 遵循语义化版本。

---

## 七、接入决策树（给业务仓）

```
是否需要 GitHub CI 安全门禁？
  └─ 否 → 暂不接入
  └─ 是 → 是否有 Python/Node/多语言？
           └─ 仅文档仓 → 开 gitleaks + config_audit，关 bandit/trivy
           └─ 应用仓 → 默认全开，大仓关 super-linter
                └─ 生产环境？
                     └─ 是 → uses: ORG/code-audit-skill@v1.x.x (SHA)
                     └─ 否 → @main 跟踪最新
```

---

## 八、推荐路线图（2026 Q3）

```
Week 1-2   P0 密钥治理 + E-06 文档对齐 + E-05 v1.0.0
Week 3-4   规则调优 + self-test 全绿确认 + 1 个真实业务仓试点
Month 2    SARIF 或 Slack 二选一 + preset inputs
Month 3    规则包版本化 + CONTRIBUTING + 第二业务仓推广
```

### 里程碑更新建议（写入 tasks.md）

| 里程碑 | 目标 |
|--------|------|
| M5 | v1.0.0 发布 + CHANGELOG |
| M6 | 密钥迁 Secrets + DEPLOYMENT 对齐 |
| M7 | 1 个生产业务仓稳定运行 30 天 |
| M8 | SARIF 或第二通知通道 |

---

## 九、验收「项目可行」的检查表

关任务或发布前，确认以下项：

- [ ] `self-test.yml` 关键场景通过  
- [ ] `examples/consumer-workflow.yml` 在新仓 5 步内跑通  
- [ ] `invalid-code` fixture 产生 failure + Bug MD  
- [ ] Token 不在 Git 明文（或已轮换）  
- [ ] 生产引用 commit SHA 或 tag，非裸 `@main`  
- [ ] `requirements-checklist.md` 与 registry 一致  
- [ ] proposal Out of Scope 无静默违反  

---

## 十、相关文档索引

| 文档 | 用途 |
|------|------|
| [proposal.md](./proposal.md) | 做什么 / 不做什么 |
| [design.md](./design.md) | 怎么做 / ADR |
| [tasks.md](./tasks.md) | 任务与风险 |
| [specs/](./specs/) | 模块契约 |
| [memory/REQUIREMENT-GUIDE.md](./memory/REQUIREMENT-GUIDE.md) | 需求工作流 |
| [memory/reports/requirements-checklist.md](./memory/reports/requirements-checklist.md) | 需求与验证总览 |
| [README.md](../README.md) | 对外快速接入 |
| [DEPLOYMENT.md](../DEPLOYMENT.md) | 部署（待 E-06 对齐） |

---

## 十一、修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-07-01 | 首版：可行性四维度 + 短中长期扩展 + 路线图 |
