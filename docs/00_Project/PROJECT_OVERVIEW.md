# AI Chip Platform — Project Overview

> **Status:** Accepted
> **Version:** V1.0
> **Date:** 2026-08-14

## 1. 项目定位

AI Chip Platform 是一个面向公司内部用户的统一 AI 芯片仿真与 Benchmark 平台。

平台建立在两个已有核心资产之上：

1. **Existing Simulator**
   - 已具备 AI 芯片微架构仿真能力；
   - 支持 Chip Config、Workload 多文件/多目录配置；
   - 支持 Kernel Binary、Input Bin 等依赖文件；
   - 可生成运行日志、Cycle、Result、Trace。

2. **Existing Benchmark Framework**
   - 按 Vendor / Chip 注册 Benchmark；
   - 一个芯片可对应多个不同 Benchmark；
   - Benchmark 包括 MACRO、MICRO、TRACE；
   - Benchmark 可面向 STARS、Cube、HBM、SMMU 等不同 Test Target；
   - Benchmark Framework 和结果资产由现有团队维护。

平台本身不替代 Simulator 和 Benchmark Framework，而是在其上增加：

- Web GUI；
- 统一访问入口；
- 用户与权限；
- 仿真任务提交、排队、运行和结果查看；
- Benchmark 资产浏览；
- Trace 入口；
- Analysis Report；
- 基础 Compare；
- 管理员审计和基础使用统计。

## 2. 核心目标

### 2.1 降低 Simulator 使用门槛

将当前主要依赖命令行、配置目录和服务器环境的仿真过程转化为统一 Web 工作流。

### 2.2 统一 Benchmark 资产入口

将不同芯片、不同 Benchmark、Trace 和研究报告统一组织和展示，减少资产分散。

### 2.3 保护内部敏感信息

对未来芯片、竞争研究、微架构数据和 Raw Trace/Log 进行权限控制、审计和必要水印保护。

### 2.4 建立团队价值数据

通过可靠的访问、Benchmark 查看、仿真任务提交等基础数据，形成团队资产使用情况的客观统计。

## 3. 核心用户

### 普通用户

- 浏览授权范围内的芯片和 Benchmark；
- 查看 Test Result、Trace、Analysis Report；
- 提交和管理自己的仿真任务。

### 高权限用户

在普通用户能力基础上，可访问：

- future_chip；
- competitor；
- micro_arch；
- 其他敏感资产。

### 管理员

- 用户管理；
- 权限审批；
- 查看基础平台统计；
- 查询关键操作审计。

## 4. 系统边界

### Platform 负责

- 登录与权限；
- Web 页面；
- Simulation Task；
- FIFO Queue；
- Task Workspace；
- Simulator Adapter；
- Benchmark Adapter；
- Result 展示协议；
- Trace 入口；
- Analysis Report；
- Audit；
- Admin。

### Existing Simulator 负责

- Chip Config / Workload 业务语义；
- SQ / SQE 等内部配置解析；
- Kernel / Input Bin 使用；
- 仿真执行；
- 真实 Cycle / Result / Trace 产生。

### Existing Benchmark Framework 负责

- Benchmark 注册；
- Benchmark 实现；
- Benchmark 执行；
- Benchmark 原始结果与资产生成。

## 5. V1 总体原则

- 简单优先；
- 复用已有能力；
- 不重复实现 Simulator / Benchmark 已有逻辑；
- 不为了未来扩展提前引入过重基础设施；
- 保持 Adapter 边界，为后续演进留接口。
