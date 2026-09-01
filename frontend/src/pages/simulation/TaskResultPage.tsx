import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Collapse,
  Descriptions,
  message,
  Modal,
  Space,
  Spin,
} from 'antd';
import { InboxOutlined, ArrowLeftOutlined, RedoOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { simulationApi } from '../../api/simulation';
import { trackAnalyticsEventQuietly } from '../../api/analytics';
import { MetricCard } from '../../components/MetricCard';
import { PageHeading } from '../../components/PageHeading';
import { TaskStatusTag, TraceStatusTag } from '../../components/StatusTag';
import { TraceViewer } from '../../components/TraceViewer';
import { CatapultTraceViewer } from '../../components/CatapultTraceViewer';
import { useAuth } from '../../auth/AuthContext';
import type {
  SimulationResultResponse,
  SimulationTask,
  SimulationTraceResponse,
} from '../../types/simulation';
import {
  formatDateTime,
  formatDuration,
  formatNumber,
  formatSimulatedTime,
  isTerminalStatus,
} from '../../utils/format';

export function TaskResultPage() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [task, setTask] = useState<SimulationTask | null>(null);
  const [result, setResult] = useState<SimulationResultResponse | null>(null);
  const [trace, setTrace] = useState<SimulationTraceResponse | null>(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!taskId) return;
    setLoading(true);
    try {
      const [taskData, resultData] = await Promise.all([
        simulationApi.getTask(taskId),
        simulationApi.getResult(taskId),
      ]);
      setTask(taskData);
      setResult(resultData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!task) return;
    trackAnalyticsEventQuietly({
      event_name: 'simulation.result_view',
      page_key: 'simulation.task_result',
      simulator_version: task.simulator_version,
      chip_variant: task.chip_variant,
      simulation_mode: task.simulation_mode,
      target_type: 'simulation_task',
      target_id: task.task_id,
      target_name: task.task_name,
    });
  }, [task?.task_id]);

  useEffect(() => {
    const sourceAvailable = result?.trace_source_available ?? result?.trace_available;
    if (
      !taskId
      || !sourceAvailable
      || result?.trace_viewer_available
      || result?.trace_status !== 'READY'
    ) {
      setTrace(null);
      setTraceLoading(false);
      setTraceError(null);
      return;
    }
    let cancelled = false;
    setTraceLoading(true);
    setTraceError(null);
    simulationApi.getTrace(taskId)
      .then((data) => {
        if (!cancelled) setTrace(data);
      })
      .catch((err) => {
        if (!cancelled) setTraceError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setTraceLoading(false);
      });
    return () => { cancelled = true; };
  }, [
    taskId,
    result?.trace_available,
    result?.trace_source_available,
    result?.trace_status,
    result?.trace_viewer_available,
  ]);

  async function archiveToggle() {
    if (!task) return;
    try {
      if (task.archived) await simulationApi.unarchiveTask(task.task_id);
      else await simulationApi.archiveTask(task.task_id);
      message.success(task.archived ? '已取消归档' : '已归档');
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    }
  }

  async function rerun() {
    if (!task) return;
    try {
      const response = await simulationApi.rerunTask(task.task_id);
      trackAnalyticsEventQuietly({
        event_name: 'simulation.task_rerun',
        page_key: 'simulation.task_result',
        result: 'success',
        simulator_version: task.simulator_version,
        chip_variant: task.chip_variant,
        simulation_mode: task.simulation_mode,
        target_type: 'simulation_task',
        target_id: response.task.task_id,
        target_name: response.task.task_name,
      });
      message.success('已复用原输入创建新任务');
      navigate(`/simulation/tasks/${response.task.task_id}`);
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    }
  }

  if (loading) return <div className="center-state"><Spin size="large" /></div>;
  if (error || !task || !result) {
    return <div className="page-container"><Alert type="error" showIcon title="结果读取失败" description={error || 'Result unavailable'} /></div>;
  }

  if (!isTerminalStatus(task.status)) {
    return (
      <div className="page-container">
        <Alert
          type="info"
          showIcon
          title="任务尚未结束"
          description="运行中的任务请进入任务详情页查看 Cycle 和日志。"
          action={<Button type="primary" onClick={() => navigate(`/simulation/tasks/${task.task_id}`)}>查看任务详情</Button>}
        />
      </div>
    );
  }

  const canManageTask = task.owner_id === user?.userId;
  const isAdmin = user?.authMode === 'admin';

  return (
    <div className="page-container result-page">
      <PageHeading
        title={<Space>{task.task_name}<TaskStatusTag status={task.status} /></Space>}
        subtitle={`${task.task_id} · ${task.simulator_label || task.simulator_version.toUpperCase()} · Chip Variant ${task.chip_variant_label || task.chip_variant || '默认'}`}
        actions={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/simulation/tasks/${task.task_id}`)}>返回任务详情</Button>
            {canManageTask ? <Button icon={<InboxOutlined />} onClick={() => void archiveToggle()}>{task.archived ? '取消归档' : '归档'}</Button> : null}
            {canManageTask ? <Button type="primary" icon={<RedoOutlined />} onClick={() => Modal.confirm({ title: '重新运行此任务？', content: '将复用原任务 input 创建新的 FIFO 任务。', onOk: rerun })}>重新运行</Button> : null}
          </Space>
        }
      />

      {task.status !== 'COMPLETED' ? (
        <Alert
          className="result-alert"
          type="error"
          showIcon
          title={`任务${task.status === 'FAILED' ? '失败' : '未正常完成'}`}
          description={task.error_message || task.error_code || '没有更多错误信息'}
        />
      ) : null}

      <div className="metrics-grid metrics-grid-4 result-metrics">
        <MetricCard label="Total Cycle" value={formatNumber(result.total_cycle)} accent />
        <MetricCard label="Simulated Time" value={formatSimulatedTime(result.simulated_time_seconds)} hint="芯片模型模拟时间" />
        <MetricCard label="Runtime" value={formatDuration(result.runtime_seconds)} hint="服务器实际仿真耗时" />
        <MetricCard label="Exit Code" value={result.exit_code ?? '—'} />
      </div>

      <Card
        title="结果摘要"
        className="section-card clean-card result-summary-card"
        extra={<TaskStatusTag status={result.status} />}
      >
        <Descriptions column={{ xs: 1, sm: 2, lg: 3 }} size="small">
          <Descriptions.Item label="Simulator">{task.simulator_label || task.simulator_version.toUpperCase()}</Descriptions.Item>
          <Descriptions.Item label="Chip Variant">{task.chip_variant_label || task.chip_variant || '默认'}</Descriptions.Item>
          <Descriptions.Item label="Simulation Mode">{task.simulation_mode_label || task.simulation_mode}</Descriptions.Item>
          {isAdmin ? <Descriptions.Item label="提交人">{task.owner_id}</Descriptions.Item> : null}
          <Descriptions.Item label="提交时间">{formatDateTime(result.submit_time)}</Descriptions.Item>
          <Descriptions.Item label="开始时间">{formatDateTime(result.start_time)}</Descriptions.Item>
          <Descriptions.Item label="完成时间">{formatDateTime(result.end_time)}</Descriptions.Item>
          <Descriptions.Item label="Current Cycle">{formatNumber(result.current_cycle)}</Descriptions.Item>
          <Descriptions.Item label="Total Cycle">{formatNumber(result.total_cycle)}</Descriptions.Item>
          <Descriptions.Item label="Trace"><TraceStatusTag status={result.trace_status} /></Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title="Trace"
        className="section-card clean-card trace-card"
        extra={<TraceStatusTag status={result.trace_status} />}
      >
        {result.trace_viewer_available ? (
          <CatapultTraceViewer
            key={task.task_id}
            taskId={task.task_id}
            title={task.task_name}
            onAnalyze={() => navigate(`/performance?taskId=${encodeURIComponent(task.task_id)}`)}
          />
        ) : traceLoading ? (
          <div className="trace-loading"><Spin /><span>正在加载 Trace…</span></div>
        ) : traceError ? (
          <Alert type="error" showIcon title="Trace 加载失败" description={traceError} />
        ) : (result.trace_source_available ?? result.trace_available) && trace ? (
          <TraceViewer
            events={trace.events}
            eventCount={trace.event_count}
            onAnalyze={() => navigate(`/performance?taskId=${encodeURIComponent(task.task_id)}`)}
          />
        ) : (
          <Alert
            type={result.trace_status === 'FAILED' ? 'error' : 'info'}
            showIcon
            title={result.trace_status === 'FAILED' ? 'Trace 生成失败' : 'Trace 暂不可用'}
            description="Trace 只在仿真结果页展示；生成成功后会直接加载到此卡片。"
          />
        )}
      </Card>

      <Collapse
        className="summary-collapse raw-result-collapse"
        items={[
          {
            key: 'summary',
            label: (
              <div className="raw-result-label">
                <strong>原始结果 · summary.json</strong>
                <span>{result.summary_available ? '可用于调试、归档和字段核对' : '当前不可用'}</span>
              </div>
            ),
            children: result.summary_available && result.summary ? (
              <pre className="json-viewer">{JSON.stringify(result.summary, null, 2)}</pre>
            ) : (
              <Alert type="warning" showIcon title="summary.json 不可用" description={result.summary_error || 'No summary'} />
            ),
          },
        ]}
      />
    </div>
  );
}
