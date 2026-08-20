import { Alert } from 'antd';

interface CatapultTraceViewerProps {
  traceHtmlUrl?: string;
}

/**
 * Catapult trace viewer wrapper.
 *
 * The actual timeline interaction is provided by trace.html generated from
 * Chromium Catapult trace2html. The platform only manages embedding and
 * lifecycle of the viewer.
 */
export function CatapultTraceViewer({ traceHtmlUrl }: CatapultTraceViewerProps) {
  if (!traceHtmlUrl) {
    return (
      <Alert
        type="info"
        showIcon
        message="Trace Viewer 暂不可用"
        description="当前任务没有可加载的 Catapult trace.html。"
      />
    );
  }

  return (
    <iframe
      title="Catapult Trace Viewer"
      src={traceHtmlUrl}
      style={{
        width: '100%',
        minHeight: 800,
        border: 0,
      }}
    />
  );
}
