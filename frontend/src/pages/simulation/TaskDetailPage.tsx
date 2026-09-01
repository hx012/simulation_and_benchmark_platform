import { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  message,
  Modal,
  Space,
  Spin,
} from 'antd';
import {
  ArrowLeftOutlined,
  CloseOutlined,
  FullscreenOutlined,
  StopOutlined,
  VerticalAlignBottomOutlined,
  VerticalAlignTopOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { simulationApi } from '../../api/simulation';
import { MetricCard } from '../../components/MetricCard';
import { PageHeading } from '../../components/PageHeading';
import { TaskStatusTag } from '../../components/StatusTag';
import { useTaskPolling } from '../../hooks/useTaskPolling';
import type { SimulationQueueResponse } from '../../types/simulation';
import { useAuth } from '../../auth/AuthContext';
import { PermissionRequestButton } from '../../components/PermissionRequestButton';
import { ResultWatermark } from '../../components/ResultWatermark';
import {
  executionPhaseText,
  formatDateTime,
  formatDuration,
  formatNumber,
  isTerminalStatus,
} from '../../utils/format';

const LOG_CHUNK_BYTES = 128 * 1024;
const LOG_RENDER_CHAR_LIMIT = 256 * 1024;

export function TaskDetailPage() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { user, hasResource } = useAuth();
  const canViewLog = hasResource('simulation.log');
  const { task, loading, error, refresh } = useTaskPolling(taskId, 2000);
  const [queue, setQueue] = useState<SimulationQueueResponse | null>(null);
  const [logText, setLogText] = useState('');
  const [logAvailable, setLogAvailable] = useState(false);
  const [logEof, setLogEof] = useState(false);
  const [logTruncated, setLogTruncated] = useState(false);
  const [logFullscreen, setLogFullscreen] = useState(false);
  const logOffset = useRef(0);
  const logBoxRef = useRef<HTMLPreElement>(null);
  const fullscreenLogRef = useRef<HTMLPreElement>(null);
  const followLogTailRef = useRef(true);

  useEffect(() => {
    if (!taskId || !task || !canViewLog) return;
    if (task.status === 'QUEUED') {
      simulationApi.getQueue(taskId).then(setQueue).catch(() => setQueue(null));
    } else {
      setQueue(null);
    }
  }, [canViewLog, task?.status, taskId]);

  useEffect(() => {
    logOffset.current = 0;
    setLogText('');
    setLogAvailable(false);
    setLogEof(false);
    setLogTruncated(false);
    followLogTailRef.current = true;
  }, [taskId]);

  useEffect(() => {
    if (!taskId || !task) return;
    let cancelled = false;
    let timer: number | null = null;
    let initialRead = logOffset.current === 0;

    const read = async () => {
      try {
        const chunk = await simulationApi.getLogs(
          taskId,
          logOffset.current,
          LOG_CHUNK_BYTES,
          initialRead,
        );
        if (cancelled) return;
        if (chunk.available) initialRead = false;

        setLogAvailable(chunk.available);
        setLogEof(chunk.eof);
        if (chunk.reset) {
          setLogText(chunk.text);
        } else if (chunk.text) {
          setLogText((current) => {
            const combined = current + chunk.text;
            if (combined.length <= LOG_RENDER_CHAR_LIMIT) return combined;
            return combined.slice(-LOG_RENDER_CHAR_LIMIT);
          });
        }
        if (chunk.offset > 0 || chunk.file_size > LOG_RENDER_CHAR_LIMIT) {
          setLogTruncated(true);
        }
        logOffset.current = chunk.next_offset;

        // 只追赶首次读取后新增的内容；首屏直接从文件末尾开始，避免把
        // 数十 MB 的历史日志全部下载并渲染到一个 <pre> 中。
        if (!chunk.eof) {
          timer = window.setTimeout(read, 150);
          return;
        }
      } catch {
        // 日志读取失败不影响任务状态页，下一轮仍可继续尝试。
      }

      if (!cancelled && !isTerminalStatus(task.status)) {
        timer = window.setTimeout(read, 2000);
      }
    };

    void read();
    return () => {
      cancelled = true;
      if (timer != null) window.clearTimeout(timer);
    };
  }, [task?.status, taskId]);

  useEffect(() => {
    if (!logFullscreen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setLogFullscreen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [logFullscreen]);

  useEffect(() => {
    if (followLogTailRef.current && logBoxRef.current) {
      logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
    }
    if (followLogTailRef.current && fullscreenLogRef.current) {
      fullscreenLogRef.current.scrollTop = fullscreenLogRef.current.scrollHeight;
    }
  }, [logText]);

  function scrollLog(target: 'top' | 'bottom') {
    followLogTailRef.current = target === 'bottom';
    const nodes = [logBoxRef.current, fullscreenLogRef.current].filter(Boolean) as HTMLPreElement[];
    nodes.forEach((node) => {
      node.scrollTop = target === 'top' ? 0 : node.scrollHeight;
    });
  }

  function handleLogScroll(event: React.UIEvent<HTMLPreElement>) {
    const node = event.currentTarget;
    followLogTailRef.current = node.scrollHeight - node.scrollTop - node.clientHeight < 48;
  }

  async function terminate() {
    if (!taskId) return;
    try {
      await simulationApi.terminateTask(taskId);
      message.success('终止请求已提交，Worker 将结束任务进程组');
      await refresh();
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    }
  }

  async function cancel() {
    if (!taskId) return;
    try {
      await simulationApi.cancelTask(taskId);
      message.success('任务已取消');
      await refresh();
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    }
  }

  if (loading && !task) return <div className="center-state"><Spin size="large" /></div>;

  if (error || !task) {
    return (
      <div className="page-container">
        <Alert type="error" showIcon title="任务读取失败" description={error?.message || 'Task not found'} />
      </div>
    );
  }

  const terminal = isTerminalStatus(task.status);
  const terminalSuccess = task.status === 'COMPLETED';
  const canManageTask = task.owner_id === user?.userId;
  const isAdmin = user?.authMode === 'admin';

  return (
    <div className="page-container task-detail-page">
      <PageHeading
        title={<Space>{task.task_name}<TaskStatusTag status={task.status} /></Space>}
        subtitle={`${task.task_id} · ${task.simulator_label || task.simulator_version.toUpperCase()} · Chip Variant ${task.chip_variant_label || task.chip_variant || '默认'}`}
        actions={(
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/simulation/tasks')}>返回列表</Button>
            {canManageTask && task.status === 'QUEUED' ? (
              <Button danger onClick={() => Modal.confirm({ title: '确认取消任务？', content: task.task_name, okButtonProps: { danger: true }, onOk: cancel })}>取消任务</Button>
            ) : null}
            {canManageTask && task.status === 'RUNNING' ? (
              <Button danger icon={<StopOutlined />} onClick={() => Modal.confirm({ title: '确认强制终止？', content: 'Worker 将向 Simulator 进程组发送终止信号。', okButtonProps: { danger: true }, onOk: terminate })}>强制终止</Button>
            ) : null}
          </Space>
        )}
      />

      {terminal ? (
        <Alert
          className="terminal-banner"
          showIcon
          type={terminalSuccess ? 'success' : task.status === 'FAILED' ? 'error' : 'warning'}
          title={terminalSuccess ? '仿真执行完成' : `任务已结束：${task.status}`}
          description={
            terminalSuccess
              ? (canViewLog
                ? '结果已经生成。你可以继续查看完整运行日志，或进入仿真结果页查看 Trace 与最终指标。'
                : '结果已经生成。你可以进入仿真结果页查看 Trace 与最终指标；原始日志需要单独申请权限。')
              : (task.error_message || task.error_code || (canViewLog
                ? '任务已经进入终态，运行日志仍保留在当前页面。'
                : '任务已经进入终态；原始日志需要单独申请权限。'))
          }
          action={terminalSuccess ? (
            <Button
              type="primary"
              onClick={() => navigate(`/simulation/tasks/${task.task_id}/result`)}
            >
              查看仿真结果
            </Button>
          ) : undefined}
        />
      ) : null}

      <div className="metrics-grid metrics-grid-4">
        <MetricCard label={terminalSuccess ? '最终 Cycle' : '当前 Cycle'} value={formatNumber(task.current_cycle)} accent={task.status === 'RUNNING'} />
        <MetricCard
          label="实际运行时间"
          value={formatDuration(task.runtime_seconds)}
          hint={terminal ? 'Worker 最终计时结果' : 'Worker 权威计时，每约 3 秒更新'}
        />
        <MetricCard label="执行阶段" value={executionPhaseText[task.execution_phase]} />
        <MetricCard
          label="队列"
          value={task.status === 'QUEUED' ? `前方 ${queue?.queued_ahead ?? '—'} 个` : terminal ? '已结束' : '已开始'}
        />
      </div>

      <Card title="任务信息" className="section-card clean-card">
        <Descriptions column={{ xs: 1, sm: 2, lg: 3 }} size="small">
          <Descriptions.Item label="Simulator">{task.simulator_label || task.simulator_version.toUpperCase()}</Descriptions.Item>
          <Descriptions.Item label="Simulation Mode">{task.simulation_mode_label || task.simulation_mode}</Descriptions.Item>
          <Descriptions.Item label="Chip Variant">{task.chip_variant_label || task.chip_variant || '默认'}</Descriptions.Item>
          {isAdmin ? <Descriptions.Item label="提交人">{task.owner_id}</Descriptions.Item> : null}
          <Descriptions.Item label="提交时间">{formatDateTime(task.submit_time)}</Descriptions.Item>
          <Descriptions.Item label="开始时间">{formatDateTime(task.start_time)}</Descriptions.Item>
          <Descriptions.Item label="完成时间">{formatDateTime(task.end_time)}</Descriptions.Item>
        </Descriptions>
      </Card>

      {canViewLog ? (
        <Card
          title={terminal ? '运行日志' : '实时运行日志'}
          className="section-card clean-card"
          extra={(
            <Space size={8}>
              <span className="muted-text">
                {logTruncated ? '仅显示最近 256 KB' : terminal && logEof ? '完整日志' : '增量读取'}
              </span>
              <Button size="small" icon={<VerticalAlignTopOutlined />} onClick={() => scrollLog('top')}>顶部</Button>
              <Button size="small" icon={<VerticalAlignBottomOutlined />} onClick={() => scrollLog('bottom')}>末尾</Button>
              <Button size="small" icon={<FullscreenOutlined />} onClick={() => setLogFullscreen(true)}>全屏</Button>
            </Space>
          )}
        >
          <pre ref={logBoxRef} className="log-viewer" onScroll={handleLogScroll}>
            {logAvailable ? (logText || '等待新的日志输出…') : '日志文件尚未生成…'}
          </pre>
        </Card>
      ) : (
        <Card title={terminal ? '运行日志' : '实时运行日志'} className="section-card clean-card">
          <div className="permission-locked-panel">
            <LockOutlined />
            <div>
              <strong>原始运行日志属于受限内容</strong>
              <p>获得 Simulator 日志访问权限后，可以查看自己任务的完整日志。</p>
            </div>
            <PermissionRequestButton
              permission="simulation_log"
              reason={`从任务 ${task.task_id} 的日志区域申请`}
            />
          </div>
        </Card>
      )}

      {logFullscreen ? (
        <ResultWatermark className="log-fullscreen">
          <div className="log-fullscreen-content" role="dialog" aria-modal="true" aria-label="运行日志全屏查看">
            <div className="log-fullscreen-head">
              <div>
                <strong>运行日志</strong>
                <span>{task.task_name}</span>
              </div>
              <Space>
                <Button icon={<VerticalAlignTopOutlined />} onClick={() => scrollLog('top')}>顶部</Button>
                <Button icon={<VerticalAlignBottomOutlined />} onClick={() => scrollLog('bottom')}>末尾</Button>
                <Button icon={<CloseOutlined />} onClick={() => setLogFullscreen(false)}>退出全屏</Button>
              </Space>
            </div>
            <pre ref={fullscreenLogRef} className="log-viewer log-viewer-fullscreen" onScroll={handleLogScroll}>
              {logAvailable ? (logText || '等待新的日志输出…') : '日志文件尚未生成…'}
            </pre>
          </div>
        </ResultWatermark>
      ) : null}
    </div>
  );
}
