# WSL 本地开发启动指南

本文档用于在 Windows + WSL 环境中启动 Ascend Simulator And Benchmark Platform。

Windows 项目目录：

```text
D:\code\chip_simulation\simulation_and_benchmark_platform
```

对应的 WSL 项目目录：

```text
/mnt/d/code/chip_simulation/simulation_and_benchmark_platform
```

本地开发服务包括：

- Docker PostgreSQL 数据库
- FastAPI 后端
- Simulation Worker
- Vite 前端

## 1. 首次初始化

以下操作只需要在首次搭建环境或数据库容器被删除后执行。

### 1.1 进入 WSL

在 PowerShell 或 Windows Terminal 中执行：

```powershell
wsl
```

进入后端目录：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform/backend
```

### 1.2 启动 Docker

检查 Docker 是否可用：

```bash
docker info
```

如果提示无法连接 Docker daemon，执行：

```bash
sudo service docker start
```

### 1.3 构建 PostgreSQL 镜像

```bash
docker build -t ascend-platform-postgres docker/postgres
```

### 1.4 创建 PostgreSQL 容器

```bash
docker volume create ascend-platform-postgres-data
```

```bash
docker run -d \
  --name ascend-platform-postgres \
  -p 15432:5432 \
  -v ascend-platform-postgres-data:/var/lib/postgresql/data \
  -e POSTGRES_USER=ascend_platform \
  -e POSTGRES_PASSWORD=12345678 \
  -e POSTGRES_DB=ascend_platform \
  ascend-platform-postgres
```

数据库连接参数：

| 参数 | 值 |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `15432` |
| Database | `ascend_platform` |
| User | `ascend_platform` |
| Password | `12345678` |

### 1.5 创建统一环境配置

在仓库根目录仅创建一份 `.env.platform`：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform
cp .env.platform.example .env.platform
chmod 600 .env.platform
```

本地数据库配置应为：

```env
TASK_ROOT=../runtime
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=15432
POSTGRES_USER=ascend_platform
POSTGRES_PASSWORD=12345678
POSTGRES_DB=ascend_platform
```

Backend 自动读取根目录 `.env.platform` 并构造数据库连接，不再创建 `backend/.env`。

### 1.6 安装后端依赖并初始化数据库

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform
bash scripts/platform.sh setup
bash scripts/platform.sh update
```

确认数据库迁移状态：

```bash
cd backend
.venv/bin/alembic current
.venv/bin/alembic check
```

## 2. 电脑重启后的日常启动

重启电脑后不需要重新构建镜像或创建数据库。推荐从 WSL 使用与公司 Linux 服务器相同的统一脚本：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform
cp .env.platform.example .env.platform   # 仅首次；随后设置本机数据库密码
bash scripts/platform.sh setup           # 仅首次或依赖变化
bash scripts/platform.sh update          # 依赖校验、迁移、前端构建
bash scripts/platform.sh start dev
bash scripts/platform.sh status
```

首次启动还必须修改 `.env.platform` 中的 `PLATFORM_BOOTSTRAP_ADMIN_PASSWORD`。密码至少 8 位且同时包含字母和数字，示例值不能用于实际环境。

关闭全部服务：

```bash
bash scripts/platform.sh stop
```

日志位于 `runtime/platform/logs/`。下面的分终端命令仅作为手工排障方法保留。

### 2.1 Terminal 1：启动数据库和后端

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform/backend
```

如果 Docker daemon 尚未启动：

```bash
sudo service docker start
```

启动已有 PostgreSQL 容器：

```bash
docker start ascend-platform-postgres
```

确认数据库已经接受连接：

```bash
docker exec ascend-platform-postgres \
  pg_isready -U ascend_platform -d ascend_platform
```

应用最新数据库迁移：

```bash
uv run alembic upgrade head
```

启动 FastAPI：

```bash
uv run uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

访问地址：

- 健康检查：<http://localhost:8000/health>
- API 文档：<http://localhost:8000/docs>

### 2.2 Terminal 2：启动 Simulation Worker

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform/backend
PYTHONPATH=$PWD uv run python worker/simulation_worker.py
```

只查看前端页面时可以不启动 Worker。需要执行 Mock 或真实仿真任务时必须启动 Worker。

### 2.3 Terminal 3：启动前端

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform/frontend
npm run dev -- --host 0.0.0.0
```

