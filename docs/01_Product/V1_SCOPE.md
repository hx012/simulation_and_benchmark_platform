# AI Chip Platform — V1 Scope

> **Status:** Accepted
> **Version:** V1.0
> **Date:** 2026-08-14

> 本文档定义 V1 目标范围。已实现项和缺口以 `../00_Project/BASELINE_STATUS.md` 为准，开发顺序以 `../00_Project/ROADMAP.md` 为准。

## 1. V1 必须实现

### 1.1 用户与权限

- 工号账号申请；
- 普通权限自动开通；
- 敏感权限申请；
- 管理员审批；
- Permission Set；
- Backend 强制权限校验。

### 1.2 Simulator

- 新建仿真任务；
- 选择 Simulator Version；
- Chip Config Bundle；
- Workload Package；
- 上传目录 / ZIP；
- 保留原始目录结构；
- FIFO Queue；
- 我的任务；
- Queue Position；
- Cancel；
- Terminate；
- Rerun；
- Running 状态；
- Current Cycle（如果现有 Simulator 可低成本获取）；
- Simulation Result；
- Trace 入口；
- Archive；
- 历史任务。

### 1.3 Benchmark

- Vendor / Chip 浏览；
- Chip Homepage；
- MACRO Benchmark List；
- MICRO Benchmark List；
- TRACE Benchmark List；
- Test Target 筛选；
- Benchmark Detail；
- Result Version；
- Test Conditions；
- Test Report；
- Trace Viewer 入口。

### 1.4 Analysis Report

- Chip 级 Analysis Report 入口；
- 有报告才显示；
- 支持一个芯片多篇报告；
- Analysis Report List；
- 单篇 Markdown 报告；
- 可关联多个 Benchmark / Trace。

### 1.5 Compare

- Benchmark Result Compare；
- 最多 4 个对象；
- 只对兼容指标计算差异；
- V1 Compare 临时使用，不保存 Compare Workspace。

### 1.6 Admin

- 用户管理；
- 权限审批；
- 平台概览；
- Benchmark 查看次数；
- Simulation Task 数量；
- Simulator Version 使用量；
- Success Rate；
- 关键行为审计。

## 2. V1 明确不做

### Simulator

- 不解析/重建 SQ、SQE 业务逻辑；
- 不智能解析所有 kernel_file / input_bin 依赖；
- 不自动推断仿真任务属于 STARS / Cube；
- 不做复杂任务优先级；
- 不做多节点调度；
- 不做 Simulator Result Compare。

### Benchmark

- 不做 Benchmark Web CMS；
- 不在线创建/编辑 Benchmark；
- 不重新维护第二套 Benchmark Registry；
- 不把 MACRO/MICRO 写死成固定指标字段；
- 不通过 Web 直接启动 Benchmark Framework。

### Trace

- 不重新开发完整 Timeline Viewer；
- 不开放普通用户 Raw Trace 下载；
- 不做复杂自动 Trace 根因分析。

### Admin / Analytics

- 不做页面有效停留时间 Heartbeat；
- 不做用户访问路径分析；
- 不记录普通点击、滚动、筛选；
- 不做复杂 BI 平台。

### Infrastructure

- 不拆微服务；
- 不引入 Kafka / RabbitMQ；
- 不强制 Redis；
- 不引入对象存储；
- 不要求 Kubernetes；
- 不要求多机部署。

## 3. V1 成功标准

V1 至少完成两条稳定业务闭环：

### Simulation

```text
上传配置
→ 提交任务
→ FIFO 排队
→ Simulator 启动
→ 状态查看
→ 完成
→ Result / Trace
```

### Benchmark

```text
Vendor / Chip
→ Benchmark Type
→ Benchmark List
→ Benchmark Detail
→ Result / Trace / Report
```
