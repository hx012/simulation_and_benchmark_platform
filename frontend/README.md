# Ascend Simulator & Benchmark Platform Frontend V1.1

技术栈：React + TypeScript + Vite + Ant Design。

V1.1 重点：

- 统一视觉与分组式左侧导航。
- V310 Chip Variant 显示“默认”。
- 支持把 V310 样例复制到当前 UploadSession。
- Chip Config / Workload 使用树状文件结构。
- YAML / JSON 在线只针对当前任务副本编辑；二进制文件只读。
- 重新上传整个 Package 时替换旧目录。
- 明确静态校验范围。
- 运行详情 Runtime 使用 Worker 回写的权威 runtime_seconds。
- 仿真结果页直接加载并渲染 Trace。

## 启动

```bash
cp .env.example .env.local
npm install
npm run build
npm run dev
```

开发模式 Vite 将 `/api` 代理到 `http://127.0.0.1:8000`。

## Backend V1.1 依赖

除 V1 已有接口外，V1.1 使用：

```text
POST /api/simulation/upload-sessions/{id}/apply-sample
GET  /api/simulation/upload-sessions/{id}/files
GET  /api/simulation/upload-sessions/{id}/files/content
PUT  /api/simulation/upload-sessions/{id}/files/content
GET  /api/simulation/tasks/{task_id}/trace
GET  /api/simulation/tasks/{task_id}/trace/viewer
```

仓库已经在 `backend/config/simulation_templates/default/` 下按 `single_chip` 和 `multi_chip` 提供统一界面样例，所有 Simulator Version 与 Chip Variant 共用。需要替换真实输入时，使用 Backend 的 `scripts/seed_simulation_sample.py` 按 Simulation Mode 安装。

WSL 开发必须使用 Linux 版 Node.js。`command -v node` 和 `command -v npm` 不应指向 `/mnt/c/Program Files/nodejs`。
