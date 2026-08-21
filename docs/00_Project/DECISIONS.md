# AI Chip Platform — Decisions

> **Status:** Active
> **Date:** 2026-08-14

本文件记录当前有效的关键产品和架构决策。

## Product Decisions

| ID | 决策 | 原因 | 状态 |
|---|---|---|---|
| P-001 | Benchmark Browse 使用 Vendor 筛选 + Chip Card，不建设独立 Vendor 页面 | 避免没有独立内容的空层级 | Accepted |
| P-002 | Chip Homepage 入口为 MACRO / MICRO / TRACE / Analysis Report | 与真实资产组织方式一致 | Accepted |
| P-003 | Analysis Report 与 Test Report 分离 | Test Report 属于单个 Benchmark；Analysis Report 可综合多个资产 | Accepted |
| P-004 | Analysis Report 为 0 时 Chip Homepage 不显示入口 | 减少无意义空页面 | Accepted |
| P-005 | Analysis Report 即使只有 1 篇也先进入统一列表页 | 保持交互一致，支持后续扩展 | Accepted |
| P-006 | Simulation 输入为 Simulator Version + Chip Config Bundle + Workload Package | Workload 本身可能多 YAML、多目录并包含 Binary | Accepted |
| P-007 | Operator Binary 不作为顶层独立输入 | Kernel/Input Bin 属于 Workload Package 依赖 | Accepted |
| P-008 | V1 不重新解析 SQ/SQE 业务语义 | Simulator 已原生支持 | Accepted |
| P-009 | MACRO / MICRO / TRACE 均使用 Benchmark List → Detail | 一个芯片可注册多个同类型 Benchmark | Accepted |
| P-010 | Benchmark Type 与 Test Target 独立 | STARS/Cube/HBM 是测试对象，不等同于 MICRO/MACRO/TRACE | Accepted |
| P-011 | Benchmark Detail 使用固定外壳 + 动态 Result Block | 避免前端为每个 Benchmark 写专用页面 | Accepted |
| P-012 | V1 不自研完整 Trace Viewer | 优先复用现有成熟 Viewer | Accepted |
| P-013 | Admin V1 不做页面有效停留时间 | Heartbeat 和前后台判断增加复杂度，第一版价值不足 | Accepted |
| P-014 | V1 不自动推断 Simulation Task 属于 STARS/Cube | 缺少可靠标准元数据时不能猜测 | Accepted |

## Architecture Decisions

| ID | 决策 | 原因 | 状态 |
|---|---|---|---|
| A-001 | Platform Backend 使用模块化单体 | V1 简单、开发和部署成本低 | Accepted |
| A-002 | Web Backend 与 Simulation Worker 分离进程，但共享代码仓和模型 | Web 请求不能等待长时间 Simulator | Accepted |
| A-003 | V1 使用数据库实现持久化 FIFO Queue | 当前只需要严格 FIFO，无需复杂 MQ | Accepted |
| A-004 | Simulator 统一通过 Simulator Adapter 接入 | 隔离具体执行命令和未来远程执行方式 | Accepted |
| A-005 | 一个 SimulationTask 对应一个独立 Task Workspace | 隔离任务、方便快照、结果和清理 | Accepted |
| A-006 | Existing Benchmark Registry 继续作为 Benchmark Definition 来源 | 避免维护第二套注册系统 | Accepted |
| A-007 | Benchmark Adapter 将结果转成标准 Result Block | 平台展示统一但不绑死 Benchmark 内容 | Accepted |
| A-008 | Database 保存元数据，大文件使用文件目录存储 | 符合 Config/Binary/Trace/Log 特征 | Accepted |
| A-009 | 业务代码不得绑定服务器 IP、目录和 Simulator 安装路径 | 支持开发机/内网服务器/未来远程节点迁移 | Accepted |
| A-010 | V1 前端轮询 Task 状态，不强制 WebSocket/SSE | 实现简单，实时性足够 | Accepted |
| A-011 | V1 不重复实现 Simulator Workload/SQ/SQE 解析 | 复用现有 Simulator | Accepted |
| A-012 | V1 Trace Timeline 复用现有 Viewer | 减少重复开发 | Accepted |
| A-013 | 本地 PostgreSQL 使用 named volume 保存数据 | 避免容器重建后任务元数据丢失 | Accepted |
| A-014 | 仓库根目录 `runtime/` 保存本地任务文件，Backend 通过 `TASK_ROOT=../runtime` 访问 | 保持运行数据与代码模块同级隔离 | Accepted |
| A-015 | 本地演示任务通过种子脚本生成，不提交日志、Trace 和数据库数据 | 保持仓库轻量且可重复恢复开发状态 | Accepted |
| A-016 | V1 使用 Catapult `trace2html` 的 `full` 配置生成独立 Viewer，由前端受限 iframe 展示 | 本地 Catapult 的 `lean` 产物缺少运行时 importer；`full` 可复用成熟 Lane、缩放、搜索和事件详情能力 | Accepted |
| A-017 | Catapult 固定使用 commit `1d18f6e11082de030c45fd55b556d15e3aa628a8`，通过离线部署包而非 Git PR 分发 | 公司服务器不能直接下载；`tools/` 不进入 Git；固定验证版本避免上游 HEAD 漂移 | Accepted |

## 变更规则

如果某个决策被替代，不删除原记录：

```text
Status: Deprecated
Superseded By: <Decision ID>
```

新决策追加记录。
