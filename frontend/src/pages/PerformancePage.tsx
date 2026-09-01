import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Input,
  Modal,
  Segmented,
  Select,
  Space,
  Spin,
  Tag,
} from 'antd';
import {
  BarChartOutlined,
  DatabaseOutlined,
  FullscreenOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { performanceApi } from '../api/performance';
import { trackAnalyticsEventQuietly } from '../api/analytics';
import { simulationApi } from '../api/simulation';
import { PageHeading } from '../components/PageHeading';
import { ResultWatermark } from '../components/ResultWatermark';
import type {
  TraceProducer,
  TraceTimeAnalysisResponse,
  TraceTimeItem,
} from '../types/performance';
import type { SimulationTask } from '../types/simulation';
import { formatNumber } from '../utils/format';

type InputMode = 'task' | 'file';

const capabilityPlaceholders = [
  {
    name: '指令分布',
    description: '指令类型统计能力开发中。',
  },
  {
    name: '内存访问热力图',
    description: '地址与时间窗口聚合能力开发中。',
  },
];

type CycleTableProps = {
  items: TraceTimeItem[];
  producer: TraceProducer;
  totalCycles: number;
  fullscreen?: boolean;
};

type CycleHierarchy = {
  chip: string;
  aiCore: string;
  engine: string;
  unit: string;
};

type CycleFilters = CycleHierarchy;

const emptyCycleFilters: CycleFilters = { chip: '', aiCore: '', engine: '', unit: '' };
const hierarchyCollator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });

function parseCycleHierarchy(name: string): CycleHierarchy {
  const tokens = name.toUpperCase().split(/[_\s.-]+/).filter(Boolean);
  const chip = tokens.find((token) => /^CHIP\d+$/.test(token)) || '';
  const aiCore = tokens.find((token) => /^AICORE\d+$/.test(token)) || '';
  const engineIndex = tokens.findIndex((token) => /^(AIC|AIV)\d*$/.test(token));
  const engine = engineIndex >= 0 ? tokens[engineIndex] : '';
  const unit = engineIndex >= 0 ? tokens.slice(engineIndex + 1).join('_') : '';
  return { chip, aiCore, engine, unit };
}

function compareCycleItems(left: TraceTimeItem, right: TraceTimeItem) {
  const leftHierarchy = parseCycleHierarchy(left.name);
  const rightHierarchy = parseCycleHierarchy(right.name);
  for (const key of ['chip', 'aiCore', 'engine', 'unit'] as const) {
    const leftValue = leftHierarchy[key];
    const rightValue = rightHierarchy[key];
    if (leftValue && !rightValue) return -1;
    if (!leftValue && rightValue) return 1;
    const compared = hierarchyCollator.compare(leftValue, rightValue);
    if (compared) return compared;
  }
  return hierarchyCollator.compare(left.name, right.name);
}

function uniqueHierarchyValues(items: TraceTimeItem[], key: keyof CycleHierarchy) {
  return [...new Set(items.map((item) => parseCycleHierarchy(item.name)[key]).filter(Boolean))]
    .sort(hierarchyCollator.compare);
}

