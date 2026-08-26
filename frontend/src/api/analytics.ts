import { readStoredUser } from '../auth/storage';
import type {
  AnalyticsEventPayload,
  AnalyticsOverview,
  AnalyticsUserDetail,
  AnalyticsUserList,
  AnalyticsUserSort,
} from '../types/analytics';
import { apiRequest } from './client';

const SESSION_KEY = 'ai-chip-platform.analytics-session.v1';
const SESSION_IDLE_MS = 30 * 60 * 1000;

interface StoredAnalyticsSession {
  id: string;
  userId: string;
  lastActiveAt: number;
}

function newId() {
  return globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(16).slice(2)}-${Math.random().toString(16).slice(2)}`;
}

function analyticsSessionId(): string {
  const now = Date.now();
  const userId = readStoredUser()?.userId || '';
  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    const stored = raw ? JSON.parse(raw) as StoredAnalyticsSession : null;
    if (
      stored?.id
      && stored.userId === userId
      && now - stored.lastActiveAt < SESSION_IDLE_MS
    ) {
      stored.lastActiveAt = now;
      window.localStorage.setItem(SESSION_KEY, JSON.stringify(stored));
      return stored.id;
    }
    const next = { id: newId(), userId, lastActiveAt: now };
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(next));
    return next.id;
  } catch {
    return newId();
  }
}

export function trackAnalyticsEvent(payload: AnalyticsEventPayload) {
  return apiRequest<{ accepted: boolean }>('/api/analytics/events', {
    method: 'POST',
    keepalive: true,
    body: JSON.stringify({
      event_id: newId(),
      session_id: analyticsSessionId(),
      ...payload,
    }),
  });
}

export function trackAnalyticsEventQuietly(payload: AnalyticsEventPayload) {
  void trackAnalyticsEvent(payload).catch(() => undefined);
}

export const analyticsApi = {
  getOverview(days: number) {
    return apiRequest<AnalyticsOverview>('/api/admin/analytics/overview', {}, { days });
  },

  listUsers(params: {
    days: number;
    search?: string;
    sortBy: AnalyticsUserSort;
    sortOrder: 'asc' | 'desc';
    page: number;
    pageSize: number;
  }) {
    return apiRequest<AnalyticsUserList>('/api/admin/analytics/users', {}, {
      days: params.days,
      search: params.search,
      sort_by: params.sortBy,
      sort_order: params.sortOrder,
      page: params.page,
      page_size: params.pageSize,
    });
  },

  getUserDetail(userId: string, days: number) {
    return apiRequest<AnalyticsUserDetail>(
      `/api/admin/analytics/users/${encodeURIComponent(userId)}`,
      {},
      { days },
    );
  },
};
