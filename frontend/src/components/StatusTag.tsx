import { Tag } from 'antd';
import type { TaskStatus, TraceStatus } from '../types/simulation';
import { taskStatusText, traceStatusText } from '../utils/format';

const taskColors: Record<TaskStatus, string> = {
  QUEUED: 'default',
  RUNNING: 'processing',
  COMPLETED: 'success',
  FAILED: 'error',
  CANCELLED: 'warning',
  TERMINATED: 'volcano',
};

const traceColors: Record<TraceStatus, string> = {
  NOT_REQUESTED: 'default',
  PENDING: 'default',
  GENERATING: 'processing',
  READY: 'success',
  FAILED: 'error',
};

export function TaskStatusTag({ status }: { status: TaskStatus }) {
  return (
    <Tag className="task-status-tag" color={taskColors[status]}>
      {taskStatusText[status]}
    </Tag>
  );
}

export function TraceStatusTag({ status }: { status: TraceStatus }) {
  return (
    <Tag className="trace-status-tag" color={traceColors[status]}>
      {traceStatusText[status]}
    </Tag>
  );
}
