# AI Chip Platform — System Architecture V0.1

> **Status:** Accepted for V1 Design
> **Version:** V0.1
> **Date:** 2026-08-14
> **Scope:** AI 芯片仿真与 Benchmark 内部平台 V1
> **Architecture Principle:** 简单、可落地、边界清晰，不过度设计

> **Implementation Note (2026-08-21):** 本文档保留 V1 目标架构。当前技术栈已经确定为 React + TypeScript + Vite、FastAPI、SQLAlchemy、PostgreSQL 和 Alembic；当前实现状态以 `../00_Project/BASELINE_STATUS.md` 为准。

---

## 1. 文档目的

本文档定义 AI Chip Platform V1 的系统架构基线，包括：

- Frontend、Platform Backend、Simulation Worker、Simulator、Benchmark Framework 的职责边界；
- Platform Backend 的模块划分；
- 仿真任务提交、排队、运行、状态更新和结果收集链路；
- Benchmark Registry 与平台 Benchmark 展示链路；
- 数据库与文件存储的职责；
- V1 部署方式及后续扩展原则。

V0.1 最初用于确定**逻辑架构和模块边界**。当前基础实现已经锁定前后端框架、PostgreSQL 和 Docker 本地开发方式，后续继续遵守本文定义的模块边界。

---

## 2. V1 架构原则

1. **优先简单实现**：第一版只实现当前明确有价值的功能。
2. **模块化单体优先**：Backend 内部按业务模块划分，但不拆微服务。
3. **Simulator 与平台解耦**：通过 Simulator Adapter 隔离 Simulator 的具体启动方式。
4. **复用现有能力**：不重复实现 Simulator 已支持的 Workload 解析、Benchmark Registry、成熟 Trace Viewer 等能力。
5. **大文件走文件系统**：数据库只保存元数据，不保存大型 Config、Binary、Trace、Log。
6. **业务代码不绑定部署环境**：服务器 IP、目录、Simulator 安装路径等均通过配置管理。
7. **V1 默认单机部署，但不把“同机”写死在业务逻辑中。**

---

## 3. 总体架构

```text
                         Browser
                            │
                            ▼
                        Frontend
                            │
                         REST API
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                    Platform Backend                        │
│                                                            │
│  ┌───────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │ Auth &        │  │ Simulation     │  │ Benchmark     │ │
│  │ Permission    │  │ Module         │  │ Module        │ │
│  └───────────────┘  └───────┬────────┘  └──────┬────────┘ │
│                              │                  │          │
│  ┌───────────────┐           │                  │          │
│  │ Report/Asset  │           │                  │          │
│  └───────────────┘           │                  │          │
│                              │                  │          │
│  ┌───────────────┐           │                  │          │
│  │ Audit & Admin │           │                  │          │
│  └───────────────┘           │                  │          │
└──────────────────────────────┼──────────────────┼──────────┘
                               │                  │
                               ▼                  ▼
                       Simulation Worker    Benchmark Adapter
                               │                  │
                               ▼                  ▼
                       Simulator Adapter    Existing Benchmark
                               │             Registry / Assets
                               ▼
                       Existing Simulator

                  Database          File Storage
```

---

## 4. 模块化单体

### 4.1 定义

V1 的 Platform Backend 采用**模块化单体（Modular Monolith）**：

```text
backend/
├── auth/
├── simulation/
├── benchmark/
├── report/
├── audit/
└── admin/
```

各模块职责独立，但：

- 位于同一代码仓；
- 共用统一数据模型和基础设施；
- 模块之间以代码调用为主；
- 不通过 HTTP/RPC 互相调用；
- 作为一个 Backend 应用统一部署。

### 4.2 与微服务的区别

| 维度 | 模块化单体 | 微服务 |
|---|---|---|
| 业务模块 | 分模块 | 分服务 |
| Backend 主体 | 一个应用 | 多个独立服务 |
| 模块通信 | 函数/类调用 | HTTP/RPC/消息 |
| 部署 | 简单 | 较复杂 |
| 数据库 | 通常共享 | 可独立 |
| V1 适用性 | 高 | 暂无必要 |

### 4.3 Backend 与 Worker

模块化单体不代表整个系统只有一个进程。

V1 建议：

```text
platform-backend
platform-worker
```

两个进程：

- `platform-backend`：处理 Web/API 请求；
- `platform-worker`：后台执行长时间 Simulator Task。

二者共享代码仓、数据模型和数据库，不视为两个微服务。

---

## 5. Platform Backend 模块划分

### 5.1 Auth & Permission

负责：

- 用户登录；
- 用户信息；
- Permission Set；
- 权限申请；
- 管理员权限审批；
- 后端资源访问检查。

示例 Permission：

```text
normal
future_chip
competitor
micro_arch
sim_advanced
```

