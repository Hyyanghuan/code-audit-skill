# 需求理解工作流

> 多样性理解 · 功能探索 · 逻辑缜密性比对

---

## 三阶段流程

```
开任务                    实施中                    关任务
  │                         │                         │
  ▼                         ▼                         ▼
intake（六棱镜）      module-map 预判          diff + audit + completion + 需求清单→TG
功能探索矩阵          spec 对照                八项逻辑比对
完整性自检                                      五维完整性复检
```

| 阶段 | 产出 | 目的 |
|------|------|------|
| **理解** | `intake/{TASK-ID}.md` | 多视角消歧、列功能点、标 Out of Scope |
| **实施** | 代码 + spec 变更 | 按 intake 矩阵逐项实现 |
| **比对** | `reports/*-requirement-audit.md` + `requirements-checklist.md` | 逻辑验证 + 新/历史需求清单 TG |

---

## 六棱镜（理解多样性）

定义见 [requirement-lens.yaml](./requirement-lens.yaml)。

| 镜 | 防什么坑 |
|----|----------|
| 产品镜 | 只做功能不想边界，范围蔓延 |
| 用户镜 | 技术正确但体验没改善 |
| 功能镜 | 漏模块、漏 inputs/outputs |
| 技术镜 | 改错层、破坏配置链 |
| 边界镜 | 空项目/失败降级未测 |
| 集成镜 | 业务仓接入被破坏 |

**原则**：同一需求至少过 **产品镜 + 功能镜 + 边界镜**；跨模块任务六镜全填。

---

## 功能探索矩阵

在 intake §2 中列出：

1. 从用户原文拆功能点 F-01…
2. 标注来源（proposal / spec / 用户口头）
3. 标 **本次做 / 不做 / 下次**，并写理由
4. 关任务时在 requirement-audit 逐行比对

→ 保证 **需求完整性**（做了啥、没做啥有账可查）

---

## 逻辑缜密性八项（关任务）

| ID | 比对什么 |
|----|----------|
| L01 | 目标 ↔ diff 文件 |
| L02 | 实现 ↔ spec AC |
| L03 | 实现 ↔ proposal Out of Scope |
| L04 | diff ↔ module-map |
| L05 | 边界场景 ↔ design 策略 |
| L06 | 集成 ↔ 零配置接入 |
| L07 | diff 行为变化 ↔ completion 结果 |
| L08 | 遗留项是否诚实写入后续行动 |

自动报告对 L04、L07 部分自动判定；**L01~L03、L05~L06、L08 需人工在 intake/audit 中勾选**。

---

## 命令

```bash
# 1. 开任务：生成 intake 模板（填六棱镜后再写代码）
python scripts/generate-memory-report.py G01 "需求理解优化" --init-intake

# 2. 关任务：diff + audit + completion + 需求清单（默认发 TG）
python scripts/generate-memory-report.py H01 "需求清单与TG" --goal "..." --epic "Epic H"
# 跳过 TG：--no-send-tg

# 3. 仅复检逻辑（不重新 diff）
python scripts/generate-memory-report.py G01 "需求理解优化" --audit-only

# 4. 仅渲染/发送清单
python scripts/generate_requirements_checklist.py --render --send-tg
```

---

## 目录

```
docs/memory/
├── requirement-lens.yaml
├── requirements-registry.yaml   # ★ 新+历史需求注册表
├── REQUIREMENT-GUIDE.md
├── intake/{TASK-ID}.md
└── reports/
    ├── *-diff.md / *-completion.md / *-requirement-audit.md
    └── requirements-checklist.md   # 时间倒序，TG 附件
```

---

## 与记忆层关系

| 文件 | 何时读 |
|------|--------|
| CONTEXT.md | 每个会话开始 |
| intake/{ID}.md | 接该任务时 |
| requirement-audit.md | 关任务验收、Code Review |

---

## 相关文档

- [memory/README.md](./README.md)
- [proposal.md](../proposal.md)
- [design.md §九](../design.md#九记忆层)