function CycleTable({
  items,
  producer,
  totalCycles,
  fullscreen = false,
}: CycleTableProps) {
  const rows = [
    { name: 'TOTAL', cycles: totalCycles, ratio_percent: 100, total: true },
    ...items.map((item) => ({ ...item, total: false })),
  ];
  return (
    <div className={`performance-cycle-table-wrap${fullscreen ? ' is-fullscreen' : ''}`}>
      <table className="performance-cycle-table" aria-label="耗时与占比统计">
        <thead><tr><th>{producer === 'esl' ? 'TID' : 'Pipe'}</th><th>耗时 (cycle)</th><th>占比</th></tr></thead>
        <tbody>
          {rows.map((item) => (
            <tr className={item.total ? 'is-total' : undefined} key={item.name}>
              <td title={item.name}>{item.name}</td>
              <td>{formatNumber(item.cycles)}</td>
              <td>{item.ratio_percent.toFixed(2)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type CycleFilterToolbarProps = {
  producer: TraceProducer;
  filters: CycleFilters;
  options: Record<keyof CycleHierarchy, string[]>;
  search: string;
  onFiltersChange: (filters: CycleFilters) => void;
  onSearchChange: (value: string) => void;
};

function CycleFilterToolbar({
  producer, filters, options, search, onFiltersChange, onSearchChange,
}: CycleFilterToolbarProps) {
  const selectOptions = (values: string[]) => values.map((value) => ({ value, label: value }));
  return (
    <div className="performance-cycle-filters">
      <Input.Search
        allowClear
        value={search}
        placeholder={`搜索 ${producer === 'esl' ? 'TID' : 'Pipe'} 名称`}
        onChange={(event) => onSearchChange(event.target.value)}
      />
      {options.chip.length ? <Select allowClear value={filters.chip || undefined} placeholder="Chip" options={selectOptions(options.chip)} onChange={(chip) => onFiltersChange({ chip: chip || '', aiCore: '', engine: '', unit: '' })} /> : null}
      {options.aiCore.length ? <Select allowClear value={filters.aiCore || undefined} placeholder="AICore" options={selectOptions(options.aiCore)} onChange={(aiCore) => onFiltersChange({ ...filters, aiCore: aiCore || '', engine: '', unit: '' })} /> : null}
      {options.engine.length ? <Select allowClear value={filters.engine || undefined} placeholder="AIC / AIV" options={selectOptions(options.engine)} onChange={(engine) => onFiltersChange({ ...filters, engine: engine || '', unit: '' })} /> : null}
      {options.unit.length ? <Select allowClear value={filters.unit || undefined} placeholder="执行单元" options={selectOptions(options.unit)} onChange={(unit) => onFiltersChange({ ...filters, unit: unit || '' })} /> : null}
      <Button onClick={() => { onSearchChange(''); onFiltersChange(emptyCycleFilters); }}>重置</Button>
    </div>
  );
}

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
  const [cycleFullscreen, setCycleFullscreen] = useState(false);
  const [cycleSearch, setCycleSearch] = useState('');
  const [cycleFilters, setCycleFilters] = useState<CycleFilters>(emptyCycleFilters);

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
    setCycleSearch('');
    setCycleFilters({ ...emptyCycleFilters });
    try {
      const analysis = await performanceApi.analyzeTaskTrace(taskId);
      setResult(analysis);
      trackAnalyticsEventQuietly({
        event_name: 'performance.trace_analyze_success',
        page_key: 'performance.workspace',
        result: 'success',
        target_type: 'simulation_task',
        target_id: taskId,
        target_name: analysis.source_name,
      });
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
    setCycleSearch('');
    setCycleFilters({ ...emptyCycleFilters });
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

  const sortedCycleItems = useMemo(
    () => [...(result?.items || [])].sort(compareCycleItems),
    [result],
  );

  const cycleFilterOptions = useMemo(() => {
    const matches = (item: TraceTimeItem, filters: Partial<CycleFilters>) => {
      const hierarchy = parseCycleHierarchy(item.name);
      return Object.entries(filters).every(([key, value]) => (
        !value || hierarchy[key as keyof CycleHierarchy] === value
      ));
    };
    const aiCoreItems = sortedCycleItems.filter((item) => matches(item, { chip: cycleFilters.chip }));
    const engineItems = aiCoreItems.filter((item) => matches(item, { aiCore: cycleFilters.aiCore }));
    const unitItems = engineItems.filter((item) => matches(item, { engine: cycleFilters.engine }));
    return {
      chip: uniqueHierarchyValues(sortedCycleItems, 'chip'),
      aiCore: uniqueHierarchyValues(aiCoreItems, 'aiCore'),
      engine: uniqueHierarchyValues(engineItems, 'engine'),
      unit: uniqueHierarchyValues(unitItems, 'unit'),
    };
  }, [cycleFilters.aiCore, cycleFilters.chip, cycleFilters.engine, sortedCycleItems]);

  const filteredCycleItems = useMemo(() => {
    const query = cycleSearch.trim().toLowerCase();
    return sortedCycleItems.filter((item) => {
      const hierarchy = parseCycleHierarchy(item.name);
      return (!query || item.name.toLowerCase().includes(query))
        && (!cycleFilters.chip || hierarchy.chip === cycleFilters.chip)
        && (!cycleFilters.aiCore || hierarchy.aiCore === cycleFilters.aiCore)
        && (!cycleFilters.engine || hierarchy.engine === cycleFilters.engine)
        && (!cycleFilters.unit || hierarchy.unit === cycleFilters.unit);
    });
  }, [cycleFilters, cycleSearch, sortedCycleItems]);

  function openCycleFullscreen() {
    setCycleFullscreen(true);
  }

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
          title="数据无法分析"
          description={error}
        />
      ) : null}

      <div className="performance-section-heading">
        <div><h2>分析状态与导航</h2><span>系统自动运行当前数据支持且已经开放的全部分析</span></div>
      </div>
      <nav className="performance-analysis-nav" aria-label="分析结果导航">
        <button type="button" className="is-open" disabled={!result} onClick={() => resultRef.current?.scrollIntoView({ behavior: 'smooth' })}>
          <span><strong>Trace 时间分析</strong><small>统计 Pipe / TID 耗时与周期占比</small></span>
          <Tag color={result ? 'success' : analyzing ? 'processing' : 'blue'}>{result ? '查看结果' : analyzing ? '分析中' : '已开放'}</Tag>
        </button>
        {capabilityPlaceholders.map((capability) => (
          <button type="button" key={capability.name} disabled>
            <span><strong>{capability.name}</strong><small>{capability.description}</small></span><Tag>能力开发中</Tag>
          </button>
        ))}
      </nav>

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
              {result.skipped_event_count ? (
                <Alert
                  className="performance-alert"
                  type="warning"
                  showIcon
                  title={`已跳过 ${formatNumber(result.skipped_event_count)} 个不参与周期统计的事件`}
                  description={result.producer === 'esl'
                    ? '这些事件缺少有效的时间字段，或 pid 不符合 core.subcore 格式，因此无法归入 ESL 周期统计。'
                    : '这些事件缺少有效的 ts/dur，或 tid 无法映射到 Pipe；通常属于 Trace 元数据或标记事件。同步事件已单独统计。'}
                />
              ) : null}
              <Card
                title="耗时统计"
                extra={(
                  <Space size={10}>
                    <span className="muted-text">
                      显示 {filteredCycleItems.length} / {result.items.length} 个{result.producer === 'esl' ? ' TID' : ' Pipe'}
                    </span>
                    <Button size="small" icon={<FullscreenOutlined />} onClick={openCycleFullscreen}>
                      全屏查看
                    </Button>
                  </Space>
                )}
                className="clean-card performance-chart-card"
              >
                <CycleFilterToolbar
                  producer={result.producer}
                  filters={cycleFilters}
                  options={cycleFilterOptions}
                  search={cycleSearch}
                  onFiltersChange={setCycleFilters}
                  onSearchChange={setCycleSearch}
                />
                <CycleTable
                  items={filteredCycleItems}
                  producer={result.producer}
                  totalCycles={result.total_cycles}
                />
              </Card>
            <Modal
              className="performance-cycle-modal"
              title={`耗时统计 · ${result.source_name}`}
              open={cycleFullscreen}
              footer={null}
              width="calc(100vw - 48px)"
              style={{ top: 24 }}
              onCancel={() => setCycleFullscreen(false)}
            >
              <ResultWatermark className="performance-cycle-watermark">
                <div className="performance-cycle-modal-toolbar">
                  <CycleFilterToolbar
                    producer={result.producer}
                    filters={cycleFilters}
                    options={cycleFilterOptions}
                    search={cycleSearch}
                    onFiltersChange={setCycleFilters}
                    onSearchChange={setCycleSearch}
                  />
                  <span>
                    显示 {filteredCycleItems.length} / {result.items.length}
                  </span>
                </div>
                <CycleTable
                  items={filteredCycleItems}
                  producer={result.producer}
                  totalCycles={result.total_cycles}
                  fullscreen
                />
              </ResultWatermark>
            </Modal>
          </>
        ) : null}
      </div>
    </div>
  );
}
