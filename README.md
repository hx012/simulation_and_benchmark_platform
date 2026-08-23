# Ascend Simulator & Benchmark Platform

面向公司内部用户的 AI 芯片仿真任务管理与 Benchmark 资产浏览平台。

当前仓库已经形成可在 Linux 服务器和 WSL 开发环境运行的基础版本：React 前端、FastAPI 后端、PostgreSQL 元数据存储、Simulation Worker、任务日志/结果/Trace 展示，以及 Benchmark Registry 只读浏览。

## 统一启停

首次部署复制并修改平台配置，然后使用同一套 Linux 脚本管理全部服务：

```bash
cp .env.platform.example .env.platform
cp backend/.env.example backend/.env
bash scripts/platform.sh start dev
bash scripts/platform.sh status
bash scripts/platform.sh stop
```

工作服务器使用 `start server`。脚本会验证 PostgreSQL 必须挂载 named volume，发现旧匿名卷时拒绝启动并提示安全迁移。

## 文档入口

- [文档导航](docs/README.md)
- [AI / 新开发者快速上下文](docs/AI_CONTEXT.md)
- [当前代码基线](docs/00_Project/BASELINE_STATUS.md)
- [后续开发路线图](docs/00_Project/ROADMAP.md)
- [Linux 服务器启动](docs/04_Startup/startup.md)
- [WSL 本地启动](docs/04_Startup/wsl_startup.md)
- [开发接手指南](docs/06_Development/DEVELOPMENT_GUIDE.md)

新会话或新开发者建议先依次阅读：`AI_CONTEXT.md`、`BASELINE_STATUS.md`、`ROADMAP.md`。

## 目录

```text
simulation_and_benchmark_platform/
├── backend/      # FastAPI、Simulation/Benchmark 业务、Worker、Alembic
├── frontend/     # React + TypeScript + Vite + Ant Design
├── docs/         # 项目 Source of Truth 和开发记录
├── runtime/      # 本地任务运行数据，不提交 Git
└── tools/        # 本地第三方工具，不纳入当前基线 PR
```

完整启动步骤见 [Linux 服务器启动指南](docs/04_Startup/startup.md)；Windows 开发机的项目路径 `D:\code\chip_simulation\simulation_and_benchmark_platform` 在 WSL 中对应 `/mnt/d/code/chip_simulation/simulation_and_benchmark_platform`。
