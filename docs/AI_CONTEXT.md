# AI 芯片仿真与 Benchmark 平台 - AI_CONTEXT

本文档用于给 AI Agent 和新开发者快速建立项目上下文。当前工程基线见 `docs/00_Project/BASELINE_STATUS.md`，后续优先级见 `docs/00_Project/ROADMAP.md`。如果目标设计与代码不一致，以当前代码和基线状态文档为准。

## 1. 项目定位

本项目是一个面向 AI 芯片仿真任务管理和 Benchmark 数据分析的平台，目标是把以下能力整合为统一工作流：

- 仿真任务创建、排队、执行和生命周期管理。
- Simulator Version、Chip Variant、Simulation Mode 的统一配置选择。
- 仿真运行日志、summary 结果和 Trace 文件展示。
- Benchmark registry 浏览，以及后续 Benchmark 结果、对比和 Trace 分析。

平台分为两条主线：

- Simulation Platform：负责仿真任务上传、校验、提交、Worker 调度、结果收集和展示。
- Benchmark Platform：负责芯片、Benchmark 定义和未来结果数据的管理展示。

## 2. 仓库结构

```text
simulation_and_benchmark_platform/
├── README.md
├── docs/
│   ├── AI_CONTEXT.md
│   ├── 00_Project/
│   ├── 01_Product/
│   ├── 03_Architecture/
│   ├── 04_Startup/
│   └── 06_Development/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── benchmark/
│   │   ├── common/
│   │   └── simulation/
│   ├── config/
│   ├── scripts/
│   ├── worker/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── styles/
│   │   ├── types/
│   │   └── utils/
│   └── package.json
├── runtime/              # 本地任务数据，不提交 Git
└── tools/                # 本地第三方工具，不纳入当前基线
```

说明：

- `backend/app/main.py` 是当前 FastAPI 应用入口。
- `backend/app/api/health.py` 提供健康检查接口。
- `docs/README.md` 是文档入口，新会话先读本文件、`BASELINE_STATUS.md` 和 `ROADMAP.md`。
- `runtime/` 与 `backend/` 同级，由 `TASK_ROOT=../runtime` 指向。
- `tools/` 当前包含 Catapult 相关工具代码，文件量很大，当前明确不纳入基线 PR。

## 3. 技术栈

前端：

- React
- TypeScript
- Vite
- Ant Design
- React Router

后端：

- Python 3.10+
- FastAPI
- Pydantic / pydantic-settings
- SQLAlchemy
- PostgreSQL
- PyYAML
- python-multipart

## 4. 后端入口与配置

后端入口：

```text
backend/app/main.py
```

当前入口会创建 FastAPI app，并注册：

- `/health`
- `/api/simulation/...`
- `/api/benchmark/...`

关键配置文件：

```text
backend/app/common/config.py
backend/app/benchmark/config.py
backend/config/simulator_profiles.yml
backend/config/simulator_profiles.multi.example.yml
.env.platform.example
backend/alembic.ini
backend/migrations/
```

通用环境变量由 `app.common.config.Settings` 读取，重要字段包括：

- `POSTGRES_HOST` / `POSTGRES_PORT`
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`
- `TASK_ROOT`
- `SIMULATOR_HOME`
- `SIMULATOR_PROFILES_FILE`
- `SST_EXECUTABLE`
- `SIM_WORKER_ID`
- `SIM_MAX_CONCURRENT_TASKS`
- `SIM_USER_TASK_LIMIT`
- `SIM_SAMPLE_TEMPLATE_ROOT`
- `ANALYTICS_EVENT_RETENTION_DAYS`（原始用户行为保留天数，`0` 表示永久保留）
- `ANALYTICS_CLEANUP_INTERVAL_HOURS`（Worker 自动清理检查间隔）

Benchmark 使用 `AIBENCH_HOME` 读取现有 aibench registry。

注意：`backend/app/common/database.py` 在导入时要求数据库连接已配置。Backend 从根目录 `.env.platform` 的 `POSTGRES_*` 自动构造连接地址；`DATABASE_URL` 仅保留为显式覆盖项。

本地开发默认从 `backend` 目录启动，使用：

```env
TASK_ROOT=../runtime
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=15432
POSTGRES_USER=ascend_platform
POSTGRES_PASSWORD=12345678
POSTGRES_DB=ascend_platform
```

完整平台从仓库根目录统一启停：

```bash
cp .env.platform.example .env.platform
bash scripts/platform.sh setup
bash scripts/platform.sh update
bash scripts/platform.sh start dev
bash scripts/platform.sh status
bash scripts/platform.sh stop
```

工作 Linux 服务器使用Vite Preview时运行 `start server`；Nginx直接托管前端时运行 `start static`。static模式不启动5173；代码更新后使用 `deploy-static` 一键构建并发布到 `FRONTEND_DEPLOY_DIR`，普通启停继续使用 `start/restart static`。部署细节见 `docs/04_Startup/domain_elb_nginx.md`。PostgreSQL 必须挂载 external named volume `ascend-platform-postgres-data`；脚本检测到匿名卷时拒绝启动，已有匿名卷通过 `scripts/migrate-postgres-volume.sh` 一次性迁移。

## 5. Simulation 当前实现

Simulation 的核心代码位于：

```text
backend/app/simulation/
backend/app/api/simulation.py
backend/worker/simulation_worker.py
```

核心模型：

- `SimulationTask`
- `UploadSession`

任务状态：

- `QUEUED`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`
- `TERMINATED`

