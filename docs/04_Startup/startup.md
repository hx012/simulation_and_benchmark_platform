# 公司 Linux 服务器启动指南

本文档记录单机 Linux 部署的基础启动方式。真实 Simulator 和 Benchmark 路径必须通过服务器 `.env` 和 Profile 配置，不写入代码。

## 1. 服务组成

- PostgreSQL
- Alembic 数据库迁移
- FastAPI Backend
- Simulation Worker
- Frontend

推荐启动顺序：PostgreSQL -> Alembic -> Backend -> Worker -> Frontend。

## 2. 后端配置

进入仓库 `backend` 目录：

```bash
cd /path/to/simulation_and_benchmark_platform/backend
cp .env.example .env
```

根据公司服务器修改 `.env`：

```env
APP_ENV=production
TASK_ROOT=/data/ai-chip-platform/simulation_tasks
DATABASE_URL=postgresql+psycopg://ascend_platform:CHANGE_ME@127.0.0.1:15432/ascend_platform
SIMULATOR_HOME=/path/to/simulator
SST_EXECUTABLE=/path/to/sst
AIBENCH_HOME=/path/to/aibench
```

不要将服务器 `.env` 提交到 Git。

## 3. PostgreSQL

构建镜像：

```bash
docker build -t ascend-platform-postgres docker/postgres
```

创建 named volume：

```bash
docker volume create ascend-platform-postgres-data
```

首次创建容器：

```bash
docker run -d \
  --name ascend-platform-postgres \
  --restart unless-stopped \
  -p 15432:5432 \
  -v ascend-platform-postgres-data:/var/lib/postgresql/data \
  -e POSTGRES_USER=ascend_platform \
  -e POSTGRES_PASSWORD=CHANGE_ME \
  -e POSTGRES_DB=ascend_platform \
  ascend-platform-postgres
```

后续启动已有容器：

```bash
docker start ascend-platform-postgres
docker exec ascend-platform-postgres \
  pg_isready -U ascend_platform -d ascend_platform
```

删除容器前必须确认 named volume 已存在。不要删除 `ascend-platform-postgres-data`，除非明确需要清空数据库。

## 4. 数据库迁移

```bash
cd /path/to/simulation_and_benchmark_platform/backend
uv sync --frozen
uv run alembic upgrade head
uv run alembic current
```

## 5. Backend

开发或联调：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务器常驻部署不使用 `--reload`，进程守护方式由公司环境确定：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

验证：

```text
http://<server-ip>:8000/health
http://<server-ip>:8000/docs
```

## 6. Simulation Worker

新终端进入 `backend`：

```bash
PYTHONPATH=$PWD uv run python worker/simulation_worker.py
```

真实任务前必须确认：

- `SIMULATOR_HOME` 和 `SST_EXECUTABLE` 正确；
- `config/simulator_profiles.yml` 的入口脚本存在；
- Worker 用户对 `TASK_ROOT` 有读写权限；
- Simulator 运行依赖和环境变量已加载。

## 7. Frontend

```bash
cd /path/to/simulation_and_benchmark_platform/frontend
cp .env.example .env.local
npm ci
npm run build
npm run dev -- --host 0.0.0.0
```

开发服务默认访问：`http://<server-ip>:5173`。

正式部署建议由 Nginx 提供前端静态文件并代理 `/api`，具体配置在公司部署方案确定后补充。

## 8. 日常检查

```bash
docker ps --filter name=ascend-platform-postgres
uv run alembic current
curl http://127.0.0.1:8000/health
```

数据库记录与任务文件必须同时保留：PostgreSQL 保存任务元数据，`TASK_ROOT` 保存日志、summary 和 Trace。只恢复其中一部分会造成页面和文件系统状态不一致。