权限安全边界必须位于 Backend。前端隐藏菜单或按钮只用于 UX，不能替代后端权限校验。

### 5.2 Simulation Module

负责 Simulation Task 的业务生命周期。

```text
Simulation
├── Task Service
├── Task Queue
├── Workspace Manager
└── Simulator Adapter Interface
```

Task Service 负责：

- 创建任务；
- 查询任务；
- 修改任务状态；
- Cancel；
- Terminate；
- Rerun；
- Result 查询。

V1 Task 状态：

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
TERMINATED
```

### 5.3 Simulation Worker

Simulation Worker 专门负责后台执行长时间仿真任务：

```text
查询 QUEUED Task
        ↓
FIFO 获取任务
        ↓
调用 Simulator Adapter
        ↓
启动 Simulator
        ↓
更新运行状态 / Cycle
        ↓
收集 Result / Trace
        ↓
更新最终 Task 状态
```

Web API 创建任务后立即返回 Task ID，不等待 Simulator 执行结束。

### 5.4 Simulator Adapter

Simulator Adapter 用于隔离 Platform 与 Simulator 的具体执行方式。

建议抽象能力：

```text
prepare(task)
start(task)
get_status(task)
terminate(task)
collect_result(task)
```

V1 Simulator 可以是本地命令行/trigger 方式。未来如果 Simulator 变成远程服务，只需要替换 Adapter 实现，不要求重写上层业务逻辑。

### 5.5 Benchmark Module

V1 Benchmark 主要为**只读资产展示**，不通过 Web 启动 Benchmark Framework。

职责：

- 读取 Chip / Vendor 信息；
- 读取 Benchmark Registry；
- 获取 Benchmark Definition；
- 获取 Benchmark Result；
- 调用 Benchmark Adapter 转为平台标准结果结构；
- 提供 MACRO / MICRO / TRACE 浏览 API。

### 5.6 Benchmark Adapter

现有 Benchmark Registry 继续作为 Benchmark Definition 的来源。平台不再维护第二套独立 Benchmark 注册系统。

```text
Existing Benchmark Registry
          ↓
Benchmark Adapter
          ↓
BenchmarkDefinition
          ↓
BenchmarkResult
          ↓
Platform Result Block
          ↓
Frontend
```

Benchmark Type 与 Test Target 是两个独立维度：

```text
Benchmark Type:
- MACRO
- MICRO
- TRACE

Test Target:
- STARS
- Cube
- HBM
- SMMU
- System
- ...
```

平台 V1 支持的标准 Result Block 可先收敛为：

```text
Metric
Metrics
Table
Series
Trace
```

Benchmark Framework 决定测试内容，Platform 定义展示协议。

### 5.7 Report / Asset

V1 主要管理：

- Trace Asset；
- Test Report；
- Analysis Report；
- 相关文件元数据。

Analysis Report 推荐采用：

```text
meta.yml
+
report.md
```

V1 不建设 Report CMS、在线编辑器和发布审核工作流。

### 5.8 Audit & Admin

V1 只记录关键业务行为：

```text
LOGIN
VIEW_CHIP
VIEW_BENCHMARK
VIEW_TRACE
VIEW_ANALYSIS_REPORT
SUBMIT_SIM
CANCEL_SIM
TERMINATE_SIM
RERUN_SIM
REQUEST_PERMISSION
GRANT_PERMISSION
REVOKE_PERMISSION
```

不记录普通按钮点击、滚动、筛选操作、页面 Heartbeat 和用户访问路径。

管理员基础统计直接基于：

```text
AuditEvent
+
SimulationTask
```

V1 暂不统计页面有效停留时间。

---

## 6. Simulation Task 输入模型

一次 Simulation Task：

```text
Simulation Task
│
├── Simulator Version
├── Chip Config Bundle
└── Workload Package
```

### 6.1 Chip Config Bundle

允许多文件、多级目录，以及现有 Simulator 支持的 YAML/JSON 等配置格式。

### 6.2 Workload Package

Workload Package 是完整输入目录，而不是单个 `workload_config.yml`。

例如：

```text
chip1_case/
├── top.yml
├── sq0/
│   ├── sq_config.yml
│   ├── sqe0_config.yml
│   └── sqe1_config.yml
├── sq1/
│   ├── sq_config.yml
│   ├── sqe0_config.yml
│   ├── sqe1_config.yml
│   └── sq_top.yml
├── case_bin/
│   └── xxx.cce.o
└── input_data/
    ├── 0/
    └── 1/
