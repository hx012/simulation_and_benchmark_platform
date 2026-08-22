import type { PermissionCode } from './types';

export const permissionCatalog: Record<PermissionCode, { name: string; description: string }> = {
  normal: {
    name: '平台基础权限',
    description: '使用 Simulator 和管理自己的仿真任务。',
  },
  benchmark_access: {
    name: 'Benchmark 访问权限',
    description: '浏览平台中的芯片、Benchmark 定义和测试结果。',
  },
  simulation_log: {
    name: 'Simulator 日志访问权限',
    description: '查看自己仿真任务产生的原始运行日志。',
  },
};
