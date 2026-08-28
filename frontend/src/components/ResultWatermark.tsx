import type { ComponentProps, ReactNode } from 'react';
import { Watermark } from 'antd';
import { useAuth } from '../auth/AuthContext';

interface ResultWatermarkProps extends Omit<ComponentProps<typeof Watermark>, 'children' | 'content'> {
  children: ReactNode;
  enabled?: boolean;
}

export function ResultWatermark({ children, enabled = true, ...watermarkProps }: ResultWatermarkProps) {
  const { user } = useAuth();
  const employeeId = user?.userId || 'UNKNOWN';

  if (!enabled) return <>{children}</>;

  return (
    <Watermark
      {...watermarkProps}
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
        fontWeight: 400,
      }}
    >
      {children}
    </Watermark>
  );
}
