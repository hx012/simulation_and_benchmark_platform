import type { ReactNode } from 'react';

interface MetricCardProps {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  accent?: boolean;
}

export function MetricCard({ label, value, hint, accent = false }: MetricCardProps) {
  return (
    <div className={`metric-card${accent ? ' metric-card-accent' : ''}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {hint ? <div className="metric-hint">{hint}</div> : null}
    </div>
  );
}
