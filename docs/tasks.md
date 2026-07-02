# Code Audit Skill — 任务拆解与进度

> 角色：全员 | 最后更新：2026-07-01

---

## 进度总览

| 里程碑 | 状态 | 完成度 |
|--------|------|--------|
| M1 Action 骨架 + 基础扫描 | ✅ 完成 | 100% |
| M2 14 模块 + audit-engine | ✅ 完成 | 100% |
| M3 测试用例 / Bug / TG | ✅ 完成 | 100% |
| M4 文档体系 docs/ | ✅ 完成 | 100% |
| M5 版本发布 v1.0.0 | ✅ 完成 | CHANGELOG + VERSION |
| M6 企业级加固 | ✅ 完成 | 见 [GUIDANCE.md](./GUIDANCE.md) |

**图例**：✅ 完成 | 🔄 进行中 | 📋 待开始 | ⏸ 阻塞

---

## 任务清单

### Epic A — 核心 Action（L0~L1）

| ID | 任务 | 负责人 | 依赖 | 状态 | 验收 |
|----|------|--------|------|------|------|
| A-01 | `action.yml` inputs/outputs 定义 | — | — | ✅ | 与 [action-core/spec.md](./specs/action-core/spec.md) 一致 |
| A-02 | `init.sh` 开关解析与环境目录 | — | A-01 | ✅ | 大小写混合开关自测通过 |
| A-03 | `detect-languages.sh` 条件检测 | — | A-02 | ✅ | no-python fixture bandit 跳过 |
| A-04 | `finalize-results.sh` 汇总判定 | — | B-* | ✅ | invalid-code → failure |

### Epic B — 扫描模块（L2）

| ID | 任务 | 依赖 | 状态 | Spec |
|----|------|------|------|------|
| B-01 | gitleaks 适配 | A-02 | ✅ | [scan-gitleaks](./specs/scan-gitleaks/spec.md) |
| B-02 | super-linter 适配 | A-03 | ✅ | [scan-super-linter](./specs/scan-super-linter/spec.md) |
| B-03 | bandit 适配 | A-03 | ✅ | [scan-bandit](./specs/scan-bandit/spec.md) |
| B-04 | trivy 依赖扫描 | A-03 | ✅ | [scan-dependency](./specs/scan-dependency/spec.md) |
| B-05 | 自定义 YAML 规则 | A-02 | ✅ | [scan-custom-rules](./specs/scan-custom-rules/spec.md) |
| B-06 | audit-engine 词法/污点/控制流 | A-02 | ✅ | [audit-engine](./specs/audit-engine/spec.md) |
| B-07 | audit-engine 配置/专项/差分 | B-06 | ✅ | 同上 |
| B-08 | audit-engine 覆盖率/运行时/人工清单 | B-06 | ✅ | 同上 |

### Epic C — 后处理（L3~L4）

| ID | 任务 | 依赖 | 状态 | Spec |
|----|------|------|------|------|
| C-01 | 验收测试用例生成 | A-04 | ✅ | [test-cases](./specs/test-cases/spec.md) |
| C-02 | 验收测试用例执行 | C-01 | ✅ | 同上 |
| C-03 | Bug 报告 MD/JSON | A-04 | ✅ | [bug-report](./specs/bug-report/spec.md) |
| C-04 | 制品上传 upload-artifact | C-03 | ✅ | [artifacts](./specs/artifacts/spec.md) |

### Epic D — 通知（L5）

| ID | 任务 | 依赖 | 状态 | Spec |
|----|------|------|------|------|
| D-01 | `telegram.yaml` 写死配置 | — | ✅ | [telegram](./specs/telegram/spec.md) |
| D-02 | 配置优先级与覆盖 | D-01 | ✅ | 同上 |
| D-03 | 摘要 + 附件推送 | C-04 | ✅ | 同上 |
| D-04 | TG 失败不阻断 | D-03 | ✅ | 无效 Token 自测 |

### Epic E — 质量与接入

| ID | 任务 | 依赖 | 状态 | 验收 |
|----|------|------|------|------|
| E-01 | test-fixtures 六场景 | B-* | ✅ | self-test.yml 全绿 |
| E-02 | consumer-workflow 模板 | A-01 | ✅ | examples/ 可复制 |
| E-03 | README 快速接入 | E-02 | ✅ | 5 步文档 |
| E-04 | docs/ proposal/design/specs/tasks | — | 🔄 | 本目录结构 + 记忆层 |
| E-07 | docs/memory 记忆层 + 报告脚本 | E-04 | ✅ | generate-memory-report 可运行 |
| E-05 | 发布 v1 tag + CHANGELOG | E-04 | ✅ | v1.0.0 / CHANGELOG.md |
| E-06 | DEPLOYMENT.md 与 proposal 对齐 | E-04 | ✅ | Secrets 优先 |

