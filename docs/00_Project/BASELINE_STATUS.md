# 当前工程基线

> **Baseline:** B0
> **Date:** 2026-08-21
> **Status:** Accepted as development baseline

本文档只描述当前仓库已经实现并验证的能力。产品目标和远期设计分别见 `PRD.md`、`V1_SCOPE.md` 和 `ROADMAP.md`。

## 1. 基线定义

当前代码作为后续优化开发的起点。原则上不再以大规模重写替代现有 Simulation 主链路；新增能力应沿用现有 API、service、repository、workspace 和 Worker 边界，通过独立分支和 PR 迭代。

## 2. 已实现能力

### Frontend

- React、TypeScript、Vite、Ant Design 基础应用。
- 开发态工号登录，身份保存在浏览器 `localStorage`。
- Simulation 新建任务、我的任务、任务详情、运行日志、结果和 Trace 页面。
- Chip Config / Workload 文件树、上传、YAML/JSON 在线编辑和样例载入。
- Benchmark Vendor / Chip / Benchmark 只读浏览页面。
- `/api` 通过 Vite 代理访问 FastAPI。

### Backend

- FastAPI 应用入口、健康检查、Simulation API 和 Benchmark API。
- PostgreSQL + SQLAlchemy 数据层。
- Alembic 初始迁移，包含 `simulation_tasks`、`upload_sessions` 和索引。
- Upload Session 创建、上传、样例复制、校验、提交和过期清理。
- Simulation Task 查询、FIFO、取消、终止、归档、删除和 Rerun。
- 独立 Simulation Worker、进程组管理、Cycle 解析、结果收集和恢复处理。
- 日志分块读取、`summary.json` 读取和 Chrome Trace Format 事件读取。
- Simulator Profile / Capabilities 配置。
- Benchmark Registry 只读适配。

### Local Development

- Docker PostgreSQL 镜像定义。
- WSL 启动文档和 `.env.example`。
- V310/default/single_chip 界面样例，共 2 个 Chip Config 和 1 个 Workload 文件。
- 本地成功任务种子脚本，可生成 10,000 行日志、summary、Trace 并写入数据库。
- 运行数据统一放在仓库根目录 `runtime/`，不提交 Git。

## 3. 当前数据与文件边界

数据库只保存任务和上传会话元数据。任务文件保存在：

```text
runtime/<task_id>/
├── input/
├── runtime/
├── logs/davinci_sim.log
└── result/
    ├── summary.json
    └── trace/dumps/trace.json
```

默认本地配置从 `backend` 目录解析：

```env
TASK_ROOT=../runtime
DATABASE_URL=postgresql+psycopg://ascend_platform:12345678@127.0.0.1:15432/ascend_platform
```

## 4. 已验证路径

- `GET /health` 可用。
- Alembic `upgrade head` 和 `check` 可用。
- 成功任务可在“我的任务”列表显示。
- 任务详情可以增量读取 10,000 行日志。
- 结果接口可以读取 summary 和 Trace。
- Trace 样例可以被当前前端 Viewer 展示。
- V310 样例可以复制到 Upload Session 并通过静态 YAML 校验。

本地演示任务默认信息：

```text
Task ID: SIM-20260818-024736-A3051FC3
Owner: test-user
Status: COMPLETED
Trace Status: READY
```

演示任务是本地数据，不在 Git 中。恢复命令见 `DEVELOPMENT_GUIDE.md`。

## 5. 当前明确边界

- 真实公司 Simulator 尚未在本地接入；Profile 中部分真实路径仍是部署占位值。
- Worker 具有 Mock 执行能力，但前端 Capabilities 尚未提供完整的本地 Mock 配置闭环。
- Benchmark 目前只读取 Registry；Result Provider 返回空结果，不执行 Benchmark。
- 登录是前端开发态身份，后端尚无正式 SSO、用户表和权限校验。
- 当前任务日志和原始 Trace 可由前端读取，尚未实现 PRD 中的敏感资产权限策略。
- Compare、Analysis Report、Admin、Audit 尚未形成完整实现。
- Trace Viewer 最终采用当前 React Viewer 还是 Catapult/trace2html，仍需后续决策。

## 6. 基线变更规则

- 行为变更必须通过 feature 分支和 PR。
- 数据模型变化必须新增 Alembic migration，不修改已发布 migration。
- 不提交 `.env`、`runtime/`、`tools/`、虚拟环境、`node_modules` 或 Python 缓存。
- 公司服务器路径只放环境变量或 Profile，不写死在业务代码。
- 每个 PR 应提供验证命令，并同步更新相关文档。
