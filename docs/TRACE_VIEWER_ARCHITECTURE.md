# Trace Viewer 架构设计

## 1. 目标

平台不自行实现完整时间轴分析工具，而是复用 Chromium Catapult Trace Viewer 能力。

## 2. 当前方案

```text
Simulator
    |
    v
trace.json
    |
    v
Catapult trace2html
    |
    v
trace.html
    |
    v
Frontend iframe
```

## 3. Viewer定位

Catapult负责：

- 时间轴展示
- Lane交互
- Event详情
- 缩放搜索

平台负责：

- Trace文件管理
- 权限控制
- 任务结果关联
- Benchmark对比入口

## 4. 后续扩展

Benchmark阶段支持：

- 多芯片trace对比
- 多版本trace对齐
- 性能瓶颈分析
