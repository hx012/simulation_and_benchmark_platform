# 后续开发路线图

> **Status:** Active
> **Updated:** 2026-08-23

路线图以 `BASELINE_STATUS.md` 为起点。优先完成可验证的小闭环，不同时展开多个大模块。

## P0：基线稳定性

1. 建立统一测试入口，覆盖后端单元测试、PostgreSQL 集成测试和前端构建。
2. 清理历史生成文件，确保 `__pycache__`、`runtime/`、`tools/` 不进入提交。
3. 将已有本地 PostgreSQL 容器迁移到 named volume，并增加挂载验证，避免重建容器后任务元数据丢失。
4. 增加本地 Mock Capability/Profile，使页面可以完成“创建任务 -> Worker -> 完成 -> 结果”的完整流程。
5. 明确开发样例与公司真实 Simulator 配置的边界和替换方式。

## P1：真实 Simulator 适配

1. 在公司 Linux 服务器确认 V310/V320 的真实安装路径、入口脚本和环境变量。
2. 补全并验证 `simulator_profiles.yml`。
3. 用真实 Chip Config / Workload 做端到端任务测试。
4. 固化成功、失败、取消、终止和 Worker 重启恢复测试。
5. 明确 Trace 生成脚本、结果判断和错误码映射。

## P2：结果与 Trace

1. 基于已接入的 Catapult/trace2html 验证真实大 Trace 的转换时间、输出大小和浏览器内存。
2. 根据真实数据调整 Trace 输入、输出和转换超时上限。
3. 完善 summary schema、版本兼容和前端 Result Block。
4. 增加配置快照、日志下载或权限受控查看策略。

## P3：Benchmark 数据闭环

1. 定义 Benchmark Result 目录和 Provider 接口实现。
2. 支持 Metric、Metrics、Table、Series、Trace Result Block。
3. 接入 Test Report 和 Analysis Report。
4. 增加兼容指标的 Compare，最多 4 个对象。

## P4：认证、权限与管理

1. 接入公司 SSO/LDAP，替换当前开发态工号身份并建立后端可信身份。
2. 已完成 Permission Set 第一版：`normal`、`benchmark_access`、`simulation_log`，权限申请审批，以及数据库化模块访问策略。
3. 已完成普通/管理员双入口、管理员密码会话和多管理员配置；后续接入正式 SSO / LDAP 并补充登录风控和审计。
4. 继续收口 Simulation 所有权、Raw Trace 和后续细分资产权限。
4. 增加关键行为 Audit、身份水印和基础 Admin 指标。

## P5：社区共建与性能分析入口

1. 增加环境变量驱动的生态社区入口。
2. 实现意见反馈落库和管理员受保护读取接口。
3. 实现需求提交、可见性控制和配置文件驱动的审视结论。
4. 实现配置文件驱动的团队风采页面。
5. 已实现 `/performance` 性能分析工作台第一版：平台 MSKPP 任务、本地 MSKPP/ESL Trace 上传和 Trace 时间分析。
6. 后续在独立 `analysis_tools` 包中增加 Roofline、Arithmetic / Memory Bandwidth、Memory Access Pattern 和 Communication Matrix。

本期边界、数据可见性以及已规划但暂不开发的功能，统一记录在
[`../01_Product/COMMUNITY_FEATURE_BACKLOG.md`](../01_Product/COMMUNITY_FEATURE_BACKLOG.md)。

## 推荐下一个 PR

建议下一项优先实现“本地 Mock 端到端闭环”：

```text
页面选择 Local Mock
  -> 载入样例
  -> 提交任务
  -> Worker 执行
  -> 任务完成
  -> 查看日志、summary 和 Trace 状态
```

验收标准：全流程不依赖公司 Simulator，且部署到公司服务器时只通过环境变量关闭 Mock 或切换真实 Profile，不修改业务代码。
