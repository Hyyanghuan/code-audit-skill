# 本地运行指南

> 在不上传 GitHub 的情况下，于本机运行 **Code Audit Skill** 进行调试、验证规则或审计自己的代码目录。

---

## 一、运行方式总览

| 方式 | 适用场景 | 环境 | 完整度 |
|------|----------|------|--------|
| **A. 一键脚本** | 最快验证 | Git Bash / WSL / Linux / macOS | ★★★★ |
| **B. 分步 Shell** | 调试单个模块 | 同上 | ★★★★★ |
| **C. GitHub Actions** | 与线上一致 | 推送到 GitHub | ★★★★★ |
| **D. act 模拟 CI** | 本地跑 workflow | WSL/Linux + Docker | ★★★★★ |
| **E. 单元测试** | 企业级脚本/预设 | Python + pytest | ★★★ |
| **F. 记忆层报告** | 文档/任务关单 | Python | — |

---

## 二、环境准备

### 2.1 必需

| 工具 | 版本建议 | 用途 |
|------|----------|------|
| **Git Bash** 或 **WSL** | — | Windows 下运行 `.sh` 脚本（PowerShell 不能直接跑） |
| **Python** | 3.10+ | audit-engine、测试用例、SARIF |
| **pip** | — | 自动安装 bandit、pyyaml 等 |

```bash
python --version
pip install pyyaml pytest bandit
```

### 2.2 可选（脚本会自动尝试安装）

| 工具 | 说明 |
|------|------|
| gitleaks | 密钥扫描（Linux 版二进制；**Windows 原生 CMD 可能失败**，请用 WSL） |
| trivy | 依赖漏洞扫描 |
| super-linter | 体积大、耗时长，本地默认 preset 会关闭 |

### 2.3 Telegram（可选）

已配置 [`config/telegram.yaml`](../config/telegram.yaml) 时，加 `--tg` 即可本地推送。

也可使用环境变量（优先级更高）：

```bash
export TG_BOT_TOKEN="你的Token"
export TG_CHAT_ID="-100xxxxxxxxxx"
```

---

## 三、方式 A — 一键本地审计（推荐）

在 **Git Bash** 或 **WSL** 中，进入仓库根目录：

```bash
cd /e/AIskiils   # Windows Git Bash 路径示例
# 或 cd ~/AIskiils
```

### 3.1 审计内置测试夹具

```bash
# 干净项目（应通过）
bash scripts/run-local-audit.sh test-fixtures/normal-project

# 违规代码（应 failure + Bug 报告）
bash scripts/run-local-audit.sh test-fixtures/invalid-code

# 多语言
bash scripts/run-local-audit.sh test-fixtures/multi-language
```

### 3.2 审计你自己的项目目录

```bash
# 审计仓库根目录
bash scripts/run-local-audit.sh .

# 审计子目录
bash scripts/run-local-audit.sh src/backend
```

### 3.3 常用参数

```bash
# 企业预设：security（默认）| minimal | python | ci-fast | full
bash scripts/run-local-audit.sh . --preset=minimal

# 开启 Telegram 推送
bash scripts/run-local-audit.sh test-fixtures/invalid-code --tg

# 组合
bash scripts/run-local-audit.sh . --preset=python --tg
```

### 3.4 查看结果

脚本结束后，产物在临时目录（默认 Linux/WSL `/tmp`，Windows Git Bash 多为 `/tmp` 或 `$TEMP`）：

```
$RUNNER_TEMP/code-audit-local-<pid>/artifacts/
├── audit-summary.json      # 总览
├── audit-bugs.md           # Bug 报告
├── test-cases.md           # 测试用例
├── codeaudit.sarif.json    # SARIF（enable-sarif 默认开）
└── *-report.json           # 各模块明细
```

快速查看摘要：

```bash
# 将 local-12345 换成脚本输出中的 RUN_ID
cat /tmp/code-audit-local-*/artifacts/audit-summary.json
# Windows Git Bash 也可：
ls /tmp/code-audit-*/artifacts/
```

---

## 四、方式 B — 分步运行（调试单模块）

适合改规则后只验证 **audit-engine** 或某一个扫描器。

