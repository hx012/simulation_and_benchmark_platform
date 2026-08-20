import { useCallback, useEffect, useRef, useState } from 'react';
import { simulationApi } from '../api/simulation';
import type { SimulationTask } from '../types/simulation';
import { isTerminalStatus } from '../utils/format';

export function useTaskPolling(taskId: string | undefined, intervalMs = 2000) {
  const [task, setTask] = useState<SimulationTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const timerRef = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    if (!taskId) return;
    try {
      const next = await simulationApi.getTask(taskId);
      setTask(next);
      setError(null);
      return next;
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
      return null;
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      const next = await refresh();
      if (cancelled || !next || isTerminalStatus(next.status)) return;
      timerRef.current = window.setTimeout(tick, intervalMs);
    };

    setLoading(true);
    void tick();

    return () => {
      cancelled = true;
      if (timerRef.current != null) window.clearTimeout(timerRef.current);
    };
  }, [intervalMs, refresh]);

  return { task, loading, error, refresh };
}
