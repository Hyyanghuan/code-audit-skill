# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-07-01

### Added

- 企业级 **audit-preset**：`full` | `minimal` | `security` | `python` | `ci-fast`（`config/audit-presets.yaml`）
- **SARIF 2.1.0** 输出（`enable-sarif`，GitHub Code Scanning 兼容）
- 文档体系：`docs/proposal|design|specs|tasks|GUIDANCE.md`
- 记忆层与需求六棱镜、`requirements-registry`、关任务清单 TG
- `SECURITY.md`、`CONTRIBUTING.md`、`VERSION` 文件
- CI 工作流 `enterprise-ci.yml`（单元测试 + self-test 触发）

### Changed

- **密钥治理**：`config/telegram.yaml` 不再包含 Token；优先 **Secrets / 环境变量**
- `load-telegram-config.sh` 支持 `telegram.local.yaml`（gitignore）
- 生产接入文档推荐 `@v1.0.0` 或 commit SHA，非裸 `@main`
- `DEPLOYMENT.md` 与 proposal 对齐（Secrets 优先）

### Security

- 移除仓库内明文 Bot Token（若曾泄露请立即 @BotFather 轮换）
- 新增 `config/telegram.yaml.example` 模板

## [0.9.0] - 2025-12（历史）

### Added

- Composite Action 骨架与 14 扫描模块
- Bug 报告、测试用例、Telegram 推送、test-fixtures 自测

[1.0.0]: https://github.com/YOUR_ORG/code-audit-skill/releases/tag/v1.0.0
