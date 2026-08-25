# 当前工程基线

> **Baseline:** B0
> **Date:** 2026-08-22
> **Status:** Accepted as development baseline

本文档只描述当前仓库已经实现并验证的能力。产品目标和远期设计分别见 `PRD.md`、`V1_SCOPE.md` 和 `ROADMAP.md`。

## 1. 基线定义

当前代码作为后续优化开发的起点。原则上不再以大规模重写替代现有 Simulation 主链路；新增能力应沿用现有 API、service、repository、workspace 和 Worker 边界，通过独立分支和 PR 迭代。

## 2. 已实现能力

### Frontend

- React、TypeScript、Vite、Ant Design 基础应用。
- 双入口登录：普通工号登录，以及需要密码的管理员登录；身份由后端 HttpOnly 会话 Cookie 管理。
- Simulation 新建任务、我的任务、任务详情、运行日志、结果和 Catapult Trace 页面。
- Trace Viewer 支持浏览器全屏、`Esc` 退出、新窗口打开、导入弹窗隐藏和存量任务 React Viewer 回退。
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
- 日志分块读取、`summary.json`、Chrome Trace Format 和 Catapult Viewer 产物读取。
- Worker 调用 Catapult `trace2html` 生成独立 `trace.html`，Trace 转换失败不影响 Simulation 终态。
- Simulator Profile / Capabilities 配置。
- Benchmark Registry 只读适配。

### Local Development

- Docker PostgreSQL 镜像定义。
- 根级 Compose 使用 external named volume `ascend-platform-postgres-data` 持久化 PostgreSQL。
- Linux 通用 `scripts/platform.sh` 统一管理数据库、Alembic、Backend、Worker 和 Frontend，支持 dev/server/static、启停、状态和日志；static模式由Nginx直接托管已发布前端。
- 匿名 PostgreSQL volume 检测与一次性逻辑备份/恢复迁移脚本。
- Linux/WSL 启动文档、systemd 示例、`.env.platform.example` 和后端/前端环境变量示例。
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
    └── trace/
        ├── trace.html
        └── dumps/trace.json
```

默认本地配置从 `backend` 目录解析：

```env
TASK_ROOT=../runtime
DATABASE_URL=postgresql+psycopg://ascend_platform:12345678@127.0.0.1:15432/ascend_platform
```

## 4. 已验证路径

- `GET /health` 可用。
- Alembic `upgrade head` 和 `check` 可用。
- `platform.sh` 的 dev/server/static、重复启动、优雅关闭和模式切换保护可用；static模式不启动5173，并验证Nginx健康地址和已发布入口文件。
- PostgreSQL named volume 挂载校验及匿名卷迁移前后任务数校验可用。
- 成功任务可在“我的任务”列表显示。
- 任务详情可以增量读取 10,000 行日志。
- 结果接口可以读取 summary 和 Trace。
- Trace 样例可以转换为 Catapult Viewer 并在前端 iframe 展示。
- V310 样例可以复制到 Upload Session 并通过静态 YAML 校验。

本地演示任务默认信息：

```text
Task ID: SIM-20260818-024736-A3051FC3
Owner: admin
Status: COMPLETED
Trace Status: READY
```

演示任务是本地数据，不在 Git 中。恢复命令见 `DEVELOPMENT_GUIDE.md`。

## 5. 当前明确边界

- 真实公司 Simulator 尚未在本地接入；Profile 中部分真实路径仍是部署占位值。
- Worker 具有 Mock 执行能力，但前端 Capabilities 尚未提供完整的本地 Mock 配置闭环。
- Benchmark 目前只读取 Registry；Result Provider 返回空结果，不执行 Benchmark。
- 普通工号识别仍是开发态方案，尚未接入正式 SSO；管理员已经使用数据库角色、密码哈希和后端会话认证。
- 当前自动授予 `normal`；`benchmark_access` 与 `simulation_log` 可申请。管理员模式默认具备全部启用的 Permission Set。
- Permission Set 名称、说明、可申请状态，以及模块的普通/指定权限/仅管理员/未开放策略均由数据库管理，可在权限中心配置；代码只注册稳定资源代码并执行策略。
- 支持多个管理员，提升管理员时必须配置密码，并保护最后一个有效管理员不被移除或停用。
- 原始 Trace、其他 Simulation 接口的完整所有权收口、正式身份水印和 Audit 尚未实现。
- Compare、Analysis Report 和完整 Admin 统计尚未形成完整实现。
- Catapult 工具目录不进入 Git，离线部署包必须携带固定 commit `1d18f6e11082de030c45fd55b556d15e3aa628a8`，并通过 `CATAPULT_HOME` 指向该目录；继续验证大 Trace 的资源上限。

## 6. 基线变更规则

- 行为变更必须通过 feature 分支和 PR。
- 数据模型变化必须新增 Alembic migration，不修改已发布 migration。
- 不提交 `.env`、`runtime/`、`tools/`、虚拟环境、`node_modules` 或 Python 缓存。
- 公司服务器路径只放环境变量或 Profile，不写死在业务代码。
- 每个 PR 应提供验证命令，并同步更新相关文档。
