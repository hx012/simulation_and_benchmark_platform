# 后续开发路线图

> **Status:** Active
> **Updated:** 2026-08-21

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

1. 决定 Trace Viewer 最终方案：当前 React Viewer 或 Catapult/trace2html。
2. 增加大 Trace 文件的加载策略和上限处理。
3. 完善 summary schema、版本兼容和前端 Result Block。
4. 增加配置快照、日志下载或权限受控查看策略。

## P3：Benchmark 数据闭环

1. 定义 Benchmark Result 目录和 Provider 接口实现。
2. 支持 Metric、Metrics、Table、Series、Trace Result Block。
3. 接入 Test Report 和 Analysis Report。
4. 增加兼容指标的 Compare，最多 4 个对象。

## P4：认证、权限与管理

1. 接入公司 SSO/LDAP，建立后端可信身份。
2. 实现 Permission Set 和敏感资产授权。
3. 增加关键行为 Audit。
4. 实现基础 Admin 指标和权限审批。

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
