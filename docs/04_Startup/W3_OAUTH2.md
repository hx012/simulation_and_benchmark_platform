# W3 OAuth2 登录部署

## W3 应用配置

当前平台使用 Authorization Code + PKCE（S256）+ `client_secret_post`：

- 回调地址：`http://mskpp-aibench.hicomputing.huawei.com/api/auth/w3/callback`
- Scope：`base.profile`
- 用户字段：`globalUserID`、`uid`、`displayName`

身份映射：

| W3 字段 | 平台用途 |
| --- | --- |
| `globalUserID` | 稳定且唯一的 W3 身份绑定键 |
| `uid` | 员工工号；右上角用户信息显示该字段 |
| `displayName` | 姓名；优先取 `cn=...`，显示在权限中心 |

## 服务器环境变量

在部署主机的 `.env.platform` 设置真实值，绝不能提交 `client_secret`：

```bash
PLATFORM_W3_OAUTH_ENABLED=true
PLATFORM_W3_CLIENT_ID=YOUR_W3_CLIENT_ID
PLATFORM_W3_CLIENT_SECRET=YOUR_W3_CLIENT_SECRET
PLATFORM_W3_REDIRECT_URI=http://mskpp-aibench.hicomputing.huawei.com/api/auth/w3/callback
PLATFORM_W3_SCOPE=base.profile
PLATFORM_SESSION_COOKIE_SECURE=false
```

当前回调为 HTTP，仅适用于已获准的内网试运行。切换 HTTPS 后，必须同时将
`PLATFORM_W3_REDIRECT_URI` 改为 `https://...`，并设定
`PLATFORM_SESSION_COOKIE_SECURE=true`。

## Nginx

正式平台不需要为回调保留临时探针的 `location = /api/auth/w3/callback` 规则。
只要现有 `/api/` 反向代理指向 FastAPI，回调会由 `/api/auth/w3/callback` 路由处理。

## 发布和验证

```bash
bash scripts/platform.sh deploy-static
```

该命令会检查并拒绝残留的`127.0.0.1:18000`临时回调代理，发布前端并修正Nginx读取权限；Nginx reload失败时自动restart，最后确认W3 callback入口不再返回502。

验证步骤：

1. 打开平台登录页，普通用户入口应显示“使用 W3 账号登录”。
2. 完成 W3 授权，应返回原目标页面。
3. 右上角只显示 W3 `uid` 工号。
4. 管理员在权限中心可看到工号与姓名。
5. 普通用户调用本地工号登录接口应被拒绝；管理员本地密码登录仍可使用。