```bash
cd /e/AIskiils

export GITHUB_WORKSPACE="$(pwd)"
export GITHUB_ACTION_PATH="$(pwd)"
export GITHUB_RUN_ID="debug-001"
export RUNNER_TEMP="/tmp"
export INPUT_WORKING_DIRECTORY="test-fixtures/invalid-code"
export INPUT_FAIL_ON_FINDINGS="false"
export INPUT_ENABLE_TELEGRAM="false"
export INPUT_AUDIT_PRESET="security"

# 1. 初始化
bash scripts/init.sh

# 2. 加载环境（路径与 GITHUB_RUN_ID 一致）
source /tmp/code-audit-debug-001/env.sh

# 3. 语言检测
bash scripts/detect-languages.sh

# 4. 单模块示例 — SAST 词法
export AUDIT_MODULE=sast_patterns
bash scripts/run-audit-module.sh

# 5. 或 gitleaks
bash scripts/run-gitleaks.sh

# 6. 汇总（需前面至少跑过部分模块）
bash scripts/finalize-results.sh
bash scripts/generate-bug-report.sh
```

### 常用 `AUDIT_MODULE` 值

| 值 | 说明 |
|----|------|
| `sast_patterns` | 词法/危险函数 |
| `taint_analysis` | 污点分析 |
| `control_flow` | 控制流 |
| `config_audit` | 配置文件 |
| `specialized_security` | 专项安全 |
| `diff_audit` | git diff（需仓库有 git 历史） |
| `manual_checklist` | 人工清单 MD |

---

## 五、方式 C — GitHub Actions 云端自测

与生产最接近，**Windows 本机零配置**即可用。

1. 将仓库 push 到 GitHub  
2. 打开 **Actions → Self Test - All Scenarios**  
3. **Run workflow** → 选择场景（`all` / `invalid` / `normal` 等）

| 场景 | 目录 | 预期 |
|------|------|------|
| normal | `test-fixtures/normal-project` | 通过 |
| invalid | `test-fixtures/invalid-code` | failure |
| empty | `test-fixtures/empty-project` | 跳过 |
| network-error | 无效 TG Token | 审计完成，TG 失败不阻断 |

---

## 六、方式 D — 使用 act 本地模拟 Actions

> 需 **WSL2 + Docker**，Windows 原生支持较弱。

```bash
# 安装 act: https://github.com/nektos/act
act workflow_dispatch -W .github/workflows/self-test.yml \
  --input scenario=invalid \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

注意：Composite Action 的 `uses: ./` 在 act 下路径需与仓库结构一致；首次运行较慢（拉镜像）。

---

## 七、方式 E — 单元测试

验证企业级预设、SARIF、Telegram 配置加载等：

```bash
cd /e/AIskiils
pip install pyyaml pytest
pytest tests/ -q
```

CI 等价命令见 [`.github/workflows/enterprise-ci.yml`](../.github/workflows/enterprise-ci.yml)。

---

## 八、方式 F — 记忆层 / 需求清单（关任务）

与代码审计流水线独立，用于文档与任务交付：

```bash
# 开任务 intake
python scripts/generate-memory-report.py T01 "本地试跑" --init-intake --raw "用户原话"

# 关任务（diff + audit + 清单；默认不发 TG 可加 --no-send-tg）
python scripts/generate-memory-report.py T01 "本地试跑" --goal "验证" --no-send-tg

