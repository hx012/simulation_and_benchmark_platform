export interface BenchmarkStatus {
  registry_available: boolean;
  results_available: boolean;
}

export interface ChipSummary {
  vendor: string;
  chip: string;
}

export interface ChipListResponse {
  items: ChipSummary[];
  total: number;
}

export interface ChipDetail extends ChipSummary {
  benchmark_dir: string;
  benchmark_registry: string;
  benchmark_count: number;
}

export interface BenchmarkDefinition {
  benchmark_id: string;
  vendor: string;
  chip: string;
  name: string;
  module: string;
  class_name: string;
  description: string;
  category: string | null;
  target: string | null;
}

export interface BenchmarkListResponse {
  vendor: string;
  chip: string;
  items: BenchmarkDefinition[];
  total: number;
}

export interface BenchmarkResultListResponse {
  vendor: string;
  chip: string;
  benchmark_name: string;
  configured: boolean;
  items: Record<string, unknown>[];
  total: number;
}
