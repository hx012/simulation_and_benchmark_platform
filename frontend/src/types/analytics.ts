export interface AnalyticsEventPayload {
  event_name: string;
  page_key?: string;
  result?: string;
  active_seconds?: number;
  vendor?: string | null;
  chip?: string | null;
  benchmark_name?: string | null;
  benchmark_type?: string | null;
  test_target?: string | null;
  simulator_version?: string | null;
  chip_variant?: string | null;
  simulation_mode?: string | null;
  target_type?: string | null;
  target_id?: string | null;
  target_name?: string | null;
  target_user_id?: string | null;
  auth_mode?: string;
  change_summary?: string;
}

export interface AnalyticsSummary {
  active_users: number;
  visits: number;
  page_views: number;
  active_seconds: number;
  simulation_tasks: number;
  demand_feedback: number;
}

export interface AnalyticsTrendPoint {
  date: string;
  active_users: number;
  visits: number;
  page_views: number;
}

export interface AnalyticsRankingItem {
  key: string;
  label: string;
  users: number;
  count: number;
  active_seconds: number;
  last_active_at: string | null;
  vendor: string | null;
  chip: string | null;
  benchmark_name: string | null;
  benchmark_type: string | null;
  test_target: string | null;
}

export interface AnalyticsSimulationDimensionItem {
  key: string;
  label: string;
  users: number;
  tasks: number;
  success_rate: number;
  simulator_version: string | null;
  chip_variant: string | null;
  simulation_mode: string | null;
}

export interface AnalyticsDemandStatusItem {
  status: string;
  label: string;
  count: number;
}

export interface AnalyticsDemandPipeline {
  submitted: number;
  accepted: number;
  accepted_unplanned: number;
  planned: number;
  in_progress: number;
  delivered: number;
  statuses: AnalyticsDemandStatusItem[];
}

export interface AnalyticsOverview {
  start_at: string;
  end_at: string;
  summary: AnalyticsSummary;
  trend: AnalyticsTrendPoint[];
  pages: AnalyticsRankingItem[];
  features: AnalyticsRankingItem[];
  chips: AnalyticsRankingItem[];
  benchmarks: AnalyticsRankingItem[];
  simulation_dimensions: AnalyticsSimulationDimensionItem[];
  demand_pipeline: AnalyticsDemandPipeline;
}

export type AnalyticsUserSort =
  | 'last_active_at'
  | 'active_days'
  | 'visits'
  | 'page_views'
  | 'active_seconds'
  | 'simulation_tasks'
  | 'demand_feedback';

export interface AnalyticsUserItem {
  user_id: string;
  display_name: string;
  role: string;
  last_active_at: string | null;
  active_days: number;
  visits: number;
  page_views: number;
  active_seconds: number;
  simulation_tasks: number;
  demand_feedback: number;
  top_page: string | null;
  top_chip: string | null;
  top_benchmark: string | null;
}

export interface AnalyticsUserList {
  items: AnalyticsUserItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AnalyticsUserDetail {
  user: AnalyticsUserItem;
  pages: Array<{
    page_key: string;
    label: string;
    page_views: number;
    active_seconds: number;
    last_active_at: string | null;
  }>;
  recent_events: Array<{
    event_name: string;
    label: string;
    page_key: string;
    occurred_at: string;
    vendor: string | null;
    chip: string | null;
    benchmark_name: string | null;
    simulator_version: string | null;
    chip_variant: string | null;
    target_type: string | null;
    target_id: string | null;
    target_name: string | null;
    target_user_id: string | null;
    auth_mode: string;
    change_summary: string;
  }>;
}
