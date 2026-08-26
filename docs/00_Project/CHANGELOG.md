# AI Chip Platform — Changelog

## 2026-08-25 — Nginx static production mode

### Added

- `platform.sh` 新增 `static` 模式，由Nginx托管已发布前端且不启动Vite 5173；
- `platform.sh` 新增 `deploy-static`，自动构建、发布、修正静态文件权限、检查Nginx并执行端到端健康验证；
- 新增Nginx站点模板以及域名、ELB、静态发布和服务器迁移文档；
- systemd示例改为从 `.env.platform` 读取启动模式。

### Deployment

- 服务器代码更新后使用 `platform.sh deploy-static` 一键发布，普通启停继续使用 `start/restart static`；
- 当前HTTP部署继续使用非Secure会话Cookie，取得证书并启用HTTPS后必须切换为Secure。

## 2026-08-23 — Community Collaboration V1

### Changed

- 数据库迁移脚本目录由 `backend/alembic/` 统一调整为 `backend/migrations/`，命令行仍使用 Alembic。

### Added

- 新增生态社区配置入口，社区地址由 `.env.platform` 管理；
- 新增意见反馈落库和管理员受保护读取接口；
- 新增需求池、需求提交、支持投票和“公开需求 + 我的需求”可见性规则；
- 新增配置文件驱动的需求审视结论和团队风采内容；
- 新增 `/performance` 功能建设中页面；
- 新增社区共建功能范围与后续规划文档。

### Deferred

- 反馈附件、“我的反馈”和管理员反馈管理页面；
- Web 端需求审视、评论、通知、附件和排期管理；
- 团队内容管理界面和完整性能分析能力。

## 2026-08-23 — Offline uv deployment and one-command startup

### Changed

- 根目录 `.env.platform` 成为数据库、Backend、Worker 和管理员的唯一环境配置；
- Backend 根据 `POSTGRES_*` 自动构造数据库连接，不再重复维护 `DATABASE_URL`；
- 公司真实 `simulator_profiles.yml` 可通过 `SIMULATOR_PROFILES_FILE` 放在仓库外；
- `scripts/platform.sh` 拆分 `setup`、`update` 和 `start`，运行时直接使用 `.venv/bin/*`；
- 增加 Linux x86_64 / Python 3.10 uv 离线缓存构建和断网验证脚本。

## 2026-08-22 — Permission Management V1

### Added

- 普通/管理员双入口和后端 HttpOnly 会话；
- 多管理员数据库配置、管理员密码哈希和自助改密；
- `normal`、`benchmark_access`、`simulation_log` Permission Set；
- 权限申请、审批、授权闭环；
- 数据库化模块访问策略和权限中心配置界面。

### Migration

- `20260822_0002` 创建用户、授权和权限申请表；
- `20260822_0003` 创建会话、Permission Set 和受保护资源表，并将 `test-user` 迁移为 `admin`。

### Known Gaps

- 普通工号识别仍待公司 SSO / LDAP；
- 首次登录强制改密、失败锁定和管理员审计尚未实现；
- Raw Trace 和跨用户支持访问仍需独立权限设计。

## 2026-08-21 — Engineering Baseline B0

形成可继续迭代的本地开发基础版本。

### Added

- FastAPI 应用入口、PostgreSQL Docker 镜像和 Alembic 初始迁移；
- WSL 本地开发启动流程；
- V310/default/single_chip 界面样例；
- 本地成功任务种子脚本；
- `BASELINE_STATUS.md`、`ROADMAP.md` 和开发接手指南。

### Confirmed

- Simulation 任务列表、详情、日志、summary 和 Trace 基础链路；
- Benchmark Registry 只读边界；
- 根级 `runtime/` 文件布局；
- 后续开发以当前代码为基线，通过 PR 演进。

### Known Gaps

- 本地 Mock 尚未形成页面提交到 Worker 的完整闭环；
- 真实 Simulator Profile 需要在公司 Linux 环境验证；
- Benchmark Result、正式认证权限、Admin 和 Compare 尚未完成。

## 2026-08-14 — Docs Baseline V1.0

建立第一套正式 Source of Truth 文档。

### Added

- `PROJECT_OVERVIEW.md`
- `PRD.md`
- `V1_SCOPE.md`
- `DECISIONS.md`
- `SYSTEM_ARCHITECTURE.md`
- `wireframe_v1.0.html`

### Product Baseline

- Wireframe V0.6 冻结为 V1.0 基线；
- Simulation 输入统一为 Chip Config Bundle + Workload Package；
- Benchmark 使用 Registry 驱动；
- MACRO / MICRO / TRACE 使用 Benchmark List → Detail；
- Analysis Report 独立于 Test Report；
- Admin V1 采用简化统计方案。

### Architecture Baseline

- 模块化单体 Backend；
- 独立 Simulation Worker；
- 数据库 FIFO Queue；
- Simulator Adapter；
- Task Workspace；
- Benchmark Adapter；
- Database + File Storage；
- Frontend Polling。

## Earlier Exploration

### Wireframe V0.1

形成第一版统一平台页面草图。

### Wireframe V0.2–V0.4

逐步明确：

- Config Bundle；
- Benchmark 两级导航；
- Trace Viewer 复用；
- Analysis Report。

### Wireframe V0.5

引入：

- Workload Package；
- Benchmark Registry；
- Benchmark List；
- Benchmark Detail；
- Benchmark Type / Test Target。

### Wireframe V0.6

简化 Admin V1：

- 去除页面停留时间；
- 去除用户路径分析；
- 去除 Simulation STARS/Cube 自动分类。
