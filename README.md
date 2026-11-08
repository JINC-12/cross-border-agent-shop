# 跨境电商 Agent 自动化平台

一个基于 **FastAPI + LangGraph** 的 AI Agent 驱动的跨境电商自动化平台，用于自动生成商品 Listing、AI 选品分析、广告素材脚本等。

项目按阶段开发，当前进度：**阶段1（工程骨架）已完成**。

## 技术栈

| 分层 | 技术 |
| --- | --- |
| 后端 | Python 3.14 + FastAPI + Uvicorn |
| Agent | LangGraph + langchain-openai |
| 数据库 | MySQL（原生 mysql-connector）+ Redis 缓存 |
| 前端 | Vue3（阶段5开发，暂未开始） |

## 目录结构

```text
cross-border-agent-shop/
├── backend/
│   ├── __init__.py          # 包标记文件
│   ├── main.py              # FastAPI 入口：创建 app、CORS、注册路由
│   ├── settings.py          # 读取 .env 的统一配置模块
│   ├── db.py                # MySQL 连接工具（原生 mysql-connector）
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py        # 根路径 / 与健康检查 /health
│   └── agent/
│       ├── __init__.py
│       └── skills/          # 预留：Agent 技能目录
├── frontend/                # 预留：Vue3 前端（阶段5）
├── docs/                    # 项目文档
├── .env.example             # 环境变量模板（提交到仓库）
├── .env                     # 本地真实配置（不提交）
├── .gitignore
├── requirements.txt
└── README.md
```

## 环境搭建

### 1. 创建并激活虚拟环境

Git Bash：

```bash
python -m venv venv
source venv/Scripts/activate
```

PowerShell：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

Git Bash：

```bash
cp .env.example .env
```

PowerShell：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env` 填写真实配置。阶段1暂时不需要填大模型密钥，MySQL / Redis 也先留空即可。

> `.env` 已被 `.gitignore` 忽略，真实密钥不会进入 Git 仓库。

## 启动项目

```bash
uvicorn backend.main:app --reload
```

启动成功后可访问：

- 服务首页：http://127.0.0.1:8000/
- 健康检查：http://127.0.0.1:8000/health
- 接口文档（Swagger）：http://127.0.0.1:8000/docs

健康检查返回示例：

```json
{
  "status": "ok",
  "app": "cross-border-agent-shop",
  "version": "0.1.0",
  "env": "dev"
}
```

## 配置项说明

配置全部通过 `.env` 读取，由 `backend/settings.py` 统一管理：

| 配置项 | 说明 |
| --- | --- |
| `APP_ENV` / `DEBUG` | 运行环境与调试开关 |
| `CORS_ORIGINS` | 允许跨域的前端地址，逗号分隔 |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | 大模型配置（阶段2使用） |
| `MYSQL_*` | MySQL 连接配置（暂未启用） |
| `REDIS_*` | Redis 连接配置（暂未启用） |

## MySQL 连接自测

MySQL 安装并启动、且在 `.env` 中填好账号密码后，可以执行：

```bash
python -c "from backend.db import check_mysql_connection; print(check_mysql_connection())"
```

成功返回 `(True, 'MySQL 连接正常')`；失败会打印中文排查步骤。

## 开发阶段规划

- [x] 阶段1：工程骨架 + 配置 + 健康检查 + 版本管理
- [ ] 阶段2：商品生成模块（LangGraph 最小 Agent + 接口）
- [ ] 阶段3：AI 选品模块
- [ ] 阶段4：广告素材生成模块
- [ ] 阶段5：Vue3 前端

## Git 使用

```bash
git add .
git commit -m "chore: 完成阶段1工程骨架"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```