# 仅发需求清单 TG
python scripts/generate_requirements_checklist.py --render --send-tg --task T01 --title "本地试跑"
```

详见 [memory/REQUIREMENT-GUIDE.md](memory/REQUIREMENT-GUIDE.md)。

---

## 九、Windows 特别说明

| 问题 | 解决 |
|------|------|
| PowerShell 无法跑 `.sh` | 用 **Git Bash** 或 **WSL** |
| `gitleaks` 安装失败 | 在 WSL 内运行，或 `enable-gitleaks: false` |
| 路径 `e:\AIskiils` | Git Bash 写作 `/e/AIskiils` |
| `/tmp` 找不到产物 | 看脚本开头打印的 `RUNNER_TEMP` 路径 |
| Telegram 超时 | 检查网络/代理；清单 MD 仍会生成到 `docs/memory/reports/` |

### Windows 推荐终端

1. 安装 [Git for Windows](https://git-scm.com/)  
2. 打开 **Git Bash**（不要用 WSL 访问 `E:` 盘时若路径不存在，请直接用 Git Bash 的 `/e/AIskiils`）  
3. `cd /e/AIskiils && bash scripts/run-local-audit.sh test-fixtures/normal-project`

> Shell 脚本已配置 `.gitattributes` 强制 LF 换行；若仍报 `$'\r': command not found`，执行：  
> `python -c "p='scripts/run-local-audit.sh'; open(p,'wb').write(open(p,'rb').read().replace(b'\\r\\n',b'\\n'))"`

---

## 十、模拟业务仓「引用 Skill」

本地无法直接 `uses: org/repo@v1` 指向未发布的本地 Action，有两种做法：

### 做法 1：在 Skill 仓内指定目录（当前仓库）

```bash
bash scripts/run-local-audit.sh . --preset=security
```

等价于业务仓 `working-directory: '.'`。

### 做法 2：业务仓 + 本地 path（GitHub 不支持本地 path）

业务仓需 push 后在 workflow 中：

```yaml
- uses: YOUR_ORG/code-audit-skill@v1.0.0
  with:
    working-directory: '.'
    audit-preset: security
```

本地开发 Skill 本身时，**始终在 Skill 仓库**用本指南方式 A/B 即可。

---

## 十一、环境变量速查

| 变量 | 默认值（本地） | 说明 |
|------|----------------|------|
| `GITHUB_WORKSPACE` | 仓库根 | 被审计代码根 |
| `GITHUB_ACTION_PATH` | 仓库根 | Skill 脚本与 config |
| `GITHUB_RUN_ID` | `local-$$` | 临时目录后缀 |
| `RUNNER_TEMP` | `/tmp` | 产物父目录 |
| `INPUT_WORKING_DIRECTORY` | 脚本第 1 参数 | 相对 WORKSPACE |
| `INPUT_AUDIT_PRESET` | `security` | 见 `config/audit-presets.yaml` |
| `INPUT_ENABLE_TELEGRAM` | `false` | `--tg` 时为 true |
| `INPUT_FAIL_ON_FINDINGS` | `false` | 本地调试建议 false |

---

## 十二、常见问题

### Q1：本地和 CI 结果不一致？

- CI 是 Linux；Windows 下部分工具可能跳过（gitleaks 二进制）。  
- 差分审计需要 `git fetch-depth: 0`；本地需完整 git 历史。  
- super-linter 本地常关闭，CI 若开启会多报规范类问题。

### Q2：如何只跑安全、不跑 linter？

```bash
bash scripts/run-local-audit.sh . --preset=security
# 或
bash scripts/run-local-audit.sh . --preset=minimal
```

### Q3：如何失败时退出码非 0？

```bash
export INPUT_FAIL_ON_FINDINGS=true
bash scripts/run-local-audit.sh test-fixtures/invalid-code
# 或在 finalize 后手动: echo $? 
```

（一键脚本对单步使用 `|| true` 降级；严格门禁请用 GitHub Actions 或分步运行后在 finalize 判定。）

### Q4：产物如何复制到当前目录？

```bash
RUN_ID="local-12345"   # 换成实际
cp -r "/tmp/code-audit-${RUN_ID}/artifacts" ./local-audit-output
```

---

## 十三、相关文档

| 文档 | 内容 |
|------|------|
| [README.md](../README.md) | 快速接入与参数 |
| [DEPLOYMENT.md](../DEPLOYMENT.md) | 上传 GitHub、Secrets |
| [SECURITY.md](../SECURITY.md) | Token 与权限 |
| [examples/consumer-workflow-enterprise.yml](../examples/consumer-workflow-enterprise.yml) | 企业 workflow 模板 |
| [docs/GUIDANCE.md](GUIDANCE.md) | 可行性与 preset 说明 |

---

## 十四、快速命令卡片

```bash
# 进入仓库（Git Bash）
cd /e/AIskiils

# 最快试跑
bash scripts/run-local-audit.sh test-fixtures/normal-project

# 看违规效果
bash scripts/run-local-audit.sh test-fixtures/invalid-code

# 审计自己的代码 + TG
bash scripts/run-local-audit.sh . --preset=security --tg

# 单元测试
pytest tests/ -q
```