```

Workload Package 可以包含：

- Workload Config Bundle；
- Kernel Files；
- Input Binaries；
- 其他 Simulator 所需资源。

### 6.3 V1 平台职责

平台负责：

- 上传目录/ZIP；
- 保留用户目录结构；
- 基础文件合法性检查；
- YAML 基础语法检查；
- 建立 Task Workspace；
- 将整个 Package 交给 Simulator。

V1 不重复实现 Simulator 已支持的 SQ/SQE 业务解析、kernel_file/input_bin 业务校验和参数语义校验。

---

## 7. Task Workspace

每个 SimulationTask 对应一个独立 Workspace。

```text
runtime/
└── SIM-20260814-000001/
    ├── input/
    │   ├── chip_config/
    │   └── workload/
    ├── runtime/
    ├── logs/
    └── result/
```

建议由 `WorkspaceManager` 统一负责：

```text
createTaskWorkspace()
getTaskWorkspace()
cleanupRuntimeFiles()
archiveTask()
```

Task Workspace 的价值：

- 任务之间互不干扰；
- 保存 Config 快照；
- 方便 Rerun；
- 方便 Result/Trace 定位；
- 方便生命周期清理。

---

## 8. Simulation Task 端到端链路

```text
User
 │
 │ Submit
 ▼
Frontend
 │
 │ POST /simulation/tasks
 ▼
Platform Backend
 │
 ├── Auth / Permission Check
 ├── 创建 Task ID
 ├── 保存 Chip Config Bundle
 ├── 保存 Workload Package
 └── status = QUEUED
 │
 ▼
Database
 │
 ▼
Simulation Worker
 │
 │ FIFO 获取 QUEUED Task
 ▼
Simulator Adapter
 │
 ├── 准备 Workspace
 ├── 准备运行参数
 ├── 启动 Simulator
 └── status = RUNNING
 │
 ▼
Existing Simulator
 │
 ├── Cycle
 ├── Log
 ├── Result
 └── Trace
 │
 ▼
Simulator Adapter
 │
 ├── 收集结果
 └── 更新状态
 │
 ▼
COMPLETED / FAILED / TERMINATED
 │
 ▼
Frontend 查询状态和结果
```

---

## 9. Task Queue

V1 仅需要严格 FIFO。

第一版不引入 Kafka、RabbitMQ、Redis Stream 等独立消息队列。

可直接使用数据库中的 `SimulationTask`：

```text
status = QUEUED
ORDER BY submit_time ASC
```

Worker 取最早任务执行。

未来出现多 Worker、多 Simulation Node、任务优先级、高并发或复杂重试后，再考虑独立队列系统。

---

## 10. Cycle 更新

Cycle 更新用于向用户反馈 Simulator 的运行状态，不属于 Simulator 正确执行的必要条件。

```text
Simulator
   ↓
Simulation Worker / Adapter
   ↓
最新 current_cycle
   ↓
Backend
   ↓
Frontend
```

前端 V1 不需要 WebSocket，可以每 3~5 秒轮询：

```text
GET /api/simulation/tasks/{task_id}
```

返回：

```json
{
  "status": "RUNNING",
  "current_cycle": 3821336
}
```

Cycle 不需要每个仿真周期都写入数据库，只需要定期更新最新值。

如果实时获取 Cycle 成本较高，V1 最低能力可以退化为 `RUNNING + Elapsed Time`。

---

## 11. Simulator Log

产品目标要求对 Raw Log 做权限控制。当前基础版本为了开发和问题定位，任务详情页会通过分块 API 展示完整 `davinci_sim.log`；正式接入公司权限体系前必须重新确认此策略。

页面当前提供：

```text
RUNNING
Current Cycle
Incremental Log
COMPLETED
FAILED
```

Raw Log 保存于 Task Workspace。后续接入权限体系时，可增加 Log Processor、脱敏或下载权限控制。

---

## 12. Benchmark 数据链路

```text
Existing Benchmark Framework
            │
            ├── Registry
            ├── Result
            ├── Trace
            └── Test Report
                 │
                 ▼
          Benchmark Adapter
                 │
                 ▼
          Benchmark Service
                 │
                 ▼
               API
                 │
                 ▼
             Frontend
```

Frontend 页面结构：

```text
Benchmark Browse
      ↓
Chip Homepage
      │
      ├── MACRO → Benchmark List → Benchmark Detail
      ├── MICRO → Benchmark List → Benchmark Detail
      ├── TRACE → Benchmark List → Trace Benchmark Detail
      └── Analysis Reports
```

---

## 13. Trace

V1 不重新开发完整 Trace Timeline Viewer。

统一将 Trace 抽象为 `Trace Asset`，来源可能是 Simulation Result 或 Benchmark Result。

平台负责：

- 权限；
- Trace 元数据；
- Trace 入口；
- 水印/审计；
- 后续分析能力。

Timeline 浏览继续复用现有成熟 Trace Viewer。

---

## 14. 数据库与文件存储

### 14.1 Database

数据库保存小型结构化元数据，例如：

```text
User
Permission
SimulationTask
TaskStatus
AuditEvent
AnalysisReport Metadata
Benchmark Index / Cache（如需要）
```

### 14.2 File Storage

服务器文件目录保存大型文件：

```text
Chip Config Bundle
Workload Package
Kernel Binary
Input Binary
Simulator Raw Log
Trace
Benchmark Result File
Analysis Report Markdown
```

V1 不引入对象存储系统。

建议 Root：

```text
/data/ai-chip-platform/
├── simulation_tasks/
├── benchmark/
├── analysis_reports/
└── temp/
```

Database 只记录文件路径和元数据。

---

## 15. V1 部署模型

V1 默认以**单台公司内网 Linux 服务器**作为最简单部署方案：

```text
                   Internal Server
