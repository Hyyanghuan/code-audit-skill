# Code Audit Web 控制台

前后端分离的 Web 界面：登录 → 填写 GitHub Token → 选择仓库 → 执行 Code Audit Skill → 在线查看/下载文档 → 手动推送 Telegram。

## 系统配置（中文开关）

登录后进入 **系统配置**，可修改并保存：

| 分组 | 内容 |
|------|------|
| 通用设置 | 审计预设、目标目录、失败策略、SARIF 等 |
| 扫描模块 | 14 个 enable-* 开关（中文标签） |
| 工具与路径 | Super-Linter 语言、gitleaks/规则/忽略路径 |
| Web 控制台 | 文档保留时长、是否自动推送 TG |
| Telegram | 连接信息 + 5 项推送内容开关 |

新建审计任务自动使用已保存配置；修改任意模块开关会自动切换为「自定义」预设。

## 快速启动

```bash
cd web
docker compose up --build -d
```

浏览器打开：**http://localhost:8088**

> 默认映射端口为 `8088:80`（若本机 8080 已被占用）。可在 `docker-compose.yml` 中改为 `"8080:80"`。

默认登录：

- 用户名：`2634564881@qq.com`
- 密码：`Admin123`

## 架构

```
┌─────────────┐     /api/*      ┌──────────────┐
│  frontend   │ ──────────────► │   backend    │
│  (nginx)    │                 │  (FastAPI)   │
│  :8080      │                 │  :8000       │
└─────────────┘                 └──────┬───────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              /skill (ro)          /data/jobs         git clone
              审计脚本              72h 文档            临时目录
```

- **backend** 挂载仓库根目录为 `/skill`（只读）
- **audit-data** 卷持久化任务与 Telegram 配置

## 本地开发（不用 Docker）

### 后端

```bash
cd web/backend
pip install -r requirements.txt
export WEB_SKILL_PATH=e:/AIskiils   # Git Bash: /e/AIskiils
export WEB_DATA_DIR=./data
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd web/frontend
npm install
npm run dev
```

访问 http://localhost:5173（Vite 代理 `/api` → 8000）

## API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/github/repos` | 列出 GitHub 仓库 |
| POST | `/api/audits` | 创建审计任务 |
| GET | `/api/audits/{id}/documents` | 文档列表 |
| GET | `/api/audits/{id}/documents/{name}/download?format=md\|csv\|xlsx` | 下载 |
| PUT | `/api/settings/telegram` | 保存 TG 配置 |
| POST | `/api/audits/{id}/telegram/send` | 一键发送 |
| POST | `/api/audits/{id}/telegram/send/{filename}` | 单文件发送 |

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `WEB_SKILL_PATH` | `/skill` | Skill 仓库挂载路径 |
| `WEB_DATA_DIR` | `/data` | 任务与配置存储 |
| `WEB_JOB_RETENTION_HOURS` | `72` | 文档保留小时数 |
| `WEB_JWT_SECRET` | 内置 dev 值 | 生产务必修改 |
| `WEB_AUTH_USERNAME` | `2634564881@qq.com` | 可覆盖写死账户 |
| `WEB_AUTH_PASSWORD` | `Admin123` | 可覆盖写死密码 |

## 注意事项

1. 审计在 **Linux 容器** 内运行（gitleaks/bandit 依赖），请用 Docker 部署 backend。
2. GitHub Token 仅存于浏览器 `localStorage`，请求时传给后端用于 clone，**不会写入数据库**。
3. Telegram 配置存于 SQLite `/data/web.db`，与仓库内 `config/telegram.yaml` 独立。
4. 生产环境请修改 `WEB_JWT_SECRET` 并通过 HTTPS 暴露服务。

## 相关文档

- [LOCAL-RUN.md](../docs/LOCAL-RUN.md) — Skill 脚本本地运行
- [DEPLOYMENT.md](../DEPLOYMENT.md) — GitHub Actions 接入
