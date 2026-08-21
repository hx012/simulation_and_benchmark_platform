# Ascend Simulator & Benchmark Platform

面向公司内部用户的 AI 芯片仿真任务管理与 Benchmark 资产浏览平台。

当前仓库已经形成可在 WSL 本地运行的基础版本：React 前端、FastAPI 后端、PostgreSQL 元数据存储、Simulation Worker、任务日志/结果/Trace 展示，以及 Benchmark Registry 只读浏览。

## 文档入口

- [文档导航](docs/README.md)
- [AI / 新开发者快速上下文](docs/AI_CONTEXT.md)
- [当前代码基线](docs/00_Project/BASELINE_STATUS.md)
- [后续开发路线图](docs/00_Project/ROADMAP.md)
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

本地完整启动步骤见 [WSL 本地开发启动指南](docs/04_Startup/wsl_startup.md)。
