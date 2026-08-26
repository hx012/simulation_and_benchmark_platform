import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { trackAnalyticsEventQuietly } from '../api/analytics';

interface PageContext {
  page_key: string;
  vendor?: string;
  chip?: string;
  benchmark_name?: string;
}

let lastPageViewKey = '';
let lastPageViewAt = 0;

function decode(value: string | undefined) {
  if (!value) return undefined;
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function pageContext(pathname: string): PageContext {
  const benchmark = pathname.match(/^\/benchmark\/chips\/([^/]+)\/([^/]+)\/benchmarks\/([^/]+)$/);
  if (benchmark) {
    return {
      page_key: 'benchmark.detail',
      vendor: decode(benchmark[1]),
      chip: decode(benchmark[2]),
      benchmark_name: decode(benchmark[3]),
    };
  }
  const chip = pathname.match(/^\/benchmark\/chips\/([^/]+)\/([^/]+)$/);
  if (chip) {
    return { page_key: 'benchmark.chip', vendor: decode(chip[1]), chip: decode(chip[2]) };
  }
  if (/^\/simulation\/tasks\/[^/]+\/result$/.test(pathname)) return { page_key: 'simulation.task_result' };
  if (/^\/simulation\/tasks\/[^/]+$/.test(pathname)) return { page_key: 'simulation.task_detail' };
  if (pathname === '/simulation/tasks') return { page_key: 'simulation.tasks' };
  if (pathname === '/simulation/new') return { page_key: 'simulation.create' };
  if (pathname === '/benchmark') return { page_key: 'benchmark.browse' };
  if (pathname === '/performance') return { page_key: 'performance.workspace' };
  if (pathname === '/team') return { page_key: 'team' };
  if (pathname === '/demands') return { page_key: 'demands' };
  if (pathname === '/permissions') return { page_key: 'permissions' };
  if (pathname === '/usage-analytics') return { page_key: 'analytics.usage' };
  return { page_key: pathname === '/home' ? 'home' : 'unknown' };
}

export function AnalyticsTracker() {
  const location = useLocation();

  useEffect(() => {
    const context = pageContext(location.pathname);
    const pageViewKey = `${location.pathname}|${context.page_key}`;
    const now = Date.now();
    if (pageViewKey !== lastPageViewKey || now - lastPageViewAt > 1_500) {
      lastPageViewKey = pageViewKey;
      lastPageViewAt = now;
      trackAnalyticsEventQuietly({ event_name: 'page_view', ...context });
      if (context.page_key === 'benchmark.chip') {
        trackAnalyticsEventQuietly({
          event_name: 'benchmark.chip_view',
          target_type: 'benchmark_chip',
          target_id: `${context.vendor}/${context.chip}`,
          target_name: context.chip,
          ...context,
        });
      }
    }

    let activeMilliseconds = 0;
    let lastTick = Date.now();
    let lastInteraction = lastTick;
    const isActive = () => (
      document.visibilityState === 'visible'
      && document.hasFocus()
      && Date.now() - lastInteraction < 5 * 60 * 1000
    );
    const accrue = () => {
      const now = Date.now();
      if (isActive()) activeMilliseconds += Math.min(now - lastTick, 30_000);
      lastTick = now;
    };
    const activity = () => {
      accrue();
      lastInteraction = Date.now();
    };
    const stateChange = () => accrue();
    const interval = window.setInterval(accrue, 15_000);
    const report = () => {
      accrue();
      const activeSeconds = Math.round(activeMilliseconds / 1000);
      activeMilliseconds = 0;
      if (activeSeconds > 0) {
        trackAnalyticsEventQuietly({
          event_name: 'page_active_time',
          active_seconds: activeSeconds,
          ...context,
        });
      }
    };
    const reportInterval = window.setInterval(report, 5 * 60_000);
    document.addEventListener('visibilitychange', stateChange);
    window.addEventListener('focus', stateChange);
    window.addEventListener('blur', stateChange);
    window.addEventListener('pointerdown', activity);
    window.addEventListener('keydown', activity);
    window.addEventListener('scroll', activity, true);
    window.addEventListener('pagehide', report);

    return () => {
      report();
      window.clearInterval(interval);
      window.clearInterval(reportInterval);
      document.removeEventListener('visibilitychange', stateChange);
      window.removeEventListener('focus', stateChange);
      window.removeEventListener('blur', stateChange);
      window.removeEventListener('pointerdown', activity);
      window.removeEventListener('keydown', activity);
      window.removeEventListener('scroll', activity, true);
      window.removeEventListener('pagehide', report);
    };
  }, [location.pathname]);

  return null;
}
