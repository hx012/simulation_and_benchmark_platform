# AI Chip Platform — Product Requirements Document

> **Status:** Accepted
> **Version:** V1.0
> **Date:** 2026-08-14
> **Wireframe Baseline:** V1.0

> 本文档描述产品目标，不代表所有功能已经实现。当前工程能力以 `../00_Project/BASELINE_STATUS.md` 为准。

## 1. 产品结构

```text
AI Chip Platform
├── Home
├── Simulation
│   ├── New Simulation Task
│   ├── My Tasks
│   ├── Running Detail
│   └── Simulation Result
├── Benchmark
│   ├── Benchmark Browse
│   └── Chip Homepage
│       ├── MACRO
│       ├── MICRO
│       ├── TRACE
│       └── Analysis Reports
└── Admin
```

## 2. 首页

### 普通用户

首页包含：

- 平台简介；
- Simulation 主入口；
- Benchmark 主入口；
- 平台资产数量：
  - 芯片数量；
  - Benchmark 数量；
  - Analysis Report 数量；
  - Simulator Version 数量；
- 最近新增 Benchmark；
- 代表性成果。

代表性成果可以同时包含：

- Benchmark；
- Analysis Report。

### 管理员

额外可查看基础平台使用数据。

## 3. Simulation

### 3.1 New Simulation Task

任务输入：

```text
Simulator Version
+
Chip Config Bundle
+
Workload Package
```

#### Chip Config Bundle

支持：

- 多文件；
- 多级目录；
- YAML/JSON；
- 模板选择；
- 上传目录 / ZIP；
- 基础查看/编辑。

#### Workload Package

不是单个 `workload_config.yml`，而是完整目录。

可能包含：

```text
chip1_case/
├── top.yml
├── sq0/
│   ├── sq_config.yml
│   ├── sqe0_config.yml
│   └── ...
├── sq1/
│   └── ...
├── case_bin/
│   └── *.cce.o
└── input_data/
    └── *.bin
```

前端 V1 主要负责：

- 上传；
- 保持目录结构；
- 显示文件树；
- YAML 基础查看/编辑；
- 文件数量/大小；
- 基础语法检查。

Operator Binary 不作为顶层独立输入项。

### 3.2 My Tasks

普通用户只能看到自己的任务。

状态：

- QUEUED；
- RUNNING；
- COMPLETED；
- FAILED；
- CANCELLED；
- TERMINATED。

排队任务显示：

```text
前方还有 N 个任务
```

不显示其他用户身份和任务名称。

### 3.3 Running Detail

显示：

- Task ID；
- Simulator Version；
- RUNNING；
- Current Cycle；
- Elapsed Time；
- 少量安全状态信息；
- Terminate。

不提供 Raw Simulator Log。

### 3.4 Simulation Result

显示：

- Task ID；
- Simulator Version；
- Runtime；
- Total Cycle；
- Result Summary；
- Trace；
- Config Snapshot；
- Archive；
- Rerun。

V1 不做 Simulation Result Compare。

## 4. Benchmark

### 4.1 数据模型

一个 Vendor 下有多个 Chip。

一个 Chip 下可注册多个 Benchmark。

Benchmark 有两个独立维度：

```text
Benchmark Type:
MACRO / MICRO / TRACE

Test Target:
STARS / Cube / HBM / SMMU / System / ...
```

### 4.2 Benchmark Browse

采用：

```text
Vendor Filter
+
Chip Filter/Label
+
Chip Cards
```

不建设独立 Vendor 页面。

### 4.3 Chip Homepage

显示：

- Chip Intro；
- MACRO；
- MICRO；
- TRACE；
- Analysis Report。

如果当前芯片没有 Analysis Report，则整个入口隐藏。

### 4.4 Benchmark List

MACRO / MICRO / TRACE 均采用：

```text
Benchmark List
→ Benchmark Detail
```

List 主要字段：

- Benchmark；
- Target；
- Description；
- Latest Result；
- Version。

支持 Target 筛选。

### 4.5 Benchmark Detail

采用：

> 固定页面外壳 + 动态 Result Block

固定信息：

- Name；
- Type；
- Target；
- Description；
- Module；
- Class；
- Result Version；
- Test Date；
- Status；
- Test Conditions；
- Test Report。

Result Block V1 支持：

- Metric；
- Metrics；
- Table；
- Series；
- Trace。

Benchmark Framework 决定测试内容，Platform 决定标准展示方式。

### 4.6 Trace Benchmark

Trace 也属于 Benchmark Registry。

一个 Chip 可以有多个 Trace Benchmark。

```text
TRACE
→ Trace Benchmark List
→ Trace Benchmark Detail
→ Trace Viewer
```

## 5. Reports

### Test Report

绑定具体 Benchmark / Trace，描述：

- 测试方法；
- 环境；
- 版本；
- 结果。

### Analysis Report

独立研究成果，可综合多个 Benchmark / Trace。

Chip Homepage 有独立 Analysis Report 入口。

页面：

```text
Analysis Report List
→ Analysis Report Detail
```

## 6. Compare

V1 Compare 面向 Benchmark Result。

最多 4 个对象。

仅对语义兼容的 Result Block 进行：

- 差值；
- 比率；
- 百分比变化。

Trace Compare 后续增强。

## 7. 权限

采用 Permission Set，而不是简单线性密级。

示例：

```text
normal
future_chip
competitor
micro_arch
sim_advanced
```

支持：

- 上层默认权限；
- 具体资产覆盖权限。

## 8. 安全

- Backend 强制权限校验；
- 普通用户不获取 Raw Simulator Log；
- 普通用户不下载 Raw Trace；
- 敏感页面增加身份水印；
- 关键访问和操作进入 Audit。

## 9. Admin V1

### 平台概览

- 今日登录用户；
- Benchmark 查看次数；
- Simulation Task 数；
- Simulation Success Rate；
- 待审批权限。

### Benchmark 使用

- MICRO；
- MACRO；
- TRACE；
- Analysis Report；
- 热门 Chip；
- 热门 Benchmark。

### Simulation

- Submitted；
- Completed；
- Failed；
- Cancelled / Terminated；
- Runtime；
- Simulator Version Usage。

### Audit

记录关键行为：

- LOGIN；
- VIEW_CHIP；
- VIEW_BENCHMARK；
- VIEW_TRACE；
- VIEW_ANALYSIS_REPORT；
- SUBMIT_SIM；
- CANCEL_SIM；
- TERMINATE_SIM；
- RERUN_SIM；
- REQUEST_PERMISSION；
- GRANT_PERMISSION；
- REVOKE_PERMISSION。
