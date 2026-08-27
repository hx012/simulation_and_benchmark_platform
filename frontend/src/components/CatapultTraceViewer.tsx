import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Space, Spin, Tooltip } from 'antd';
import {
  ExportOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
  ReloadOutlined,
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
  const containerRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const readinessTimerRef = useRef<number | null>(null);
  const viewerReadyRef = useRef(false);
  const [loading, setLoading] = useState(true);
  const [viewerRevision, setViewerRevision] = useState(() => Date.now());
  const [nativeFullscreen, setNativeFullscreen] = useState(false);
  const [fallbackFullscreen, setFallbackFullscreen] = useState(false);
  const viewerUrl = useMemo(
    () => simulationApi.getTraceViewerUrl(taskId, viewerRevision),
    [taskId, viewerRevision],
  );
  const fullscreen = nativeFullscreen || fallbackFullscreen;

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

  useEffect(() => {
    function syncFullscreenState() {
      setNativeFullscreen(document.fullscreenElement === containerRef.current);
    }

    document.addEventListener('fullscreenchange', syncFullscreenState);
    return () => {
      document.removeEventListener('fullscreenchange', syncFullscreenState);
    };
  }, []);

  useEffect(() => {
    if (!fallbackFullscreen) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    function handleKeydown(event: KeyboardEvent) {
      if (event.key === 'Escape') setFallbackFullscreen(false);
    }

    window.addEventListener('keydown', handleKeydown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeydown);
    };
  }, [fallbackFullscreen]);

  async function enterFullscreen() {
    const container = containerRef.current;
    if (!container) return;

    try {
      if (container.requestFullscreen) {
        await container.requestFullscreen();
        window.setTimeout(() => {
          if (document.fullscreenElement !== container) {
            setNativeFullscreen(false);
            setFallbackFullscreen(true);
          }
        }, 250);
        return;
      }
    } catch {
      // Browser or embedding policy denied native fullscreen; use the
      // page-level fallback below.
    }

    setFallbackFullscreen(true);
  }

  async function exitFullscreen() {
    if (document.fullscreenElement) {
      await document.exitFullscreen().catch(() => undefined);
    }
    setFallbackFullscreen(false);
  }

  function reloadViewer() {
    if (readinessTimerRef.current !== null) {
      window.clearTimeout(readinessTimerRef.current);
      readinessTimerRef.current = null;
    }
    viewerReadyRef.current = false;
    setLoading(true);
    setViewerRevision(Date.now());
  }

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
    <div
      ref={containerRef}
      className={`catapult-trace-viewer ${fallbackFullscreen ? 'catapult-trace-viewer-fallback-fullscreen' : ''}`}
    >
      <div className="catapult-trace-toolbar">
        <div>
          <strong>Catapult Trace Viewer</strong>
          <span>支持 Lane、缩放、搜索与事件详情</span>
        </div>
        <Space size={8}>
          <Tooltip title="重新加载 Viewer">
            <Button icon={<ReloadOutlined />} onClick={reloadViewer}>
              重新加载
            </Button>
          </Tooltip>
          <Button icon={<ExportOutlined />} onClick={openStandalone}>
            新窗口打开
          </Button>
          <Button
            icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={() => void (fullscreen ? exitFullscreen() : enterFullscreen())}
          >
            {fullscreen ? '退出全屏' : '全屏查看'}
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
          key={viewerRevision}
          className={`catapult-trace-frame ${loading ? 'catapult-trace-frame-loading' : ''}`}
          src={viewerUrl}
          title={`${title} Catapult Trace Viewer`}
          sandbox="allow-scripts allow-same-origin allow-downloads"
          allow="fullscreen"
          allowFullScreen
          loading="lazy"
          referrerPolicy="same-origin"
          onLoad={waitForViewerReady}
        />
      </div>
    </div>
  );
}
