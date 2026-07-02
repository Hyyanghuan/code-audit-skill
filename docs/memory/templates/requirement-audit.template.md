# 需求逻辑比对 — {TASK_ID} {TITLE}

> 生成时间：{TIMESTAMP}  
> 关联 intake：[{INTAKE_FILENAME}](../intake/{INTAKE_FILENAME})  
> 关联 diff：[{DIFF_REPORT_FILENAME}](./{DIFF_REPORT_FILENAME})  
> 关联 completion：[{COMPLETION_REPORT_FILENAME}](./{COMPLETION_REPORT_FILENAME})

---

## 1. 比对结论

| 项 | 结果 |
|----|------|
| 完整性（五维） | {COMPLETENESS_SCORE} — {COMPLETENESS_VERDICT} |
| 逻辑缜密性（八项） | {LOGIC_SCORE} — {LOGIC_VERDICT} |
| 总体 | {OVERALL_VERDICT} |

---

## 2. 六棱镜 ↔ 交付映射

| 棱镜 | intake 要点（摘要） | 交付证据 | 对齐 |
|------|---------------------|----------|------|
{LENS_TRACE_ROWS}

**对齐图例**：✅ 一致 | ⚠️ 部分 | ❌ 缺失 | ➖ 本任务不涉及

---

## 3. 功能探索矩阵 ↔ 实现

| 功能点 | 计划 | diff/代码证据 | 对齐 |
|--------|------|---------------|------|
{FEATURE_TRACE_ROWS}

---

## 4. 完整性五维（关任务复检）

| 维度 | 检查项 | 结果 | 证据 |
|------|--------|------|------|
{COMPLETENESS_ROWS}

---

## 5. 逻辑缜密性八项

| ID | 检查项 | 结果 | 说明 |
|----|--------|------|------|
{LOGIC_ROWS}

---

## 6. 缺口与超出

### 6.1 遗漏（需求有但未做）

{GAPS}

### 6.2 超出（做了但需求未要求）

{OVER_DELIVERY}

### 6.3 矛盾（前后表述不一致）

{CONTRADICTIONS}

---

## 7. 关任务门禁

- [ ] 完整性 ≥ 80% 或已标注豁免
- [ ] 逻辑八项全 ✅ 或豁免已说明
- [ ] 遗漏/超出已写入 completion 后续行动
- [ ] intake 状态改为 ✅ 已确认

**未通过项** → 回到实施或更新 intake 后再关任务。
