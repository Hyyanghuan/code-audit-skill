# 模块 Spec：Gitleaks 敏感密钥扫描

> 联调契约 | 对应：`enable-gitleaks`、`run-gitleaks.sh`

---

## 1. 职责

检测仓库中硬编码 API Key、Token、密码等敏感信息泄露。

---

## 2. 触发条件

```
enable_gitleaks == 'true'
```

无额外语言检测；全仓库扫描（受 ignore-paths 约束）。

---

## 3. 配置接口

| 来源 | 键 | 说明 |
|------|-----|------|
| Action input | `gitleaks-config` | 自定义 toml 路径，空则用内置 |
| 内置 | `config/gitleaks.toml` | 默认规则 |
| 内置 | `config/ignore-paths.txt` | 忽略 node_modules 等 |

---

## 4. 输出契约

**文件**：`$RESULTS_DIR/gitleaks.json`

```json
{
  "module": "gitleaks",
  "status": "success | failure | skipped | error",
  "findings": 0,
  "details": [],
  "report_path": "gitleaks-report.json"
}
```

**明细**：`$ARTIFACTS_DIR/gitleaks-report.json`（gitleaks 原生格式）

---

## 5. 交互

| 方向 | 说明 |
|------|------|
| → finalize | 计入 `total_findings`，failure 模块列入 `failed[]` |
| → bug-report | findings 转为 BUG-ID 条目，category 含 `hardcoded_secret` |
| → test-cases | 可生成边界值/等价类用例 |

---

## 6. 验收标准

| # | Fixture | 预期 |
|---|---------|------|
| AC-01 | `invalid-code/.env.example.leak` | `status: failure`，findings ≥ 1 |
| AC-02 | `normal-project` | `status: success` |
| AC-03 | `enable-gitleaks: false` | 无 gitleaks.json 或 skipped |
| AC-04 | gitleaks 安装失败 | `status: error`，不阻断其他模块 |