首次启动或 `package.json` 发生变化后，先安装依赖：

```bash
npm install
```

必须使用 WSL 内安装的 Linux 版 Node.js。检查：

```bash
command -v node
command -v npm
```

如果 `npm` 指向 `/mnt/c/Program Files/nodejs`，不要继续安装依赖；先在 WSL 安装 Linux 版 Node，再重新安装 `node_modules`。

前端访问地址：<http://localhost:5173>

## 3. 推荐启动顺序

```text
Docker daemon
  -> PostgreSQL 容器
  -> Alembic 数据库迁移
  -> FastAPI 后端
  -> Simulation Worker
  -> Vite 前端
```

## 4. 停止服务

FastAPI、Worker 和前端分别在对应终端中按 `Ctrl+C` 停止。

停止 PostgreSQL 容器：

```bash
docker stop ascend-platform-postgres
```

停止容器不会删除数据库数据。下次使用 `docker start` 即可恢复。

不要执行下面的命令，除非确定需要删除本地数据库：

```bash
docker rm -f ascend-platform-postgres
```

## 5. 常见问题

### 5.1 DATABASE_URL is not configured

确认当前目录是 `backend`，并检查 `.env`：

```bash
pwd
ls -la .env
grep DATABASE_URL .env
```

### 5.2 无法连接 Docker daemon

```bash
sudo service docker start
docker info
```

### 5.3 PostgreSQL 容器未启动

```bash
docker ps -a --filter name=ascend-platform-postgres
docker start ascend-platform-postgres
```

### 5.4 端口 15432 被占用

```bash
ss -ltn 'sport = :15432'
```

停止占用该端口的服务，或者修改容器端口和 `.env` 中的 `DATABASE_URL`。

### 5.5 Worker 找不到 app 模块

确认从 `backend` 目录启动，并设置 `PYTHONPATH`：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform/backend
PYTHONPATH=$PWD uv run python worker/simulation_worker.py
```

### 5.6 数据库容器已被删除

确认 named volume 仍存在：

```bash
docker volume inspect ascend-platform-postgres-data
```

然后重新执行“首次初始化”中的镜像构建、容器创建和 Alembic 数据库迁移步骤。不要创建不挂载 volume 的临时容器，否则历史任务元数据不会恢复。

### 5.7 恢复本地成功任务样例

准备好 Trace 样例文件后执行：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform/backend
uv run python scripts/seed_local_completed_task.py \
  --trace-source /mnt/c/Users/zyp/Downloads/trace_sample.json \
  --owner-id admin
```

脚本会在与 `backend` 同级的 `runtime/` 下生成任务文件，并新增或更新数据库记录。

如果任务已有 `trace.json`，可生成或回填 Catapult Viewer：

```bash
uv run python scripts/build_trace_viewers.py --all --force
```

默认要求仓库根目录存在 `tools/catapult`，当前验证版本固定为 commit `1d18f6e11082de030c45fd55b556d15e3aa628a8`。`tools/` 被 Git 忽略，制作公司服务器离线包时需要显式携带该目录；服务器可在 `.env` 中通过 `CATAPULT_HOME` 和 `CATAPULT_PYTHON` 指向项目内的绝对路径。

如果 WSL 项目位于 `/mnt/*`，Catapult 大量小文件的冷读取可能显著变慢。开发机可把同一 commit 缓存到 WSL 的 Linux 原生文件系统，并仅在本机 `.env` 覆盖 `CATAPULT_HOME`。该缓存路径是本机性能优化，不能复制到公司 Linux 服务器配置。

Viewer HTML 内含平台集成桥，用于隐藏 Catapult 原生黑色 `Importing...` 弹窗，并在加载完成后通知结果页显示 iframe。更新适配脚本后应使用上面的 `--force` 重新生成存量 Viewer。

## 6. 日常快速命令

优先使用：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform
bash scripts/platform.sh start dev
bash scripts/platform.sh logs
bash scripts/platform.sh stop
```

以下命令用于手工排障。

后端终端：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform/backend
sudo service docker start
docker start ascend-platform-postgres
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Worker 终端：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform/backend
PYTHONPATH=$PWD uv run python worker/simulation_worker.py
```

前端终端：

```bash
cd /mnt/d/code/chip_simulation/simulation_and_benchmark_platform/frontend
npm run dev -- --host 0.0.0.0
```
