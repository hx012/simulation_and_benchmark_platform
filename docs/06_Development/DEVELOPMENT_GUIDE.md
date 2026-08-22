# 开发接手指南

本文档用于新开发者或新 AI 会话快速接手当前代码。

## 1. 开始前

按顺序阅读：

1. `docs/AI_CONTEXT.md`
2. `docs/00_Project/BASELINE_STATUS.md`
3. `docs/00_Project/ROADMAP.md`
4. 与任务相关的 Product / Architecture / Startup 文档

然后执行：

```bash
git status --short --branch
git log --oneline -5
```

工作区可能包含用户本地数据。不得提交或删除 `runtime/`、`tools/`、`.env`、虚拟环境和未确认的用户改动。

## 2. 代码入口

### Backend

```text
backend/app/main.py                    FastAPI 入口
backend/app/api/simulation.py          Simulation API
backend/app/api/benchmark.py           Benchmark API
backend/app/common/config.py           环境配置
backend/app/common/database.py         SQLAlchemy Engine/Session
backend/app/simulation/                Simulation 业务层
backend/worker/simulation_worker.py    Worker 入口
backend/alembic/                       数据库迁移
```

### Frontend

```text
frontend/src/App.tsx                   路由
frontend/src/api/                      API Client
frontend/src/auth/AuthContext.tsx      开发态身份
frontend/src/pages/simulation/         Simulation 页面
frontend/src/pages/benchmark/          Benchmark 页面
frontend/src/components/               通用组件和 Trace Viewer
```

## 3. 常用命令

Linux 服务器和 WSL 使用同一入口。Windows 路径 `D:\code\chip_simulation\simulation_and_benchmark_platform` 对应 WSL 路径 `/mnt/d/code/chip_simulation/simulation_and_benchmark_platform`：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform
bash scripts/platform.sh start dev
bash scripts/platform.sh status
bash scripts/platform.sh logs
bash scripts/platform.sh stop
```

工作服务器使用 `bash scripts/platform.sh start server`。完整配置和故障排查见 `docs/04_Startup/startup.md` 与 `docs/04_Startup/wsl_startup.md`。

后端基础检查：

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run alembic check
uv run python scripts/test_simulation_task_management.py
uv run python scripts/test_simulation_capabilities.py
```

前端检查：

```bash
cd frontend
npm install
npm run typecheck
npm run build
```

WSL 必须使用 Linux 版 `node` 和 `npm`。如果 `command -v npm` 指向 `/mnt/c/Program Files/nodejs`，先在 WSL 安装 Node，再删除并重装 `node_modules`。

## 4. 恢复本地演示任务

数据库和 Backend 启动后执行：

```bash
cd backend
uv run python scripts/seed_local_completed_task.py \
  --trace-source /mnt/c/Users/zyp/Downloads/trace_sample.json \
  --owner-id test-user
```

该脚本会在仓库根目录 `runtime/<task_id>/` 生成日志、summary 和 Trace，并新增或更新数据库任务。Trace 文件属于本地输入，不进入 Git。

为已有任务生成 Catapult Viewer：

```bash
cd backend
uv run python scripts/build_trace_viewers.py --all --dry-run
uv run python scripts/build_trace_viewers.py --all
```

Catapult 默认从仓库根目录 `tools/catapult` 读取，也可以通过 `CATAPULT_HOME` 和 `CATAPULT_PYTHON` 指向部署环境中的固定版本。当前验证并要求打包的版本是 `1d18f6e11082de030c45fd55b556d15e3aa628a8`。生成文件位于 `runtime/<task_id>/result/trace/trace.html`，不进入 Git。

`tools/` 被 Git 忽略，PR 只提交适配代码和版本文档，不提交 Catapult 源码。制作离线服务器包时必须显式包含 `tools/catapult`。WSL 项目位于 `/mnt/*` 时，Catapult 大量小文件的冷读取可能超过转换超时；本地可把同一 commit 缓存到 Linux 原生文件系统并仅在本机 `.env` 覆盖 `CATAPULT_HOME`，公司原生 Linux 服务器仍使用项目内目录。

`catapult_trace2html.py` 会向生成的 HTML 注入平台集成桥。Catapult 解析期间隐藏其原生 `Importing...` overlay，完成、失败或超时后向父页面发送状态。调整该逻辑后必须强制回填测试任务并做浏览器验证：

```bash
uv run python scripts/build_trace_viewers.py \
  --task-id <task-id> \
  --force
```

如果页面使用其他工号登录，将 `--owner-id` 改为当前工号；“我的任务”会按 `owner_id` 严格过滤。

## 5. 修改约束

- API 改动同步更新前端类型和文档。
- 数据库结构改动新增 migration，并执行 `alembic check`。
- Simulation 代码沿用 API -> service -> repository 的现有边界。
- 文件读写必须限制在 `TASK_ROOT` 或 Upload Session 目录内。
- 真实 Simulator 路径通过 `.env` 和 Profile 配置，不写入代码。
- Benchmark Registry 是定义来源，不在平台维护第二套注册信息。
- 新功能至少提供一个成功路径和一个失败路径验证。

## 6. PR 交付清单

1. 从最新 `main` 创建 `codex/` 或 `feature/` 分支；依赖未合入 PR 时，从父 PR 分支创建堆叠分支并将 PR base 指向父分支。
2. 只暂存本次任务文件，不使用 `git add .`。
3. 检查 `git diff --check` 和最终 staged diff。
4. 运行与改动风险匹配的测试。
5. PR 描述写明范围、验证结果、已知限制和文档变化。
6. 默认先创建 Draft PR，验证和评审完成后再转 Ready。
7. Catapult 相关 PR 必须写明验证 commit；离线工具目录通过部署包交付，不得误认为 PR 会包含 `tools/`。
