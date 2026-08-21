import { Alert } from 'antd';

interface TraceViewerProps {
  viewerUrl?: string | null;
}

export function TraceViewer({ viewerUrl }: TraceViewerProps) {
  if (!viewerUrl) {
    return (
      <Alert
        type="info"
        showIcon
        message="Trace Viewer 不可用"
        description="未生成 Catapult trace.html。"
      />
    );
  }

  return (
    <div
      style={{
        width: '100%',
        height: '720px',
        border: '1px solid #d9d9d9',
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      <iframe
        title="Catapult Trace Viewer"
        src={viewerUrl}
        style={{ width: '100%', height: '100%', border: 0 }}
      />
    </div>
  );
}
