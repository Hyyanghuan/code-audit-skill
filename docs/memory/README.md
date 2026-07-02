# 记忆层（Memory Layer）

> 减少 Token · 避免重复劳动 · **六棱镜理解需求** · **关任务逻辑比对**

---

## 为什么需要记忆层？

| 问题 | 解法 |
|------|------|
| 每次重读 README/全量 spec | [CONTEXT.md](./CONTEXT.md) 热快照 |
| 需求理解单一、漏功能 | [六棱镜 intake](./REQUIREMENT-GUIDE.md) |
| 关任务不知是否做对 | [requirement-audit](./REQUIREMENT-GUIDE.md) 八项逻辑比对 |
| 改完不知影响哪些模块 | diff 报告 + [module-map.yaml](./module-map.yaml) |

---

## 目录结构

```
docs/memory/
├── CONTEXT.md                 # ★ 会话入口（省 Token）
├── REQUIREMENT-GUIDE.md       # ★ 需求理解工作流
├── requirement-lens.yaml      # 六棱镜 + 五维 + 八项定义
├── module-map.yaml
├── intake/{TASK-ID}.md        # 开任务：多视角需求探索
├── templates/
│   ├── requirement-intake.template.md
│   ├── requirement-audit.template.md
│   ├── diff-report.template.md
│   └── completion-report.template.md
└── reports/
    ├── *-diff.md
    ├── *-completion.md
    └── *-requirement-audit.md   # 关任务：逻辑缜密性比对
```

---

## 标准工作流（三阶段）

```mermaid
flowchart TB
    subgraph 理解
        A[--init-intake] --> B[填六棱镜 + 功能矩阵]
    end
    subgraph 实施
        C[改代码] --> D[module-map 预判]
    end
    subgraph 比对
        E[generate-memory-report] --> F[diff + audit + completion]
        F --> G[audit §7 门禁通过]
        G --> H[更新 CONTEXT]
    end
    B --> C --> E
```

### 1. 开任务 — 理解多样性 + 探索完整性

```bash
python scripts/generate-memory-report.py G01 "任务标题" --init-intake --raw "用户原话"
```

编辑 `intake/G01.md`：

- **§1 六棱镜**：产品/用户/功能/技术/边界/集成 六视角
- **§2 功能矩阵**：F-01… 列做/不做/理由
- **§3 完整性自检**：开任务勾选
- **§5 确认**后再写代码

→ 详见 [REQUIREMENT-GUIDE.md](./REQUIREMENT-GUIDE.md)

### 2. 任务进行中

- 路径 → 模块： [module-map.yaml](./module-map.yaml)
- 行为对照：相关 **单个** [spec.md](../specs/)

### 3. 关任务 — 逻辑缜密性比对

```bash
python scripts/generate-memory-report.py G01 "任务标题" --goal "目标" --epic "Epic G"
```

产出三份报告：

| 报告 | 作用 |
|------|------|
| `*-diff.md` | 改了什么、影响哪些模块 |
| `*-requirement-audit.md` | 需求↔实现↔契约 三角验证、八项逻辑检查 |
| `*-completion.md` | AC 勾选、后续行动 |

**门禁**：requirement-audit §7 全过 → 更新 CONTEXT → 同步 tasks.md

---

## 报告说明

### requirement-audit（逻辑比对）

| 章节 | 内容 |
|------|------|
| §1 结论 | 完整性五维得分、逻辑八项得分 |
| §2 六棱镜↔交付 | intake 每镜与 diff 证据对齐 |
| §3 功能矩阵↔实现 | F-xx 计划 vs 代码 |
| §4 五维复检 | 范围/契约/行为/验证/文档 |
| §5 八项逻辑 | L01~L08 |
| §6 缺口/超出/矛盾 | 诚实记录 |
| §7 关任务门禁 | 未通过则回到实施或 intake |

自动判定：L04 module-map、L06 未改 action、L07 报告同批生成  
**人工必选**：L02 spec AC、L03 Out of Scope、L05 边界镜

---

## 与四件套关系

```
proposal / design / specs / tasks     ← 稳定契约
         ↑
memory/CONTEXT + intake + reports     ← 会话态 + 需求态 + 变更态
```

---

## 相关文档

- [REQUIREMENT-GUIDE.md](./REQUIREMENT-GUIDE.md) — 六棱镜与比对详解
- [design.md §九~§十](../design.md#九记忆层)
- [tasks.md Epic G](../tasks.md)