### Epic F — 记忆层（省 Token / 减重复）

| ID | 任务 | 依赖 | 状态 | 验收 |
|----|------|------|------|------|
| F-01 | memory/CONTEXT 热快照 | E-04 | ✅ | Agent 读 CONTEXT 可续接 |
| F-02 | module-map.yaml 路径映射 | F-01 | ✅ | 改动路径可映射 spec |
| F-03 | diff/completion 模板 | F-01 | ✅ | templates/ 两文件 |
| F-04 | generate-memory-report 脚本 | F-02,F-03 | ✅ | 产出 reports/*.md |
| F-05 | 任务结束更新 CONTEXT 规范 | F-04 | ✅ | memory/README 工作流 |

### Epic G — 需求理解（六棱镜 + 逻辑比对）

| ID | 任务 | 依赖 | 状态 | 验收 |
|----|------|------|------|------|
| G-01 | requirement-lens.yaml 六棱镜/五维/八项 | F-04 | ✅ | 定义完整 |
| G-02 | intake + audit 模板 | G-01 | ✅ | templates/ 两文件 |
| G-03 | REQUIREMENT-GUIDE 工作流 | G-02 | ✅ | 三阶段可执行 |
| G-04 | 脚本 --init-intake / audit 集成 | G-02 | ✅ | G01 报告已生成 |
| G-05 | completion 关联 audit 摘要 | G-04 | ✅ | §6 逻辑比对 |

### Epic H — 需求清单与 TG 推送

| ID | 任务 | 依赖 | 状态 | 验收 |
|----|------|------|------|------|
| H-01 | requirements-registry.yaml | G-04 | ✅ | 含 M1~G01 历史 |
| H-02 | generate_requirements_checklist.py | H-01 | ✅ | 倒序 MD |
| H-03 | 关任务接 memory-report + 默认 TG | H-02 | ✅ | --no-send-tg 可跳过 |
| H-04 | send_requirements_checklist 配置 | H-03 | ✅ | telegram.yaml |

---

## 依赖关系图

```
A-01 → A-02 → A-03
              ↓
         B-01 … B-08 (可并行)
              ↓
            A-04 (finalize)
              ↓
    C-01 → C-02 ─┐
    C-03 → C-04 ─┼→ D-03
                 ↓
            Job 失败判定
```

---

## 当前 Sprint（文档与发布）

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | F-04 首份报告 E04 | 差异 + 完成 MD 已生成 |
| P0 | E-04 完善各模块 spec | 联调契约补齐 |
| P1 | E-06 统一 DEPLOYMENT 与 TG 写死方案 | 见 GUIDANCE R1/E-06 |
| P1 | 密钥迁 Secrets（GUIDANCE P0） | Token 勿明文进 Git |
| P2 | E-05 打 v1.0.0 tag | 供生产 SHA 锁定 |
| P3 | 新增 Slack 通知 spike | Out of Scope v1，仅调研 |

---

## 阻塞与风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| DEPLOYMENT.md 仍描述 Secrets 为主方案 | 新用户配置错误 | E-06 对齐 proposal |
| `@main` 漂移 | 生产意外行为变更 | E-05 tag + 文档推荐 SHA |
| super-linter 耗时长 | 大仓 CI 超时 | workflow 可 `enable-super-linter: false` |
| Fork PR Secrets | TG 覆盖失败 | 文档 + Skill 仓统一 TG |

---

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-07-01 | **v1.0.0 企业级**：Secrets 治理、audit-preset、SARIF、CI 测试 |
| 2026-07-01 | 新增 memory 记忆层 + 报告生成脚本 |
| 2026-07-01 | 初始化 docs/ 四件套与 specs 目录 |
| — | 核心 Action 与 14 模块已实现（历史） |

---

## 相关文档

- [proposal.md](./proposal.md) — 做什么 / 不做什么
- [design.md](./design.md) — 怎么做
- [specs/](./specs/) — 模块契约
- [memory/](./memory/) — 记忆层与报告
- [GUIDANCE.md](./GUIDANCE.md) — 可行性与扩展指导
