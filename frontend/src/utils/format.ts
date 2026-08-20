import type { ExecutionPhase, TaskStatus, TraceStatus } from '../types/simulation';

const numberFormatter = new Intl.NumberFormat('zh-CN');

export function formatNumber(value: number | null | undefined): string {
  return value == null ? '—' : numberFormatter.format(value);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date);
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return '—';
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 2 : 1)} s`;

  const total = Math.max(0, Math.round(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;

  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
  return `${minutes}m ${secs}s`;
}

export function getElapsedSeconds(startTime: string | null, endTime?: string | null): number | null {
  if (!startTime) return null;
  const start = new Date(startTime).getTime();
  const end = endTime ? new Date(endTime).getTime() : Date.now();
  if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
  return Math.max(0, (end - start) / 1000);
}

export function formatSimulatedTime(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return '—';
  const abs = Math.abs(seconds);
  if (abs === 0) return '0 s';
  if (abs < 1e-9) return `${(seconds * 1e12).toPrecision(6)} ps`;
  if (abs < 1e-6) return `${(seconds * 1e9).toPrecision(6)} ns`;
  if (abs < 1e-3) return `${(seconds * 1e6).toPrecision(6)} μs`;
  if (abs < 1) return `${(seconds * 1e3).toPrecision(6)} ms`;
  return `${seconds.toPrecision(6)} s`;
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

export const taskStatusText: Record<TaskStatus, string> = {
  QUEUED: '排队中',
  RUNNING: '运行中',
  COMPLETED: '已完成',
  FAILED: '失败',
  CANCELLED: '已取消',
  TERMINATED: '已终止',
};

export const executionPhaseText: Record<ExecutionPhase, string> = {
  WAITING: '等待',
  PREPARING: '准备环境',
  STARTING: '启动仿真器',
  EXECUTING: '执行仿真',
  COLLECTING: '收集结果',
  FINISHED: '已结束',
};

export const traceStatusText: Record<TraceStatus, string> = {
  NOT_REQUESTED: '未请求',
  PENDING: '等待生成',
  GENERATING: '生成中',
  READY: '已就绪',
  FAILED: '生成失败',
};

export function isTerminalStatus(status: TaskStatus): boolean {
  return ['COMPLETED', 'FAILED', 'CANCELLED', 'TERMINATED'].includes(status);
}
