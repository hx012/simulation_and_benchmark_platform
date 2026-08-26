# 公司 Linux 服务器启动指南

本文档记录单机 Linux 部署的基础启动方式。根目录 `.env.platform` 是唯一环境配置；真实 Simulator、Benchmark 和 Profile 路径不写入代码。

## 1. 服务组成

- PostgreSQL
- Alembic 数据库迁移
- FastAPI Backend
- Simulation Worker
- Frontend
- Catapult Trace Viewer 工具目录

推荐启动顺序：PostgreSQL -> Alembic -> Backend -> Worker -> Frontend。

## 2. 统一启停脚本

平台以 Linux Bash 脚本作为开发机和工作服务器的统一入口，不依赖 WSL 路径：

```bash
cd /path/to/simulation_and_benchmark_platform
cp .env.platform.example .env.platform
chmod 600 .env.platform
```

配置完成后执行：

```bash
bash scripts/platform.sh setup           # 首次部署或依赖变化
bash scripts/platform.sh update          # 校验依赖、迁移数据库、构建前端
bash scripts/platform.sh deploy-static   # 构建并一键发布到Nginx静态目录
bash scripts/platform.sh start dev       # Uvicorn reload + Vite dev
bash scripts/platform.sh start server    # Uvicorn 常驻 + 已构建前端 preview
bash scripts/platform.sh start static    # Uvicorn 常驻 + Nginx直接托管前端
bash scripts/platform.sh status
bash scripts/platform.sh logs backend
bash scripts/platform.sh restart server
bash scripts/platform.sh stop
```

首次启动前必须在 `.env.platform` 设置启动管理员，不能保留示例密码：

```env
PLATFORM_BOOTSTRAP_ADMIN_ID=admin
PLATFORM_BOOTSTRAP_ADMIN_PASSWORD=至少8位且同时包含字母和数字
PLATFORM_SESSION_HOURS=12
PLATFORM_SESSION_COOKIE_SECURE=true
```

开发环境没有 HTTPS 时可将 `PLATFORM_SESSION_COOKIE_SECURE` 设为 `false`；公司 HTTPS 环境必须使用 `true`。首次管理员登录会将密码哈希写入数据库，后续管理员在权限中心配置。完整说明见 `../03_Architecture/PERMISSION_MANAGEMENT_V1.md`。

`setup` 和 `update` 要求应用进程已经停止；`start` 不安装依赖、不构建前端。脚本负责 PostgreSQL 健康检查、Alembic 迁移、PID/进程组、日志和 HTTP 健康检查。运行状态位于 `runtime/platform/`，不会提交 Git。重复启动不会创建同一服务的第二个实例；端口被外部进程占用时会明确失败。

`static` 模式不要求npm或前端运行时依赖，不启动5173端口，而是检查 `FRONTEND_DEPLOY_DIR/index.html` 和 `NGINX_HEALTH_URL`。服务器代码更新后使用`deploy-static`完成构建、发布、权限修正、Nginx生效检查和端到端健康验证；普通启停仍使用`start/restart static`。当前域名部署见 [domain_elb_nginx.md](domain_elb_nginx.md)。

`stop` 按 Frontend -> Worker -> Backend -> PostgreSQL 顺序停止，只执行容器 stop，不删除容器或 volume。服务器开机启动模板见 `deploy/systemd/`。

## 3. 统一配置

服务器只维护根目录 `.env.platform`，Backend 也直接读取该文件，不再使用 `backend/.env`。数据库连接由 `POSTGRES_*` 自动生成，不重复保存 `DATABASE_URL`：

```dotenv
APP_ENV=production
TASK_ROOT=/data/ai-chip-platform/simulation_tasks
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=15432
POSTGRES_USER=ascend_platform
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_DB=ascend_platform
SIMULATOR_HOME=/path/to/simulator
SIMULATOR_PROFILES_FILE=/path/to/local/config/simulator_profiles.yml
SST_EXECUTABLE=/path/to/sst
AIBENCH_HOME=/path/to/aibench
CATAPULT_HOME=/path/to/simulation_and_benchmark_platform/tools/catapult
CATAPULT_PYTHON=/usr/bin/python3
SIM_TRACE_VIEWER_ENABLED=true
SIM_TRACE_VIEWER_CONFIG=full
```

`SIMULATOR_PROFILES_FILE` 应指向仓库跟踪目录之外的公司真实配置，例如 `deploy/local/config/simulator_profiles.yml`。不要将 `.env.platform` 或 `deploy/local/` 提交到 Git。

离线服务器还需配置：

```dotenv
UV_OFFLINE=true
UV_CACHE_DIR=/absolute/path/to/deploy/offline/python/<bundle>/uv-cache
```

