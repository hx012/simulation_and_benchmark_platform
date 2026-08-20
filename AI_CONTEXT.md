# AI芯片仿真与Benchmark平台 - AI_CONTEXT

## 1. 项目定位

本项目用于构建统一的 AI 芯片仿真与 Benchmark 平台。

核心目标：

- 提供 Web 化仿真任务管理能力。
- 支持不同 Simulator Version、Chip Variant、Simulation Mode 的统一配置与运行。
- 管理仿真任务生命周期，包括创建、执行、结果收集和展示。
- 支持 Benchmark 数据管理以及后续性能分析和 Trace 对比。

## 2. 当前仓库结构

当前仓库主要包含前端和后端两部分：

```
simulation_and_benchmark_platform/
├── backend/
├── frontend/
└── README.md
```

## 3. 后端架构

后端位于：

```
backend/
```

主要目录：

|目录|职责|
|-|-|
|app|后端应用核心代码|
|config|平台配置文件|
|worker|后台任务执行相关逻辑|
|scripts|辅助脚本|

当前后端主要负责：

- Simulation 任务管理。
- Simulator 配置解析。
- 仿真任务执行调度。
- Runtime 环境管理。
- 结果和日志收集。

## 4. 前端架构

前端位于：

```
frontend/
```

技术栈：

- TypeScript
- Vite
- Web 前端组件化开发

主要职责：

- 用户登录和身份标识。
- Simulation 配置页面。
- 任务列表和任务详情展示。
- 仿真结果展示。
- Benchmark 展示。

## 5. Simulation 功能

Simulation 模块目标是支持统一管理多种芯片仿真能力。

当前设计支持：

```
Simulator Version
        |
        Chip Variant
                |
                Simulation Mode
```

配置入口：

```
backend/config/simulator_profiles.yml
```

配置用于描述：

- Simulator 启动信息。
- 芯片版本。
- 仿真模式。
- 运行参数。

## 6. 仿真运行流程

基本流程：

```
用户提交任务
      ↓
Backend创建Job
      ↓
准备Runtime环境
      ↓
启动Simulator
      ↓
收集日志和结果
      ↓
Result页面展示
```

每个任务应保持独立运行环境，避免不同任务之间文件冲突。

## 7. Trace能力

Trace 用于展示芯片微架构执行过程。

当前方向：

- 使用 Chrome Trace Format。
- 使用 Catapult trace viewer 进行展示。
- 避免重复开发自定义时间线组件。

未来支持：

- 多 Trace 对比。
- Benchmark Trace 分析。
- 性能瓶颈定位。

## 8. Benchmark功能规划

Benchmark 模块用于管理芯片性能数据。

规划支持：

- Macro 指标展示。
- Micro 指标展示。
- Trace 对比分析。
- 不同芯片和版本之间的性能比较。

## 9. 当前开发状态

已完成：

- 基础 Web 平台框架。
- 前后端分离架构。
- Simulation任务管理基础能力。
- Simulator Profile 配置框架。
- 多级 Simulator 配置选择。
- Trace生成和Catapult验证。

进行中：

- 仿真结果页面完善。
- Trace Viewer 集成。
- Benchmark 数据链建设。

## 10. 开发规范

1. 文档统一使用中文 Markdown。
2. 大功能使用 feature 分支开发，通过 PR 合入 main。
3. 代码修改需要同步更新相关文档。
4. Simulator 核心代码与平台代码保持解耦。
5. 优先复用成熟开源工具。

## 11. 后续规划

- 完善 Trace Viewer。
- Benchmark Compare。
- 性能回归分析。
- AI Agent辅助开发流程。
- 建立持续维护的项目知识库。
