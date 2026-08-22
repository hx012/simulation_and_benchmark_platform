# Permission Management V1

> **Status:** Implemented
> **Date:** 2026-08-22
> **Scope:** 登录会话、管理员账号、Permission Set、资源访问策略和权限申请审批

## 1. 设计结论

V1 采用 Permission Set，不使用单一的 1/2/3/4 权限等级。原因是 Benchmark、Simulator 日志和后续资产不是天然的单向包含关系，Permission Set 更适合按工作内容独立申请和授权。

认证采用两个明确入口：

- **普通登录**：使用工号进入普通会话；即使该工号是管理员账号，也按普通用户权限运行。
- **管理员登录**：工号必须已配置为管理员，并验证管理员密码；管理员会话默认具备全部启用的 Permission Set。

管理员全权限不改变业务所有权边界。例如 Simulator 日志权限仍只允许查看本人任务；跨用户支持访问应作为单独、可审计的后续权限设计。

## 2. 当前 Permission Set

| Code | 名称 | 默认获得 | 可申请 | 用途 |
|---|---|---:|---:|---|
| `normal` | 平台基础权限 | 是 | 否 | 登录平台和 Simulator 基础功能 |
| `benchmark_access` | Benchmark 访问权限 | 否 | 是 | 浏览芯片、Benchmark 定义和测试结果 |
| `simulation_log` | Simulator 日志访问权限 | 否 | 是 | 查看本人仿真任务日志 |

Permission Set 的名称、说明、启用状态和是否可申请保存在数据库中。`normal` 是系统基础权限，不能停用或改为可申请。

## 3. 受保护资源策略

| Resource Code | 模块 | 默认访问方式 | Permission Set |
|---|---|---|---|
| `simulation.task` | Simulator 任务 | 普通用户 | — |
| `simulation.log` | Simulator 日志 | 指定权限 | `simulation_log` |
| `benchmark.view` | Benchmark | 指定权限 | `benchmark_access` |
| `permission.manage` | 权限管理 | 仅管理员 | — |
| `admin.manage` | 管理员管理 | 仅管理员 | — |

资源支持四种访问方式：

- `normal`：普通会话可访问；
- `permission`：必须具备资源绑定的全部 Permission Set；
- `admin`：仅密码认证后的管理员会话可访问；
- `disabled`：所有会话均不可访问，管理员仍可在权限中心修改配置。

权限中心可以修改模块名称、说明、访问方式和 Permission Set 绑定，不需要修改代码或重启服务。`permission.manage` 和 `admin.manage` 是核心管理资源，固定为仅管理员访问。

## 4. 数据模型

| 表 | 职责 |
|---|---|
| `users` | 工号、显示名称、账号角色、管理员密码哈希和状态 |
| `user_sessions` | 服务端登录会话、普通/管理员模式、过期和撤销状态 |
| `permission_sets` | Permission Set 名称、说明、可申请和启用配置 |
| `user_permission_grants` | 用户获得的 Permission Set |
| `permission_requests` | 用户申请、审批结果和审批人 |
| `protected_resources` | 模块资源及访问方式 |
| `resource_permission_sets` | 资源与 Permission Set 的多对多绑定 |

前端不再通过 `X-Platform-User` 声明身份。登录成功后，Backend 设置 `HttpOnly`、`SameSite=Lax` 的会话 Cookie；数据库只保存随机会话令牌的 SHA-256 摘要。

管理员密码使用带随机盐的 PBKDF2-SHA256 哈希保存，当前规则为至少 8 位且同时包含字母和数字。明文密码只能存在于不提交 Git 的部署环境配置或管理员创建账号时的一次请求中。

## 5. 启动管理员与公司环境部署

每套新环境必须在根目录 `.env.platform` 配置启动管理员：

```env
PLATFORM_BOOTSTRAP_ADMIN_ID=admin
PLATFORM_BOOTSTRAP_ADMIN_PASSWORD=请替换为公司环境初始密码
PLATFORM_SESSION_HOURS=12
PLATFORM_SESSION_COOKIE_SECURE=false
```

要求：

1. 初始密码至少 8 位，同时包含字母和数字；
2. `.env.platform` 不提交 Git，也不要打入交付包；
3. 首次管理员登录时，Backend 将密码哈希写入数据库；
4. 数据库已经存在密码哈希后，修改环境变量不会覆盖管理员密码；
5. HTTPS 部署时将 `PLATFORM_SESSION_COOKIE_SECURE` 设为 `true`。

迁移 `20260822_0003` 会把已有 `test-user` 账号重命名为 `admin`，同步更新 `simulation_tasks.owner_id` 和 `upload_sessions.owner_id`，并保留该用户 UUID 下的权限申请和授权关系。

## 6. 添加其他管理员

管理员以管理员模式登录后，进入“权限中心 → 管理员配置”：

1. 选择已有工号，或输入一个新工号；
2. 将角色设为管理员；
3. 设置至少 8 位、包含字母和数字的初始密码；
4. 将初始密码通过受控渠道交给新管理员；
5. 新管理员登录后可在权限中心修改自己的密码。

系统不允许停用或移除最后一个有效管理员。启动恢复管理员不能通过页面降级或停用；需要更换时先配置新管理员，再修改部署配置。

## 7. 新增模块或 Permission Set

代码负责注册稳定标识并执行校验，数据库负责可变策略：

1. 在 `backend/app/auth/constants.py` 注册新的 Permission Set 或 Resource Code；
2. 新资源使用 `disabled` 作为安全默认值，完成页面和 API 后再由管理员启用；
3. API 使用 `require_resource(<resource code>)` 作为后端安全边界；
4. 前端根据 `/api/auth/me` 返回的可访问资源决定入口和申请提示；
5. 管理员在权限中心配置名称、访问方式和 Permission Set 绑定。

前端隐藏按钮只用于用户体验，不能代替 Backend 的资源检查。

## 8. 当前边界

- 普通工号识别仍是开发态方案，正式部署后应接入公司 SSO / LDAP；
- 当前支持“初始密码 + 管理员自行修改”，尚未强制首次登录修改密码；
- 尚未实现密码失败次数锁定、管理员操作审计和会话管理页面；
- Raw Trace 和跨用户支持访问仍需要单独的权限与审计设计；
- 数据库策略修改对 Backend 立即生效，已登录用户的前端入口在下一次刷新用户信息或刷新页面后同步。

## 9. 验证

自动化脚本 `backend/scripts/test_permissions.py` 覆盖：

- 普通用户默认权限和受限接口；
- 权限申请、管理员审批和授权生效；
- 管理员密码失败与成功登录；
- 管理员模式默认全部 Permission Set；
- 数据库策略改为普通访问后即时生效；
- 管理员账号以普通模式登录时不能调用管理 API。

前端同时通过 TypeScript 检查、生产构建和浏览器交互验证。
