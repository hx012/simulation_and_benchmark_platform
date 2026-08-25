# AI Chip Platform 文档导航

> 当前工程基线：2026-08-22
> 产品目标：V1
> 工程状态：基础版本已可在 WSL 本地运行，后续通过 PR 迭代

## 新会话阅读顺序

新 AI 会话或新开发者只需先读以下三份文档即可开始工作：

1. [AI_CONTEXT.md](AI_CONTEXT.md)：项目地图、代码入口、核心约束。
2. [BASELINE_STATUS.md](00_Project/BASELINE_STATUS.md)：当前已实现能力、验证状态、已知边界。
3. [ROADMAP.md](00_Project/ROADMAP.md)：下一阶段优先级和推荐任务。

需要运行项目时再读 [wsl_startup.md](04_Startup/wsl_startup.md)；生产域名部署读 [domain_elb_nginx.md](04_Startup/domain_elb_nginx.md)；需要修改代码时读 [DEVELOPMENT_GUIDE.md](06_Development/DEVELOPMENT_GUIDE.md)。

## 文档目录

```text
docs/
├── README.md
├── AI_CONTEXT.md
├── 00_Project/
│   ├── PROJECT_OVERVIEW.md
│   ├── BASELINE_STATUS.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md
│   └── CHANGELOG.md
├── 01_Product/
│   ├── PRD.md
│   └── V1_SCOPE.md
├── 02_UX/
│   └── wireframe/wireframe_v1.0.html
├── 03_Architecture/
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── BENCHMARK_BACKEND_V0_1.md
│   └── PERMISSION_MANAGEMENT_V1.md
├── 04_Startup/
│   ├── startup.md
│   ├── domain_elb_nginx.md
│   └── wsl_startup.md
├── 05_KnownIssues/
└── 06_Development/
    └── DEVELOPMENT_GUIDE.md
```

## Source of Truth 优先级

当文档存在冲突时，按以下顺序判断：

1. 当前代码、数据库迁移和自动化验证结果。
2. `BASELINE_STATUS.md` 和 `AI_CONTEXT.md` 中的当前实现说明。
3. `DECISIONS.md` 中已接受且未废弃的决策。
4. `PRD.md`、`V1_SCOPE.md` 和 `SYSTEM_ARCHITECTURE.md` 中的目标设计。
5. Wireframe 和历史问题记录。

产品目标不等于当前已经实现。新增功能前必须先确认 `BASELINE_STATUS.md`。

## 文档维护规则

每个影响行为的 PR 至少检查：

1. 当前实现是否需要更新 `BASELINE_STATUS.md`。
2. 后续优先级是否需要更新 `ROADMAP.md`。
3. 架构选择是否需要追加到 `DECISIONS.md`。
4. 启动命令或环境变量是否需要更新 `04_Startup/`。
5. 用户可见行为是否影响 `PRD.md` 或 `V1_SCOPE.md`。
6. 是否需要在 `CHANGELOG.md` 记录基线变化。

不要覆盖已经冻结的 Wireframe 历史版本；需要调整时创建新版本。