执行阶段：

- `WAITING`
- `PREPARING`
- `STARTING`
- `EXECUTING`
- `COLLECTING`
- `FINISHED`

Trace 状态：

- `NOT_REQUESTED`
- `PENDING`
- `GENERATING`
- `READY`
- `FAILED`

上传会话状态：

- `UPLOADING`
- `READY`
- `VALIDATING`
- `INVALID`
- `COMMITTING`
- `SUBMITTED`
- `EXPIRED`

## 6. Simulation 任务流程

标准流程：

```text
前端创建 Upload Session
        ↓
上传或套用样例 chip_config / workload
        ↓
后端校验上传内容
        ↓
提交 Upload Session
        ↓
创建 SimulationTask 和独立 workspace
        ↓
Worker FIFO claim 任务
        ↓
准备 runtime 输入
        ↓
启动 SST / Simulator 子进程
        ↓
更新日志、cycle、runtime
        ↓
收集 summary / trace
        ↓
任务进入终态
```

相关服务：

- `UploadSessionService`：上传会话创建、文件替换、过期清理。
- `UploadSessionValidator`：检查 chip_config / workload 文件结构和引用安全性。
- `SimulationSubmissionService`：提交上传会话、创建任务 workspace、支持 rerun。
- `TaskWorkspaceManager`：创建、克隆、删除任务 workspace。
- `SimulationTaskService`：任务状态流转、取消、终止、归档。
- `SimulationTaskIOService`：读取日志、summary 和 trace。
- `SimulationWorker`：后台领取任务、启动仿真、采集进度和结果。

## 7. Workspace 与文件组织

每个仿真任务拥有独立 workspace，避免日志、结果和 Trace 相互覆盖。

典型结构：

```text
TASK_ROOT/
└── SIM-xxxx/
    ├── input/
    │   ├── chip_config/
    │   └── workload/
    ├── runtime/
    │   └── resolved_config/
    ├── logs/
    │   └── davinci_sim.log
    └── result/
        ├── summary.json
        └── trace/
            └── dumps/
                └── trace.json
```

数据库保存任务状态、路径和元数据；日志、summary、trace 这类大文件保存在文件系统中。

仓库内置一个用于界面开发的 V310 样例：

```text
backend/config/simulation_templates/v310/default/single_chip/
├── chip_config/
│   ├── simulator_config.yml
│   └── daw_config.yml
└── workload/
    └── workload.yml
```

## 8. Simulator Profile

默认 Profile 配置入口：

```text
backend/config/simulator_profiles.yml
```

公司真实配置通过 `.env.platform` 的 `SIMULATOR_PROFILES_FILE` 指向不提交 Git 的部署文件。

Profile 描述：

- `simulator_version`
- `simulator_label`
- `chip_variant`
- `chip_variant_label`
- `simulation_mode`
- `simulation_mode_label`
- `entry_script`
- `sst_args`

选择层级：

```text
Simulator Version
        ↓
Chip Variant
        ↓
Simulation Mode
```

`SimulatorAdapter` 会根据任务选择的 profile 生成 `LaunchSpec`，设置：

- SST 命令行。
- Simulator 工作目录。
- `DAVINCI_SIM_ROOT`
- `DAVINCI_DUMP_DIR`
- `DAVINCI_SIMULATOR_CONFIG_DIR`
- `DAVINCI_WORKLOAD_CONFIG_DIR`
- `PYTHONPATH`

