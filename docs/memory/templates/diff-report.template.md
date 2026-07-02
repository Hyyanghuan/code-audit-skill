# 差异报告 — {TASK_ID} {TITLE}

> 生成时间：{TIMESTAMP}  
> 对比基准：`{BASE_REF}` → `{HEAD_REF}`  
> 生成方式：`bash scripts/generate-memory-report.sh {TASK_ID} "{TITLE}" [--base {BASE_REF}]`

---

## 1. 变更概览

| 指标 | 值 |
|------|-----|
| 变更文件数 | {FILE_COUNT} |
| 新增行 | {INSERTIONS} |
| 删除行 | {DELETIONS} |

```
{DIFF_STAT}
```

---

## 2. 文件清单与模块归属

| 文件 | 变更类型 | 归属模块 | Spec |
|------|----------|----------|------|
{FILE_TABLE_ROWS}

---

## 3. 功能影响分析

{IMPACT_SECTION}

### 3.1 运行时影响

| 影响面 | 级别 | 说明 |
|--------|------|------|
| Action 编排 | {LEVEL} | {NOTE} |
| 扫描结果 | {LEVEL} | {NOTE} |
| 制品/TG | {LEVEL} | {NOTE} |
| 业务仓接入 | {LEVEL} | {NOTE} |

### 3.2 契约变更（如有）

- [ ] 无 spec / action inputs 变更
- [ ] 有契约变更 → 已更新 spec：{SPEC_LINKS}

---

## 4. 行为变化说明（人工/Agent 补充）

<!-- 对比前后行为差异，每条：场景 → 之前 → 之后 -->

1. 

---

## 5. 回归建议

| 场景 | Fixture / 命令 | 预期 |
|------|----------------|------|
| 自测 | Actions → Self Test | {EXPECTED} |
| 本地 | `bash scripts/generate-memory-report.sh ...` | 报告生成成功 |

---

## 6. 原始 diff（可选，大改动时折叠）

<details>
<summary>展开 git diff</summary>

```diff
{DIFF_PATCH}
```

</details>
