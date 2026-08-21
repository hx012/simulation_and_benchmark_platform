# 数据库任务持久化问题

> **Status:** Resolved in baseline documentation
> **Resolution:** PostgreSQL 容器必须挂载 named volume `ascend-platform-postgres-data`

## 1. 问题描述
### 现象

电脑重启后，仿真平台页面中的历史任务消失：

页面任务列表为空；
只有重启后重新提交的任务能够显示；
但是 runtime 目录下历史任务数据仍然存在，包括：
任务运行目录；
日志；
仿真结果等。

表现为：

页面：
simulation_tasks
    ↓
只有新任务




文件系统：
runtime/
 ├── task_001
 ├── task_002
 └── task_003

数据库记录和实际运行数据不一致。

## 2. 问题定位

### 数据库检查

查询 PostgreSQL：

select count(*) from simulation_tasks;

结果：

count
-----
1

说明：

历史任务记录已经不在数据库中。

### Docker 检查

当前 PostgreSQL 容器：

docker ps

发现：

ascend-platform-postgres

使用匿名 volume：

bea656fd2fec706bf10ccc3ed79cb07e...

查看：

docker volume inspect bea656fd2fec706bf10ccc3ed79cb07e...

发现：

CreatedAt:
2026-08-21T14:33:43

说明：

当前数据库是重启后重新创建的新数据库。

找到历史数据库 Volume

查看：

docker volume ls

发现：

ascend-platform-postgres-data

创建时间：

2026-08-15T17:45:26

该 volume 是之前运行平台时使用的数据库。

## 3. 根因分析

启动 PostgreSQL 时使用：

docker run -d \
 --name ascend-platform-postgres \
 -p 15432:5432 \
 -e POSTGRES_USER=ascend_platform \
 -e POSTGRES_PASSWORD=12345678 \
 -e POSTGRES_DB=ascend_platform \
 ascend-platform-postgres

没有指定数据卷：

-v xxx:/var/lib/postgresql/data

导致：

Docker 自动创建匿名 volume：

container
    |
    ↓
anonymous volume
    |
    ↓
数据库数据

当容器删除并重新创建：

旧container
    |
    ↓
旧volume
    |
    ↓
历史任务

变成：

新container
    |
    ↓
新anonymous volume
    |
    ↓
空数据库

因此：

runtime文件仍存在；
PostgreSQL任务表为空；
页面无法展示历史任务。

## 4. 基线解决方案

创建容器时显式挂载 named volume：

```bash
docker volume create ascend-platform-postgres-data

docker run -d \
  --name ascend-platform-postgres \
  -p 15432:5432 \
  -v ascend-platform-postgres-data:/var/lib/postgresql/data \
  -e POSTGRES_USER=ascend_platform \
  -e POSTGRES_PASSWORD=12345678 \
  -e POSTGRES_DB=ascend_platform \
  ascend-platform-postgres
```

验证挂载：

```bash
docker inspect ascend-platform-postgres \
  --format '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{end}}'
```

数据库迁移仍需执行：

```bash
cd backend
uv run alembic upgrade head
```

注意：PostgreSQL 保存任务元数据，仓库根目录 `runtime/` 保存任务文件。两者都需要备份和恢复。

## 5. 恢复历史任务

如果历史 named volume 仍存在，应优先用原 volume 重建容器。只有 `runtime/` 而没有数据库记录时，页面无法自动恢复任务；需要从备份恢复数据库，或使用明确的迁移/重建脚本补回元数据。
