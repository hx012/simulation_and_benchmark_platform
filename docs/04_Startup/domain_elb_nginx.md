# 域名、ELB 与 Nginx 静态部署

本文记录 `mskpp-aibench.hicomputing.huawei.com` 当前的 HTTP 部署方式、日常发布步骤和服务器迁移边界。HTTPS 尚未配置时，登录 Cookie 必须保持 `Secure=false`；取得证书后应切换到 HTTPS 并设为 `true`。

## 1. 当前访问链路

```text
http://mskpp-aibench.hicomputing.huawei.com
  -> DNS / ELB VIP
  -> ELB 80 监听与防火墙策略
  -> 平台服务器 100.102.199.192:80
  -> Nginx
       /、/assets       -> /var/www/mskpp-aibench
       /api             -> FastAPI 127.0.0.1:8000
       /docs            -> FastAPI Swagger
       /openapi.json    -> FastAPI OpenAPI schema
       /elb-health      -> Nginx 200 OK
```

Nginx直接托管构建后的前端文件，Vite 5173不参与线上请求。平台使用 `static` 模式时只管理PostgreSQL、Backend和Worker，并通过 `/elb-health` 验证Nginx。

## 2. 生产环境变量

服务器的 `.env.platform` 至少包含：

```dotenv
APP_ENV=production
PLATFORM_MODE=static

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

FRONTEND_DEPLOY_DIR=/var/www/mskpp-aibench
NGINX_HEALTH_URL=http://127.0.0.1/elb-health
PLATFORM_PUBLIC_URL=http://mskpp-aibench.hicomputing.huawei.com

PLATFORM_SESSION_COOKIE_SECURE=false
```

真实密码、Simulator路径和其他生产配置不得提交Git。

## 3. 安装Nginx站点

仓库模板位于 `deploy/nginx/mskpp-aibench.conf`，并应与当前生产服务器的生效配置保持同步。它包含ELB健康检查、FastAPI代理、Swagger、Vite哈希资源缓存和React Router回退。Ubuntu服务器执行：

```bash
sudo cp deploy/nginx/mskpp-aibench.conf /etc/nginx/sites-available/mskpp-aibench
sudo ln -s /etc/nginx/sites-available/mskpp-aibench /etc/nginx/sites-enabled/mskpp-aibench
sudo unlink /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

软链接已存在时不要重复创建。修改配置后始终先执行 `sudo nginx -t`。

## 4. 一键构建与发布

服务器代码更新后执行：

```bash
bash scripts/platform.sh deploy-static
```

`deploy-static`自动停止应用、同步依赖、执行数据库迁移、构建前端、发布到`FRONTEND_DEPLOY_DIR`、修正目录/文件权限、检查Nginx配置、启动Backend和Worker，并验证首页、认证配置接口和W3回调入口。

发布命令会拒绝磁盘配置中仍指向`127.0.0.1:18000`的临时W3探针。它先尝试reload Nginx；reload失败时会restart，以释放旧worker和文件描述符并确保新配置真正生效。当前服务器若同时承载其他Nginx站点，执行前应评估这次短暂重启的影响。

普通启停、仅修改`.env.platform`或服务器重启后恢复服务时，不需要重新发布，使用：

```bash
bash scripts/platform.sh restart static
```

浏览器可能缓存入口或哈希资源，发布后应至少验证一次无缓存访问。

## 5. 启停与验证

```bash
bash scripts/platform.sh restart static
bash scripts/platform.sh status
curl -i http://127.0.0.1/elb-health
curl -i http://127.0.0.1/api/platform-config
sudo ss -lntp | grep -E ':(80|8000|5173)\b'
```

预期状态：

```text
mode       static
backend    running
worker     running
frontend   stopped
database   running
```

端口预期为Nginx监听80、FastAPI监听8000、5173无监听。

## 6. 仓库外配置与数据

以下内容不会随Git自动迁移：

| 内容 | 位置或来源 |
|---|---|
| Nginx站点配置 | `/etc/nginx/sites-available/mskpp-aibench` |
| Nginx启用链接 | `/etc/nginx/sites-enabled/mskpp-aibench` |
| 前端静态文件 | `/var/www/mskpp-aibench` |
| 生产环境变量 | `.env.platform` |
| PostgreSQL数据 | Docker named volume |
| 仿真任务及结果 | `TASK_ROOT` |
| Simulator配置和本体 | `SIMULATOR_PROFILES_FILE`、`SIMULATOR_HOME` |
| AiBench、SST、Catapult | 对应外部目录 |
| ELB和防火墙策略 | 公司网络管理平台 |

数据库迁移使用 `pg_dump` 和 `pg_restore`。不要复制正在运行的PostgreSQL数据目录，也不要只迁移数据库而遗漏 `TASK_ROOT`。

## 7. 更换部署服务器

1. 在新服务器准备代码、Python/Node环境、Docker、Nginx、Simulator、AiBench、SST和Catapult。
2. 创建新的 `.env.platform`，恢复数据库及任务目录。
3. 构建并复制前端到 `/var/www/mskpp-aibench`，安装Nginx模板。
4. 执行 `bash scripts/platform.sh deploy-static` 并完成本机健康检查。
5. 申请ELB后端网段到新服务器TCP 80的防火墙策略，旧策略暂不删除。
6. 将新服务器 `IP:80` 加入ELB，先使用低权重灰度验证。
7. 验证页面、登录、API、数据库、Trace和仿真任务后，提高新服务器权重并移除旧服务器。
8. 保留旧服务器一段回退时间，稳定后再下线旧环境。

域名始终指向ELB VIP，迁移服务器时通常只调整ELB后端，用户访问地址不变。

## 8. HTTPS切换

取得覆盖该域名的证书后，在Nginx增加443 TLS站点，并让80只执行HTTP到HTTPS跳转；ELB相应增加443监听。切换完成后必须设置：

```dotenv
PLATFORM_PUBLIC_URL=https://mskpp-aibench.hicomputing.huawei.com
PLATFORM_SESSION_COOKIE_SECURE=true
```

证书、私钥和真实密码不得提交仓库。