离线包由 `scripts/build-python-offline-cache.sh` 在可联网的 Linux x86_64 Docker 环境生成。脚本同时构建本地 `analysis_tools` 包，将 Hatchling 等构建依赖写入缓存，并在禁网容器中验证本地包可以重新构建和导入。压缩包和校验文件存放在 `deploy/offline/python/`，不提交 Git；`backend/uv.lock` 或 `analysis_tools/pyproject.toml` 变化时需要重新生成和传输。

## 4. PostgreSQL

PostgreSQL 由仓库根目录 `compose.yaml` 管理，数据固定写入外部 named volume：

```text
ascend-platform-postgres-data
```

数据库账号、密码和端口来自不提交 Git 的 `.env.platform`，与 Backend 共用同一组字段：

```env
POSTGRES_USER=ascend_platform
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_DB=ascend_platform
POSTGRES_PORT=15432
```

只管理数据库时可执行：

```bash
bash scripts/platform.sh start-db
bash scripts/platform.sh db-check
bash scripts/platform.sh stop-db
```

如果已有容器使用匿名 volume，脚本会拒绝启动。先阅读 `docs/05_KnownIssues/database_issue.md`，然后执行一次性安全迁移：

```bash
bash scripts/migrate-postgres-volume.sh
```

迁移会生成逻辑备份并保留重命名后的旧容器。该卷声明为 Compose external volume，不属于 Compose 项目生命周期；仍然不要手工删除 `ascend-platform-postgres-data`，除非明确需要清空数据库。

## 5. 数据库迁移

```bash
cd /path/to/simulation_and_benchmark_platform/backend
.venv/bin/alembic upgrade head
.venv/bin/alembic current
```

## 6. Backend

开发或联调：

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务器常驻部署不使用 `--reload`，进程守护方式由公司环境确定：

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

验证：

```text
http://<server-ip>:8000/health
http://<server-ip>:8000/docs
```

## 7. Simulation Worker

新终端进入 `backend`：

```bash
PYTHONPATH=$PWD .venv/bin/python worker/simulation_worker.py
```

真实任务前必须确认：

- `SIMULATOR_HOME` 和 `SST_EXECUTABLE` 正确；
- `SIMULATOR_PROFILES_FILE` 指向的入口脚本配置存在；
- Worker 用户对 `TASK_ROOT` 有读写权限；
- Simulator 运行依赖和环境变量已加载。

## 8. Catapult Trace Viewer

部署包必须包含仓库根目录下的 `tools/catapult`。当前验证版本为：

```text
Source: https://chromium.googlesource.com/catapult
Commit: 1d18f6e11082de030c45fd55b556d15e3aa628a8
Config: full
```

`tools/` 被根级 `.gitignore` 忽略，因此 `git clone`、`git archive` 和 PR 都不会携带 Catapult。离线部署包必须显式加入该目录：

```text
simulation_and_benchmark_platform/
├── backend/
├── frontend/
└── tools/
    └── catapult/
```

不要把开发机的 `.env.platform`、`.venv`、`node_modules`、`runtime` 或 `deploy/local` 打入代码包。服务器上单独维护 `.env.platform`，并将 `CATAPULT_HOME` 指向服务器项目内的绝对路径。WSL 为规避 `/mnt/*` 小文件读取性能问题可能使用 `$HOME/.cache` 副本，这个本机覆盖路径不得复制到公司服务器。

部署后验证：

```bash
test -f "$CATAPULT_HOME/tracing/tracing_build/trace2html.py"
cd /path/to/simulation_and_benchmark_platform/backend
.venv/bin/python scripts/test_catapult_trace_viewer.py
.venv/bin/python scripts/build_trace_viewers.py --all --dry-run
```

平台通过 Python 3 适配入口调用 Catapult，生成 `full` 配置的独立 `trace.html`。生成文件内包含平台集成桥：导入期间隐藏 Catapult 自带的黑色 `Importing...` 弹窗，模型就绪后通过 `postMessage` 通知结果页显示 iframe。已有 `trace.json` 的存量任务升级后需要执行：

```bash
.venv/bin/python scripts/build_trace_viewers.py --all --force
```

## 9. Frontend

```bash
cd /path/to/simulation_and_benchmark_platform/frontend
cp .env.example .env.local
npm ci
npm run build
npm run dev -- --host 0.0.0.0
```

开发服务默认访问：`http://<server-ip>:5173`。

正式部署建议由 Nginx 提供前端静态文件并代理 `/api`。仓库模板位于 `deploy/nginx/mskpp-aibench.conf`，当前域名的安装、发布和迁移步骤见 [domain_elb_nginx.md](domain_elb_nginx.md)。

## 10. 日常检查

```bash
bash scripts/platform.sh status
bash scripts/platform.sh db-check
bash scripts/platform.sh logs worker
test -f "$CATAPULT_HOME/tracing/tracing_build/trace2html.py"
```

数据库记录与任务文件必须同时保留：PostgreSQL 保存任务元数据，`TASK_ROOT` 保存日志、summary 和 Trace。只恢复其中一部分会造成页面和文件系统状态不一致。
