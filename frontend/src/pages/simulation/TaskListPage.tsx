import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  Button,
  Card,
  Dropdown,
  message,
  Modal,
  Segmented,
  Space,
  Table,
  Tooltip,
  Typography,
} from 'antd';
import type { TableColumnsType } from 'antd';
import {
  DeleteOutlined,
  EllipsisOutlined,
  EyeOutlined,
  PlusOutlined,
  RedoOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { simulationApi } from '../../api/simulation';
import { PageHeading } from '../../components/PageHeading';
import { TaskStatusTag } from '../../components/StatusTag';
import type {
  SimulationTask,
  SimulationTaskQuotaResponse,
  TaskStatus,
} from '../../types/simulation';
import {
  formatDateTime,
  formatNumber,
  isTerminalStatus,
} from '../../utils/format';

type FilterKey = 'ALL' | 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'ARCHIVED';

function QueueCell({ task }: { task: SimulationTask }) {
  const [ahead, setAhead] = useState<number | null>(null);

  useEffect(() => {
    if (task.status !== 'QUEUED') return;
    simulationApi.getQueue(task.task_id)
      .then((value) => setAhead(value.queued_ahead))
      .catch(() => setAhead(null));
  }, [task.status, task.task_id]);

  if (task.status === 'QUEUED') return <span>前方 {ahead ?? '—'} 个任务</span>;
  if (task.status === 'RUNNING') return <span>Cycle {formatNumber(task.current_cycle)}</span>;
  if (task.total_cycle != null) return <span>{formatNumber(task.total_cycle)} cycles</span>;
  return <span>—</span>;
}

export function TaskListPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const ownerId = user?.userId || import.meta.env.VITE_DEFAULT_OWNER_ID || 'admin';
  const [filter, setFilter] = useState<FilterKey>('ALL');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [items, setItems] = useState<SimulationTask[]>([]);
  const [total, setTotal] = useState(0);
  const [quota, setQuota] = useState<SimulationTaskQuotaResponse | null>(null);
  const [selectedTaskIds, setSelectedTaskIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  const query = useMemo(() => {
    const status = ['QUEUED', 'RUNNING', 'COMPLETED', 'FAILED'].includes(filter)
      ? (filter as TaskStatus)
      : undefined;
    return {
      ownerId,
      status,
      archived: filter === 'ARCHIVED' ? true : false,
      page,
      pageSize,
    };
  }, [filter, ownerId, page, pageSize]);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [response, quotaResponse] = await Promise.all([
        simulationApi.listTasks(query),
        simulationApi.getTaskQuota(ownerId),
      ]);
      setItems(response.items);
      setTotal(response.total);
      setQuota(quotaResponse);
    } catch (error) {
      if (!silent) message.error(error instanceof Error ? error.message : String(error));
    } finally {
      if (!silent) setLoading(false);
    }
  }, [ownerId, query]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(true), 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function deleteTasks(taskIds: string[]) {
    if (!taskIds.length) return;
    setDeleting(true);
    try {
      const response = taskIds.length === 1
        ? await simulationApi.deleteTask(taskIds[0], ownerId)
        : await simulationApi.batchDeleteTasks(ownerId, taskIds);
      message.success(`已删除 ${response.deleted_count} 个任务及其后端运行数据`);
      setSelectedTaskIds((current) => current.filter((id) => !response.deleted_task_ids.includes(id)));
      await load(true);
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setDeleting(false);
    }
  }

  function confirmDelete(taskIds: string[], title: string) {
    Modal.confirm({
      title,
      content: `将同时删除任务记录、配置副本、运行日志、Result 和 Trace，共 ${taskIds.length} 个任务。删除后不可恢复。`,
      okText: '确认删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => deleteTasks(taskIds),
    });
  }

  async function action(
    task: SimulationTask,
    type: 'cancel' | 'terminate' | 'archive' | 'unarchive' | 'rerun' | 'delete',
  ) {
    if (type === 'delete') {
      confirmDelete([task.task_id], `删除任务“${task.task_name}”？`);
      return;
    }

    try {
      if (type === 'cancel') await simulationApi.cancelTask(task.task_id);
      if (type === 'terminate') await simulationApi.terminateTask(task.task_id);
      if (type === 'archive') await simulationApi.archiveTask(task.task_id);
      if (type === 'unarchive') await simulationApi.unarchiveTask(task.task_id);
      if (type === 'rerun') {
        const response = await simulationApi.rerunTask(task.task_id);
        message.success('已创建重跑任务');
        navigate(`/simulation/tasks/${response.task.task_id}`);
        return;
      }
      message.success('操作已提交');
      await load(true);
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    }
  }

  const columns: TableColumnsType<SimulationTask> = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      width: 260,
      render: (_, task) => (
        <div>
          <Typography.Link
            strong
            onClick={() => navigate(`/simulation/tasks/${task.task_id}`)}
          >
            {task.task_name}
          </Typography.Link>
          <div className="table-secondary">{task.task_id}</div>
        </div>
      ),
    },
    {
      title: '版本',
      dataIndex: 'simulator_version',
      width: 110,
      render: (_value: string, task) => task.simulator_label || task.simulator_version.toUpperCase(),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 115,
      render: (value: TaskStatus) => <TaskStatusTag status={value} />,
    },
    {
      title: '提交时间',
      dataIndex: 'submit_time',
      width: 190,
      render: (value: string | null) => formatDateTime(value),
    },
    {
      title: '进度 / 结果',
      width: 190,
      render: (_, task) => <QueueCell task={task} />,
    },
    {
      title: '操作',
      width: 180,
      fixed: 'right',
      render: (_, task) => {
        const menuItems = [
          task.status === 'QUEUED'
            ? { key: 'cancel', label: '取消任务', icon: <DeleteOutlined /> }
            : null,
          task.status === 'RUNNING'
            ? { key: 'terminate', label: '强制终止', icon: <StopOutlined />, danger: true }
            : null,
          isTerminalStatus(task.status)
            ? { key: 'rerun', label: '重新运行', icon: <RedoOutlined /> }
            : null,
          isTerminalStatus(task.status) && !task.archived
            ? { key: 'archive', label: '归档' }
            : null,
          task.archived
            ? { key: 'unarchive', label: '取消归档' }
            : null,
          isTerminalStatus(task.status)
            ? { key: 'delete', label: '删除任务', icon: <DeleteOutlined />, danger: true }
            : null,
        ].filter(Boolean) as { key: string; label: string; icon?: ReactNode; danger?: boolean }[];

        return (
          <Space>
            {task.status === 'COMPLETED' ? (
              <Button
                icon={<EyeOutlined />}
                onClick={() => navigate(`/simulation/tasks/${task.task_id}/result`)}
              >
                查看
              </Button>
            ) : null}
            {menuItems.length ? (
              <Dropdown
                trigger={['click']}
                menu={{
                  items: menuItems,
                  onClick: ({ key }) => {
                    if (key === 'delete') {
                      void action(task, 'delete');
                      return;
                    }
                    const destructive = key === 'cancel' || key === 'terminate';
                    if (destructive) {
                      Modal.confirm({
                        title: key === 'terminate' ? '确认强制终止任务？' : '确认取消任务？',
                        content: task.task_name,
                        okButtonProps: { danger: true },
                        onOk: () => action(task, key as 'cancel' | 'terminate'),
                      });
                    } else {
                      void action(task, key as 'archive' | 'unarchive' | 'rerun');
                    }
                  },
                }}
              >
                <Button icon={<EllipsisOutlined />} />
              </Dropdown>
            ) : null}
          </Space>
        );
      },
    },
  ];

  const quotaFull = quota ? !quota.can_create : false;
  const subtitle = quota
    ? `已保留 ${quota.retained_count} / ${quota.limit} 个任务 · 列表每 5 秒自动刷新`
    : '列表每 5 秒自动刷新';

  return (
    <div className="page-container">
      <PageHeading
        title="我的任务"
        subtitle={subtitle}
        actions={(
          <Tooltip title={quotaFull ? `已达到任务保留上限 ${quota?.limit} 个，请先删除不再需要的任务` : undefined}>
            <span>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                disabled={quotaFull}
                onClick={() => navigate('/simulation/new')}
              >
                新建任务
              </Button>
            </span>
          </Tooltip>
        )}
      />

      <div className="filter-row task-list-toolbar">
        <Segmented<FilterKey>
          value={filter}
          onChange={(value) => {
            setFilter(value);
            setPage(1);
            setSelectedTaskIds([]);
          }}
          options={[
            { label: '全部', value: 'ALL' },
            { label: '排队中', value: 'QUEUED' },
            { label: '运行中', value: 'RUNNING' },
            { label: '已完成', value: 'COMPLETED' },
            { label: '失败', value: 'FAILED' },
            { label: '已归档', value: 'ARCHIVED' },
          ]}
        />

        {selectedTaskIds.length ? (
          <Space>
            <span className="muted-text">已选择 {selectedTaskIds.length} 个</span>
            <Button
              danger
              icon={<DeleteOutlined />}
              loading={deleting}
              onClick={() => confirmDelete(selectedTaskIds, `删除选中的 ${selectedTaskIds.length} 个任务？`)}
            >
              删除所选任务
            </Button>
          </Space>
        ) : null}
      </div>

      <Card className="table-card">
        <Table<SimulationTask>
          className="task-list-table"
          rowKey="task_id"
          loading={loading}
          columns={columns}
          dataSource={items}
          rowSelection={{
            selectedRowKeys: selectedTaskIds,
            onChange: (keys) => setSelectedTaskIds(keys.map(String)),
            getCheckboxProps: (task) => ({
              disabled: !isTerminalStatus(task.status),
              title: isTerminalStatus(task.status) ? undefined : '运行中或排队中的任务不能直接删除',
            }),
          }}
          scroll={{ x: 1120 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (count) => `共 ${count} 个任务`,
            onChange: (nextPage, nextPageSize) => {
              setSelectedTaskIds([]);
              setPage(nextPageSize !== pageSize ? 1 : nextPage);
              setPageSize(nextPageSize);
            },
          }}
        />
      </Card>
    </div>
  );
}
