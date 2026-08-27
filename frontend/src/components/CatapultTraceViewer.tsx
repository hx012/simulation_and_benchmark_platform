import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Space, Spin } from 'antd';
import {
  ExportOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { simulationApi } from '../api/simulation';

interface CatapultTraceViewerProps {
  taskId: string;
  title: string;
  onAnalyze?: () => void;
}

const VIEWER_READY_TIMEOUT_MS = 120_000;
const VIEWER_STATUS_MESSAGE = 'catapult-trace-viewer-status';

export function CatapultTraceViewer({ taskId, title, onAnalyze }: CatapultTraceViewerProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const readinessTimerRef = useRef<number | null>(null);
  const viewerReadyRef = useRef(false);
  const [loading, setLoading] = useState(true);
  const viewerUrl = useMemo(
    () => simulationApi.getTraceViewerUrl(taskId),
    [taskId],
  );

  useEffect(() => {
    if (readinessTimerRef.current !== null) {
      window.clearTimeout(readinessTimerRef.current);
      readinessTimerRef.current = null;
    }
    viewerReadyRef.current = false;
    setLoading(true);
  }, [viewerUrl]);

  useEffect(() => {
    function handleViewerStatus(event: MessageEvent) {
      if (event.source !== iframeRef.current?.contentWindow) return;
      if (!event.data || typeof event.data !== 'object') return;

      const message = event.data as { type?: unknown; status?: unknown };
      if (message.type !== VIEWER_STATUS_MESSAGE) return;
      if (!['ready', 'error', 'timeout'].includes(String(message.status))) return;

      viewerReadyRef.current = true;
      if (readinessTimerRef.current !== null) {
        window.clearTimeout(readinessTimerRef.current);
        readinessTimerRef.current = null;
      }
      setLoading(false);
    }

    window.addEventListener('message', handleViewerStatus);
    return () => {
      window.removeEventListener('message', handleViewerStatus);
      if (readinessTimerRef.current !== null) {
        window.clearTimeout(readinessTimerRef.current);
      }
    };
  }, []);

  function waitForViewerReady() {
    if (readinessTimerRef.current !== null) {
      window.clearTimeout(readinessTimerRef.current);
    }

    if (viewerReadyRef.current) return;
    readinessTimerRef.current = window.setTimeout(() => {
      readinessTimerRef.current = null;
      setLoading(false);
    }, VIEWER_READY_TIMEOUT_MS);
  }

  function openStandalone() {
    window.open(viewerUrl, '_blank', 'noopener,noreferrer');
  }

  return (
    <div className="catapult-trace-viewer">
      <div className="catapult-trace-toolbar">
        <div>
          <strong>Catapult Trace Viewer</strong>
          <span>支持 Lane、缩放、搜索与事件详情</span>
        </div>
        <Space size={8}>
          <Button icon={<ExportOutlined />} onClick={openStandalone}>
            新窗口打开
          </Button>
          {onAnalyze ? (
            <Button type="primary" icon={<BarChartOutlined />} onClick={onAnalyze}>
              分析此结果
            </Button>
          ) : null}
        </Space>
      </div>

      <div className="catapult-trace-frame-shell">
        {loading ? (
          <div className="catapult-trace-loading">
            <Spin />
            <span>正在解析 Trace 数据…</span>
          </div>
        ) : null}
        <iframe
          ref={iframeRef}
          key={taskId}
          className={`catapult-trace-frame ${loading ? 'catapult-trace-frame-loading' : ''}`}
          src={viewerUrl}
          title={`${title} Catapult Trace Viewer`}
          sandbox="allow-scripts allow-same-origin allow-downloads"
          loading="lazy"
          referrerPolicy="same-origin"
          onLoad={waitForViewerReady}
        />
      </div>
    </div>
  );
}
