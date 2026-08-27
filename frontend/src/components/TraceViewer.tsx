import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Input,
  Slider,
  Space,
  Switch,
  Tag,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { TraceEvent } from '../types/simulation';
import { formatNumber } from '../utils/format';
import { ResultWatermark } from './ResultWatermark';

interface TraceViewerProps {
  events: TraceEvent[];
  eventCount: number;
  onAnalyze?: () => void;
}

type TraceLane = {
  key: string;
  label: string;
  events: Required<Pick<TraceEvent, 'name' | 'ts' | 'dur'>>[];
};

const MAX_RENDER_EVENTS = 6000;
const TRACE_BASE_WIDTH = 1600;
const BASE_LANE_HEIGHT = 24;
const TIME_SCALE_OPTIONS = [25, 40, 60, 80, 100, 125, 160, 200, 300, 400] as const;
const LANE_SCALE_OPTIONS = [25, 50, 75, 100, 125, 150, 200] as const;
const DEFAULT_TIME_SCALE_INDEX = TIME_SCALE_OPTIONS.indexOf(100);
const DEFAULT_LANE_SCALE_INDEX = LANE_SCALE_OPTIONS.indexOf(100);

function stableColor(name: string) {
  const palette = ['#2563eb', '#7c3aed', '#0891b2', '#0f766e', '#b45309', '#be123c', '#4f46e5', '#47704f'];
  let hash = 0;
  for (let index = 0; index < name.length; index += 1) {
    hash = (hash * 31 + name.charCodeAt(index)) >>> 0;
  }
  return palette[hash % palette.length];
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function nearestOptionIndex(options: readonly number[], value: number) {
  let bestIndex = 0;
  let bestDistance = Number.POSITIVE_INFINITY;
  options.forEach((option, index) => {
    const distance = Math.abs(option - value);
    if (distance < bestDistance) {
      bestIndex = index;
      bestDistance = distance;
    }
  });
  return bestIndex;
}

export function TraceViewer({ events, eventCount, onAnalyze }: TraceViewerProps) {
  const [timeScaleIndex, setTimeScaleIndex] = useState(DEFAULT_TIME_SCALE_INDEX);
  const [laneScaleIndex, setLaneScaleIndex] = useState(DEFAULT_LANE_SCALE_INDEX);
  const [laneQuery, setLaneQuery] = useState('');
  const [hideEmptyLanes, setHideEmptyLanes] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const viewportRef = useRef<HTMLDivElement>(null);
  const canvasPaneRef = useRef<HTMLDivElement>(null);

  const model = useMemo(() => {
    const processNames = new Map<string, string>();
    const threadNames = new Map<string, string>();

    events.forEach((event) => {
      if (event.ph !== 'M') return;
      const pid = String(event.pid ?? '0');
      const tid = String(event.tid ?? '0');
      const name = typeof event.args?.name === 'string' ? event.args.name : undefined;
      if (!name) return;
      if (event.name === 'process_name') processNames.set(pid, name);
      if (event.name === 'thread_name') threadNames.set(`${pid}:${tid}`, name);
    });

    const laneMap = new Map<string, TraceLane>();

    threadNames.forEach((threadName, key) => {
      const [pid] = key.split(':');
      const processName = processNames.get(pid);
      const label = threadName || [processName, key].filter(Boolean).join(' · ');
      laneMap.set(key, { key, label, events: [] });
    });

    const completeEvents = events
      .filter((event) => (
        event.ph === 'X'
        && typeof event.ts === 'number'
        && typeof event.dur === 'number'
      ))
      .sort((a, b) => (a.ts as number) - (b.ts as number))
      .slice(0, MAX_RENDER_EVENTS);

    let minTs = Number.POSITIVE_INFINITY;
    let maxTs = Number.NEGATIVE_INFINITY;

    completeEvents.forEach((event) => {
      const pid = String(event.pid ?? '0');
      const tid = String(event.tid ?? '0');
      const key = `${pid}:${tid}`;
      const ts = event.ts as number;
      const dur = event.dur as number;
      minTs = Math.min(minTs, ts);
      maxTs = Math.max(maxTs, ts + dur);

      if (!laneMap.has(key)) {
        const processName = processNames.get(pid);
        const threadName = threadNames.get(key);
        const label = threadName || [processName, `P${pid}/T${tid}`].filter(Boolean).join(' · ');
        laneMap.set(key, { key, label, events: [] });
      }
      laneMap.get(key)!.events.push({
        name: String(event.name || 'event'),
        ts,
        dur,
      });
    });

    const lanes = Array.from(laneMap.values());
    if (!Number.isFinite(minTs) || !Number.isFinite(maxTs) || maxTs <= minTs) {
      minTs = 0;
      maxTs = 1;
    }

    return {
      lanes,
      minTs,
      maxTs,
      renderedEventCount: completeEvents.length,
    };
  }, [events]);

  const visibleLanes = useMemo(() => {
    const query = laneQuery.trim().toLowerCase();
    return model.lanes.filter((lane) => {
      if (hideEmptyLanes && lane.events.length === 0) return false;
      if (query && !lane.label.toLowerCase().includes(query)) return false;
      return true;
    });
  }, [hideEmptyLanes, laneQuery, model.lanes]);

  useEffect(() => {
    if (!isFullscreen) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsFullscreen(false);
    };

    window.addEventListener('keydown', handleKeydown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeydown);
    };
  }, [isFullscreen]);

  if (!model.lanes.length) {
    return <Alert type="warning" showIcon title="Trace 中没有可渲染的 Lane" />;
  }

  const duration = model.maxTs - model.minTs;
  const timeScalePercent = TIME_SCALE_OPTIONS[timeScaleIndex];
  const laneScalePercent = LANE_SCALE_OPTIONS[laneScaleIndex];
  const laneHeight = Math.max(6, Math.round(BASE_LANE_HEIGHT * laneScalePercent / 100));
  const laneLabelFontSize = clamp(Math.round(laneHeight * 0.45), 6, 11);
  const height = Math.max(visibleLanes.length * laneHeight, laneHeight);
  const eventHeight = clamp(laneHeight - Math.max(2, laneHeight * 0.25), 2, 20);
  const eventYOffset = Math.max((laneHeight - eventHeight) / 2, 0.5);
  const canvasWidth = Math.max(320, Math.round(TRACE_BASE_WIDTH * timeScalePercent / 100));

  function resetViewport() {
    window.requestAnimationFrame(() => {
      if (viewportRef.current) {
        viewportRef.current.scrollLeft = 0;
        viewportRef.current.scrollTop = 0;
      }
    });
  }

  function handleFitTime() {
    const availableWidth = canvasPaneRef.current?.clientWidth || viewportRef.current?.clientWidth || TRACE_BASE_WIDTH;
    const targetPercent = clamp((availableWidth / TRACE_BASE_WIDTH) * 100, TIME_SCALE_OPTIONS[0], TIME_SCALE_OPTIONS[TIME_SCALE_OPTIONS.length - 1]);
    setTimeScaleIndex(nearestOptionIndex(TIME_SCALE_OPTIONS, targetPercent));
    resetViewport();
  }

  function changeTimeScale(nextIndex: number) {
    setTimeScaleIndex(clamp(Math.round(nextIndex), 0, TIME_SCALE_OPTIONS.length - 1));
  }

  function changeLaneScale(nextIndex: number) {
    setLaneScaleIndex(clamp(Math.round(nextIndex), 0, LANE_SCALE_OPTIONS.length - 1));
  }

  return (
    <div className={`trace-viewer ${isFullscreen ? 'trace-viewer-fullscreen' : ''}`}>
      <ResultWatermark className="result-watermark-fill" enabled={isFullscreen}>
        {isFullscreen ? (
          <div className="trace-fullscreen-head">
            <strong>Trace</strong>
            <Button onClick={() => setIsFullscreen(false)}>退出全屏</Button>
          </div>
        ) : null}

      <div className="trace-toolbar trace-toolbar-rich">
        <div className="trace-toolbar-main">
          <Space wrap size={[8, 8]}>
            <Tag>{formatNumber(eventCount)} events</Tag>
            <Tag>{visibleLanes.length}/{model.lanes.length} lanes</Tag>
            <span className="muted-text">
              ts: {model.minTs.toFixed(2)} → {model.maxTs.toFixed(2)} · span {duration.toFixed(2)}
            </span>
          </Space>

          <div className="trace-lane-tools">
            <Input
              allowClear
              prefix={<SearchOutlined />}
              value={laneQuery}
              onChange={(event) => setLaneQuery(event.target.value)}
              placeholder="搜索 Lane，例如 AICORE0 / VEC"
              className="trace-lane-search"
            />
            <label className="trace-switch-label">
              <Switch size="small" checked={hideEmptyLanes} onChange={setHideEmptyLanes} />
              <span>隐藏空 Lane</span>
            </label>
            <Button onClick={handleFitTime}>适应时间轴</Button>
            <Button onClick={() => setIsFullscreen((value) => !value)}>
              {isFullscreen ? '退出全屏' : '全屏'}
            </Button>
            {onAnalyze ? <Button type="primary" onClick={onAnalyze}>分析此结果</Button> : null}
          </div>
        </div>

        <div className="trace-scale-panels">
          <div className="trace-scale-panel">
            <span className="trace-zoom-label">时间缩放</span>
            <div className="trace-scale-controls">
              <Button size="small" onClick={() => changeTimeScale(timeScaleIndex - 1)} disabled={timeScaleIndex === 0}>−</Button>
              <Slider
                min={0}
                max={TIME_SCALE_OPTIONS.length - 1}
                step={1}
                value={timeScaleIndex}
                tooltip={{ formatter: (value) => `${TIME_SCALE_OPTIONS[value ?? DEFAULT_TIME_SCALE_INDEX]}%` }}
                onChange={changeTimeScale}
              />
              <Button size="small" onClick={() => changeTimeScale(timeScaleIndex + 1)} disabled={timeScaleIndex === TIME_SCALE_OPTIONS.length - 1}>+</Button>
              <span className="trace-zoom-value">{timeScalePercent}%</span>
            </div>
          </div>

          <div className="trace-scale-panel">
            <span className="trace-zoom-label">Lane 高度</span>
            <div className="trace-scale-controls">
              <Button size="small" onClick={() => changeLaneScale(laneScaleIndex - 1)} disabled={laneScaleIndex === 0}>−</Button>
              <Slider
                min={0}
                max={LANE_SCALE_OPTIONS.length - 1}
                step={1}
                value={laneScaleIndex}
                tooltip={{ formatter: (value) => `${LANE_SCALE_OPTIONS[value ?? DEFAULT_LANE_SCALE_INDEX]}%` }}
                onChange={changeLaneScale}
              />
              <Button size="small" onClick={() => changeLaneScale(laneScaleIndex + 1)} disabled={laneScaleIndex === LANE_SCALE_OPTIONS.length - 1}>+</Button>
              <span className="trace-zoom-value">{laneScalePercent}%</span>
            </div>
          </div>
        </div>
      </div>

      {eventCount > MAX_RENDER_EVENTS ? (
        <Alert
          className="trace-limit-alert"
          type="info"
          showIcon
          title={`Trace 较大，为保证浏览器流畅仅渲染前 ${MAX_RENDER_EVENTS} 个 Complete Event`}
        />
      ) : null}

      {visibleLanes.length === 0 ? (
        <Alert
          type="info"
          showIcon
          title="当前筛选条件下没有 Lane"
          description="清空搜索条件或关闭“隐藏空 Lane”后重试。"
        />
      ) : (
        <div className="trace-viewport" ref={viewportRef}>
          <div className="trace-scroll-shell">
            <div className="trace-lane-labels" style={{ height }}>
              {visibleLanes.map((lane) => (
                <div
                  className="trace-lane-label"
                  key={lane.key}
                  title={lane.label}
                  style={{ height: laneHeight, fontSize: laneLabelFontSize }}
                >
                  {lane.label}
                </div>
              ))}
            </div>
            <div className="trace-canvas-scroll" ref={canvasPaneRef}>
              <div className="trace-canvas-zoom" style={{ width: canvasWidth }}>
                <svg
                  className="trace-svg"
                  width={canvasWidth}
                  height={height}
                  viewBox={`0 0 ${TRACE_BASE_WIDTH} ${height}`}
                  preserveAspectRatio="none"
                  role="img"
                  aria-label="Simulation trace timeline"
                >
                  {visibleLanes.map((lane, laneIndex) => {
                    const y = laneIndex * laneHeight;
                    return (
                      <g key={lane.key}>
                        <line
                          x1="0"
                          x2={TRACE_BASE_WIDTH}
                          y1={y + laneHeight}
                          y2={y + laneHeight}
                          className="trace-row-line"
                        />
                        {lane.events.map((event, eventIndex) => {
                          const x = ((event.ts - model.minTs) / duration) * TRACE_BASE_WIDTH;
                          const rectWidth = Math.max((event.dur / duration) * TRACE_BASE_WIDTH, 1.5);
                          return (
                            <rect
                              key={`${event.ts}-${eventIndex}`}
                              x={x}
                              y={y + eventYOffset}
                              width={rectWidth}
                              height={eventHeight}
                              rx={Math.min(3, eventHeight / 3)}
                              fill={stableColor(event.name)}
                              className="trace-event"
                            >
                              <title>{`${event.name}\nts=${event.ts}\ndur=${event.dur}\nlane=${lane.label}`}</title>
                            </rect>
                          );
                        })}
                      </g>
                    );
                  })}
                </svg>
              </div>
            </div>
          </div>
        </div>
      )}
      </ResultWatermark>
    </div>
  );
}
