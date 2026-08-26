import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Segmented,
  Select,
  Space,
  Spin,
  Tag,
} from 'antd';
import {
  BarChartOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { performanceApi } from '../api/performance';
import { simulationApi } from '../api/simulation';
import { PageHeading } from '../components/PageHeading';
import type {
  TraceProducer,
  TraceTimeAnalysisResponse,
} from '../types/performance';
import type { SimulationTask } from '../types/simulation';
import { formatNumber } from '../utils/format';

type InputMode = 'task' | 'file';

const capabilityPlaceholders = [
  {
    name: 'Roofline',
    description: '分析算术强度与计算、带宽上限之间的关系。',
  },
  {
    name: 'Arithmetic / Memory Bandwidth',
    description: '分析计算单元利用率、访存吞吐和带宽瓶颈。',
  },
  {
    name: 'Memory Access Pattern',
    description: '识别地址分布、访问热点、步长与缓存局部性。',
  },
  {
    name: 'Communication Matrix',
    description: '分析节点、Core 或 Rank 间的通信量与热点路径。',
  },
];

export function PerformancePage() {
  const [searchParams] = useSearchParams();
  const initialTaskId = searchParams.get('taskId') || '';
  const { user } = useAuth();
  const ownerId = user?.userId || import.meta.env.VITE_DEFAULT_OWNER_ID || 'admin';
  const resultRef = useRef<HTMLDivElement>(null);
  const autoAnalyzedTask = useRef<string>('');

  const [inputMode, setInputMode] = useState<InputMode>('task');
  const [tasks, setTasks] = useState<SimulationTask[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [selectedTaskId, setSelectedTaskId] = useState(initialTaskId);
  const [producer, setProducer] = useState<TraceProducer>('mskpp');
  const [localFile, setLocalFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TraceTimeAnalysisResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    setTasksLoading(true);
    simulationApi.listTasks({
      ownerId,
      status: 'COMPLETED',
      archived: false,
      page: 1,
      pageSize: 100,
    })
      .then(async (response) => {
        let available = response.items.filter((task) => task.trace_status === 'READY');
        if (initialTaskId && !available.some((task) => task.task_id === initialTaskId)) {
          try {
            const selected = await simulationApi.getTask(initialTaskId);
            if (selected.trace_status === 'READY') available = [selected, ...available];
          } catch {
            // The analysis request below surfaces a precise task/trace error.
          }
        }
        if (!cancelled) {
          setTasks(available);
          setSelectedTaskId((current) => current || available[0]?.task_id || '');
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setTasksLoading(false);
      });
    return () => { cancelled = true; };
  }, [initialTaskId, ownerId]);

  const runTaskAnalysis = useCallback(async (taskId: string) => {
    if (!taskId) {
      setError('请选择一个 Trace 已就绪的仿真任务');
      return;
    }
    setAnalyzing(true);
    setError(null);
    setResult(null);
    try {
      setResult(await performanceApi.analyzeTaskTrace(taskId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setAnalyzing(false);
    }
  }, []);

  useEffect(() => {
    if (!initialTaskId || autoAnalyzedTask.current === initialTaskId) return;
    autoAnalyzedTask.current = initialTaskId;
    void runTaskAnalysis(initialTaskId);
  }, [initialTaskId, runTaskAnalysis]);

  async function runAnalysis() {
    if (inputMode === 'task') {
      await runTaskAnalysis(selectedTaskId);
      return;
    }
    if (!localFile) {
      setError('请选择一个 trace.json 文件');
      return;
    }
    setAnalyzing(true);
    setError(null);
    setResult(null);
    try {
      setResult(await performanceApi.analyzeUploadedTrace(localFile, producer));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setAnalyzing(false);
    }
  }

  function switchMode(value: string | number) {
    setInputMode(value as InputMode);
    setResult(null);
    setError(null);
  }

  const maxCycles = useMemo(
    () => Math.max(...(result?.items.map((item) => item.cycles) || [0]), 1),
    [result],
  );

  return (
    <div className="page-container performance-page">
      <PageHeading
        title="性能分析工作台"
        subtitle="接入性能数据，查看当前可用的分析能力与结论"
        actions={<Tag color="blue">Trace 时间分析已开放</Tag>}
      />

      <Card
        title="接入分析数据"
        className="clean-card performance-input-card"
        extra={(
          <Segmented
            value={inputMode}
            onChange={switchMode}
            options={[
              { label: '平台任务', value: 'task', icon: <DatabaseOutlined /> },
              { label: '本地文件', value: 'file', icon: <UploadOutlined /> },
            ]}
          />
        )}
      >
        {inputMode === 'task' ? (
          <div className="performance-input-grid">
            <label className="performance-field performance-task-field">
              <span>仿真任务</span>
              <Select
                showSearch
                loading={tasksLoading}
                value={selectedTaskId || undefined}
                placeholder="选择已完成且 Trace 就绪的任务"
                optionFilterProp="label"
                onChange={(value) => {
                  setSelectedTaskId(value);
                  setResult(null);
                  setError(null);
                }}
                options={tasks.map((task) => ({
                  value: task.task_id,
                  label: `${task.task_name} · ${task.task_id}`,
                }))}
              />
            </label>
            <div className="performance-field">
              <span>分析数据类型</span>
              <div className="performance-static-field">Trace</div>
            </div>
            <div className="performance-field">
              <span>数据生成来源</span>
              <div className="performance-static-field">MSKPP</div>
            </div>
          </div>
        ) : (
          <div className="performance-input-grid">
            <div className="performance-field">
              <span>分析数据类型</span>
              <div className="performance-static-field">Trace</div>
            </div>
            <label className="performance-field">
              <span>数据生成来源</span>
              <Select<TraceProducer>
                value={producer}
                onChange={(value) => {
                  setProducer(value);
                  setResult(null);
                  setError(null);
                }}
                options={[
                  { value: 'mskpp', label: 'MSKPP' },
                  { value: 'esl', label: 'ESL' },
                ]}
              />
            </label>
            <label className="performance-field">
              <span>输入文件</span>
              <input
                className="performance-file-input"
                type="file"
                accept=".json,application/json"
                onChange={(event) => {
                  setLocalFile(event.target.files?.[0] || null);
                  setResult(null);
                  setError(null);
                }}
              />
            </label>
          </div>
        )}
        <div className="performance-input-actions">
          <span>
            {inputMode === 'task'
              ? '平台任务固定使用 MSKPP Trace'
              : '文件最大 64 MB；类型由用户选择，系统仍会校验数据结构'}
          </span>
          <Button
            type="primary"
            icon={<BarChartOutlined />}
            loading={analyzing}
            onClick={() => void runAnalysis()}
          >
            加载并分析
          </Button>
        </div>
      </Card>

      {error ? (
        <Alert
          className="performance-alert"
          type="error"
          showIcon
          message="数据无法分析"
          description={error}
        />
      ) : null}

      <div className="performance-section-heading">
        <div><h2>分析能力</h2><span>根据当前接入的数据更新状态</span></div>
      </div>
      <div className="performance-capability-grid">
        <Card className={`performance-capability-card ${result ? 'is-ready' : ''}`}>
          <div className="performance-capability-head">
            <ClockCircleOutlined />
            <Tag color={result ? 'success' : analyzing ? 'processing' : 'default'}>
              {result ? '可分析' : analyzing ? '分析中' : '等待数据'}
            </Tag>
          </div>
          <h3>Trace 时间分析</h3>
          <p>统计 MSKPP/ESL Pipe 或 TID 耗时、周期占比和同步事件过滤情况。</p>
          <Button
            disabled={!result}
            onClick={() => resultRef.current?.scrollIntoView({ behavior: 'smooth' })}
          >
            查看结果 ↓
          </Button>
        </Card>
        {capabilityPlaceholders.map((capability) => (
          <Card key={capability.name} className="performance-capability-card is-planned">
            <div className="performance-capability-head">
              <BarChartOutlined />
              <Tag>开发中</Tag>
            </div>
            <h3>{capability.name}</h3>
            <p>{capability.description}</p>
            <Button disabled>能力预留</Button>
          </Card>
        ))}
      </div>

      <div ref={resultRef} className="performance-result-anchor">
        {analyzing ? (
          <Card className="clean-card performance-result-loading">
            <Spin /><span>正在解析 Trace 并计算时间区间…</span>
          </Card>
        ) : result ? (
          <>
            <div className="performance-section-heading">
              <div>
                <h2>Trace 时间分析结果</h2>
                <span>{result.source_name} · {result.producer.toUpperCase()}</span>
              </div>
            </div>
            <div className="metrics-grid metrics-grid-4 performance-result-metrics">
              <div className="metric-card metric-card-accent"><div className="metric-label">Total Cycle</div><div className="metric-value">{formatNumber(result.total_cycles)}</div></div>
              <div className="metric-card"><div className="metric-label">Trace Events</div><div className="metric-value">{formatNumber(result.event_count)}</div></div>
              <div className="metric-card"><div className="metric-label">Analyzed Events</div><div className="metric-value">{formatNumber(result.analyzed_event_count)}</div></div>
              <div className="metric-card"><div className="metric-label">Filtered Sync Events</div><div className="metric-value">{formatNumber(result.sync_event_count)}</div></div>
            </div>
            {result.warnings.length ? (
              <Alert
                className="performance-alert"
                type="warning"
                showIcon
                message="部分事件未参与分析"
                description={result.warnings.join('；')}
              />
            ) : null}
            <Card
              title="周期分布"
              extra={`共 ${result.items.length} 个${result.producer === 'esl' ? ' TID' : ' Pipe'}`}
              className="clean-card performance-chart-card"
            >
              <div className="performance-bars">
                {result.items.map((item) => (
                  <div className="performance-bar-row" key={item.name}>
                    <strong title={item.name}>{item.name}</strong>
                    <div className="performance-bar-track">
                      <div
                        className="performance-bar-fill"
                        style={{ width: `${Math.max(item.cycles / maxCycles * 100, 1)}%` }}
                      />
                    </div>
                    <span>
                      {formatNumber(item.cycles)} / {item.ratio_percent.toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          </>
        ) : null}
      </div>
    </div>
  );
}
