# Contributing

感谢参与 Code Audit Skill 贡献。本仓库采用 **文档驱动 + spec 契约** 流程。

## 开发环境

- Git、Bash、Python 3.10+
- （可选）Docker / act 模拟 Actions

```bash
pip install pyyaml pytest
pytest tests/ -q
```

## 提交前检查

```bash
# 单元测试
pytest tests/ -q

# 本地 TG 配置（勿提交）
cp config/telegram.yaml.example config/telegram.local.yaml
export TG_BOT_TOKEN=... TG_CHAT_ID=...

# 记忆层关任务（文档/脚本变更）
python scripts/generate-memory-report.py <ID> "<标题>" --no-send-tg
```

## 变更类型与要求

| 类型 | 必须更新 |
|------|----------|
| 新扫描模块 | `action.yml` + `init.sh` + `docs/specs/` + `module-map.yaml` |
| 规则变更 | `config/*.yaml` + 相关 spec |
| TG/通知 | `docs/specs/telegram/spec.md` + `SECURITY.md` |
| Breaking Change | `CHANGELOG.md` + major 版本 + migration 说明 |

## 分支与 PR

1. 从 `main` 拉 feature 分支  
2. 小步 PR，描述链接相关 `tasks.md` ID  
3. 确保 `enterprise-ci` / `self-test` 通过  
4. 文档变更同步 `docs/memory/CONTEXT.md`（若关任务）

## 代码规范

- Shell：`set -uo pipefail`，复用 `scripts/common.sh`
- Python：类型提示优先，单文件职责清晰
- 不增加无测试的过度抽象

## 语义化版本

- **MAJOR**：Breaking（input 默认值、输出格式、模块行为）  
- **MINOR**：新功能向后兼容  
- **PATCH**：修复、规则微调  

## 联系

见 [SECURITY.md](./SECURITY.md) 安全报告渠道。
