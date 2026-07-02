# 模块 Spec 索引

各模块 **接口 / 交互 / 验收标准** 联调契约。实现变更时须同步更新对应 spec。

| 目录 | 模块 | Action input |
|------|------|--------------|
| [action-core](./action-core/spec.md) | 编排 / init / finalize | 全部 inputs & outputs |
| [scan-gitleaks](./scan-gitleaks/spec.md) | Gitleaks 密钥 | `enable-gitleaks` |
| [scan-bandit](./scan-bandit/spec.md) | Bandit Python | `enable-bandit` |
| [scan-super-linter](./scan-super-linter/spec.md) | Super-Linter | `enable-super-linter` |
| [scan-dependency](./scan-dependency/spec.md) | Trivy SCA | `enable-dependency-scan` |
| [scan-custom-rules](./scan-custom-rules/spec.md) | YAML 业务规则 | `enable-custom-rules` |
| [audit-engine](./audit-engine/spec.md) | 内置 9 子模块 | `enable-sast-patterns` 等 9 项 |
| [test-cases](./test-cases/spec.md) | 验收测试用例 | `enable-test-cases` |
| [bug-report](./bug-report/spec.md) | Bug MD/JSON | always |
| [telegram](./telegram/spec.md) | TG 推送 | `enable-telegram` |
| [artifacts](./artifacts/spec.md) | 制品上传 | `upload-artifacts` |

---

## 联调顺序建议

1. 阅读 [action-core](./action-core/spec.md) 掌握全局 inputs/outputs
2. 按负责模块阅读 scan / engine spec
3. 后处理链：[bug-report](./bug-report/spec.md) → [artifacts](./artifacts/spec.md) → [telegram](./telegram/spec.md)
4. 端到端验收对照 [test-cases](./test-cases/spec.md) 与 `test-fixtures/`
5. 会话续接读 [memory/CONTEXT.md](../memory/CONTEXT.md)；关任务跑 `scripts/generate-memory-report.py`