┌───────────────────────────────────────────┐
│ Frontend                                  │
│ Platform Backend                          │
│ Simulation Worker                         │
│          │                                │
│          ▼                                │
│ Existing Simulator                        │
│ Benchmark Assets                          │
│ Database                                  │
│ File Storage                              │
└───────────────────────────────────────────┘
```

开发阶段可以使用：

```text
http://server-ip:3000
```

正式内部使用时可通过内部 DNS + Nginx 暴露：

```text
https://<internal-domain>
```

V1 默认同机部署，但业务逻辑不得依赖同机。

---

## 16. 部署环境隔离

以下信息禁止散落写死在业务代码：

```text
Server IP
Task Root
Simulator Home
Simulator Executable
Benchmark Root
Database URL
```

统一通过配置或环境变量管理，例如：

```text
TASK_ROOT
SIMULATOR_HOME
SIMULATOR_EXECUTABLE
BENCHMARK_ROOT
DATABASE_URL
```

未来可以从 `LocalSimulatorAdapter` 演进到 `RemoteSimulatorAdapter`，而不改变上层 Simulation Service。

---

## 17. V1 管理员统计

V1 只实现成本低、数据可靠的统计。

### Platform

- 今日登录用户；
- 本周 Benchmark 查看次数；
- 本周 Simulation Task 数；
- 待审批权限。

### Benchmark

- MICRO 查看次数；
- MACRO 查看次数；
- TRACE 查看次数；
- Analysis Report 查看次数；
- 热门 Chip / Benchmark。

### Simulation

- Submitted；
- Completed；
- Failed；
- Cancelled / Terminated；
- Success Rate；
- Simulator Version 使用量；
- 平均 Runtime。

V1 暂不实现：

```text
页面有效停留时间
用户访问路径分析
根据 Workload 自动推断 STARS / Cube 任务类型
```

---

## 18. Architecture Decisions

| ID | 决策 |
|---|---|
| A-001 | Platform Backend 采用模块化单体，不拆微服务 |
| A-002 | Web Backend 与 Simulation Worker 分离进程，但共享代码仓和数据模型 |
| A-003 | Simulation Task V1 使用数据库实现持久化 FIFO Queue |
| A-004 | Simulator 统一通过 Simulator Adapter 接入 |
| A-005 | 一个 SimulationTask 对应一个独立 Task Workspace |
| A-006 | Existing Benchmark Registry 继续作为 Benchmark Definition 来源 |
| A-007 | Benchmark Adapter 将不同结果转换为平台标准 Result Block |
| A-008 | Database 保存元数据，大型文件使用服务器文件目录存储 |
| A-009 | 业务逻辑不得依赖具体服务器 IP、目录和 Simulator 安装位置 |
| A-010 | V1 Frontend 使用轮询查询任务运行状态，不强制引入 WebSocket/SSE |
| A-011 | V1 不重新实现 Simulator 已支持的 Workload/SQ/SQE 业务解析 |
| A-012 | V1 Trace Timeline 优先复用现有成熟 Viewer |

---

## 19. 已锁定与待决问题

当前已锁定：

- Frontend 使用 React + TypeScript + Vite + Ant Design；
- Backend 使用 FastAPI；
- Database 使用 PostgreSQL + SQLAlchemy + Alembic；
- 本地开发使用 Docker PostgreSQL；
- Backend 与 Worker 为两个进程，共享数据库和代码。

仍待后续部署约束确认：

以下内容不阻塞 V0.1：

- 正式内部域名；
- Simulator 最终部署在物理机、虚拟机或内部云；
- 多 Simulation Server；
- 独立对象存储；
- 微服务拆分；
- 实时 WebSocket；
- 复杂任务优先级；
- Benchmark Web CMS；
- 自研完整 Trace Viewer。

这些在后续技术设计或真实部署约束明确后再决定。

---

## 20. 下一阶段

Simulation Task 的模型、上传、Workspace、FIFO Worker、进程管理、Cycle、Cancel/Terminate 和 Result/Trace 基础实现已经存在。下一阶段按 `../00_Project/ROADMAP.md` 推进，优先完成本地 Mock 端到端闭环和公司真实 Simulator Profile 验证。