注意：当前 `simulator_profiles.yml` 中部分 `entry_script` 仍可能是占位路径。Capabilities 查询可以正常使用，但真正启动仿真前必须替换为真实脚本路径。

## 9. Benchmark 当前实现

Benchmark 当前是 V0.1 只读接入，不运行 benchmark，也不落库保存 benchmark result。

核心代码：

```text
backend/app/api/benchmark.py
backend/app/benchmark/registry_reader.py
backend/app/benchmark/service.py
backend/app/benchmark/result_provider.py
```

当前数据来源：

```text
AIBENCH_HOME/
└── registry/
    ├── chip_registry.json
    └── ...
```

当前 API：

- `GET /api/benchmark/status`
- `GET /api/benchmark/chips`
- `GET /api/benchmark/chips/{vendor}/{chip}`
- `GET /api/benchmark/chips/{vendor}/{chip}/benchmarks`
- `GET /api/benchmark/chips/{vendor}/{chip}/benchmarks/{benchmark_name}`
- `GET /api/benchmark/chips/{vendor}/{chip}/benchmarks/{benchmark_name}/results`

当前 result provider 是 `EmptyBenchmarkResultProvider`，会返回空结果列表。未来可以扩展为文件系统或数据库结果提供器。

未来规划：

- Macro 指标展示，例如 latency、throughput、power、memory usage。
- Micro 指标展示，例如 bandwidth、compute、memory latency。
- Benchmark result parser。
- 不同芯片、版本、benchmark 的对比分析。
- Benchmark Trace 分析。

## 10. 前端当前实现

前端入口和路由：

```text
frontend/src/main.tsx
frontend/src/App.tsx
```

主要页面：

- `/`：欢迎页。
- `/login`：开发态登录页。
- `/home`：首页。
- `/simulation/new`：创建仿真任务。
- `/simulation/tasks`：任务列表。
- `/simulation/tasks/:taskId`：任务详情和实时日志。
- `/simulation/tasks/:taskId/result`：仿真结果和 Trace。
- `/performance`：性能分析工作台；支持平台任务和本地 Trace 文件。
- `/benchmark`：Benchmark 芯片浏览。
- `/benchmark/chips/:vendor/:chip`：芯片 Benchmark 页面。
- `/benchmark/chips/:vendor/:chip/benchmarks/:benchmarkName`：Benchmark 详情。

前端 API 封装：

```text
frontend/src/api/client.ts
frontend/src/api/simulation.ts
frontend/src/api/benchmark.ts
```

登录分为普通模式和管理员模式。普通工号识别仍是开发态方案；管理员模式必须验证数据库中的密码哈希。两种模式都使用后端 HttpOnly 会话 Cookie，`localStorage` 只缓存非敏感展示状态；正式 SSO / LDAP 尚未接入。

## 11. Trace 能力

Trace 输入采用 Chrome Trace Format。V1 已确定复用 Catapult/trace2html，Worker 在原始 Trace 生成成功后创建独立 HTML Viewer，前端通过受控 API 在受限 iframe 中展示。Catapult 需要同源存储保存 Viewer 偏好，因此 iframe 允许脚本和同源访问，同时由后端固定产物、CSP `connect-src 'none'` 和路径校验控制安全边界。

当前实现：

```text
trace.json
    ↓
trace2html
    ↓
trace.html
    ↓
前端 iframe 或独立 viewer 展示
```

Viewer 默认使用 Catapult `full` 配置；验证版本固定为 `1d18f6e11082de030c45fd55b556d15e3aa628a8`。`lean` 产物缺少运行时 importer，不能作为可用性基线。结果页支持浏览器原生全屏、`Esc` 退出、新窗口打开和页面级全屏降级。对于尚未回填 `trace.html` 的存量任务，前端仍可使用原 React Viewer 读取原始 Trace。

`catapult_trace2html.py` 在独立 HTML 中注入平台集成桥：Catapult 导入模型期间隐藏其原生黑色 `Importing...` overlay，完成、失败或超时后通过 `postMessage` 通知父页面。前端在收到终态通知前保持平台统一加载遮罩，从而避免 iframe 内部加载窗口闪现。

Catapult 源码位于被 Git 忽略的 `tools/catapult`，不会进入 PR 或 `git archive`。公司离线部署包必须显式携带上述固定 commit 的目录；服务器 `.env` 使用项目内绝对路径。WSL `/mnt/*` 开发环境可使用 Linux 原生文件系统缓存加速，但该本机覆盖配置不得带到服务器。

