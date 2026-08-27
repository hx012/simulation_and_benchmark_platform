import type { CSSProperties, ReactNode } from 'react';
import { Watermark } from 'antd';
import { useAuth } from '../auth/AuthContext';

interface ResultWatermarkProps {
  children: ReactNode;
  className?: string;
  enabled?: boolean;
  style?: CSSProperties;
}

export function ResultWatermark({ children, className, enabled = true, style }: ResultWatermarkProps) {
  const { user } = useAuth();
  const employeeId = user?.userId || 'UNKNOWN';

  if (!enabled) return <>{children}</>;

  return (
    <Watermark
      className={className}
      style={style}
      inherit={false}
      content={`MSKPP&AIBench + ${employeeId}`}
      rotate={-22}
      gap={[190, 118]}
      offset={[76, 48]}
      zIndex={12}
      font={{
        color: 'rgba(31, 78, 121, 0.10)',
        fontFamily: 'Arial, "Microsoft YaHei", sans-serif',
        fontSize: 15,
        fontWeight: 600,
      }}
    >
      {children}
    </Watermark>
  );
}