相关入口：

```text
backend/app/simulation/catapult_trace_exporter.py
backend/scripts/catapult_trace2html.py
backend/scripts/build_trace_viewers.py
frontend/src/components/CatapultTraceViewer.tsx
GET /api/simulation/tasks/{task_id}/trace/viewer
```

复用 Catapult 的原因：

- 支持 lane 展示。
- 支持缩放和搜索。
- 支持事件详情查看。
- 后续更容易扩展多 Trace 对比。

### Trace 时间分析

性能分析算法位于独立顶层包 `analysis_tools/`，不依赖 FastAPI、SQLAlchemy 或平台任务模型。Backend 的 `app/performance/` 只负责权限、任务 Trace 读取、本地上传大小限制和 API 响应转换。

当前支持：

- 平台仿真任务固定按 MSKPP Trace 分析。
- 本地 `trace.json` 由用户选择 MSKPP 或 ESL，Backend 同时校验对应结构。
- 前端 `/performance` 展示 Trace 时间分析，以及 Roofline、Metric、Memory Access Pattern 和 Communication Matrix 的后续能力占位。

相关入口：

```text
analysis_tools/src/chip_performance_analysis/trace_time/
backend/app/api/performance.py
frontend/src/pages/PerformancePage.tsx
GET  /api/performance/tasks/{task_id}/trace-time
POST /api/performance/trace-time
```

## 12. 当前开发状态

已完成或已有代码：

- React + Vite 前端基础框架。
- FastAPI 后端入口和 health API。
- Simulation API 路由。
- Benchmark API 路由。
- SQLAlchemy 任务和上传会话模型。
- 上传会话、任务提交、任务管理、日志读取、结果读取相关服务。
- Worker 轮询、claim、启动仿真进程和更新任务状态的基础框架。
- Simulator Profile 配置读取和 capabilities API。
- Benchmark registry 只读浏览。
- 前端登录、任务创建、任务列表、任务详情、结果页、Benchmark 浏览页面。
- Catapult Trace Viewer 生成、受控读取、iframe 展示和全屏交互。
- Docker PostgreSQL 镜像、external named volume、Alembic 初始迁移和 Linux/WSL 统一生命周期脚本。
- V310 界面样例，以及本地成功任务种子脚本。
- 根级 `runtime/` 任务目录约定、日志/summary/trace API 验证。

进行中或待完善：

- 本地 Mock Capability/Profile 的完整前端提交闭环。
- 真实 Simulator 环境和 profile 路径配置。
- 真实大规模 Trace 的转换耗时和浏览器内存上限验证。
- Benchmark result provider 和真实结果数据链。
- Benchmark compare 和性能回归分析。
- 正式 SSO 认证，以及在现有 Permission Set 第一版基础上的完整 Simulation 所有权、Raw Trace、Audit 和水印体系。

## 13. 开发规范

- 文档统一使用中文 Markdown。
- 大功能建议使用 feature 分支开发，通过 PR 合入 main。
- 代码修改需要同步更新相关文档。
- Simulator 核心代码与平台代码保持解耦。
- 优先复用成熟开源工具。
- 不提交 `tools/`、`runtime/`、`.env`、虚拟环境、`node_modules` 和 Python 缓存。

## 14. 给 AI Agent 的注意事项

- 先读 `docs/AI_CONTEXT.md`、`docs/00_Project/BASELINE_STATUS.md`、`docs/00_Project/ROADMAP.md`，再查看 `backend/app/main.py` 和 `frontend/src/App.tsx`。
- 后端完整启动依赖 `DATABASE_URL`；如果只是阅读代码，不要假设服务可直接启动。
- 启动完整平台优先使用根目录 `scripts/platform.sh`，不要绕过 named volume 挂载检查手工重建 PostgreSQL 容器。
- Benchmark 当前不是完整执行平台，只是 registry read-only 接入。
- 不要把未来规划中的用户表、Benchmark 结果表当作当前已经实现的数据库模型。
- 修改前端时保持 Ant Design 和现有页面风格。
- 修改后端时优先沿用 service / repository / schema 的分层方式。
- 当前 `tools/` 和 `runtime/` 是明确的本地目录，不纳入基线提交。
- “我的任务”按当前登录用户的 `owner_id` 过滤；启动管理员账号为 `admin`，旧 `test-user` 数据由迁移同步重命名。
- 后端数据模型变化必须新增 Alembic migration，不能直接修改已发布 migration。
