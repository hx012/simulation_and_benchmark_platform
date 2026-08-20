import { apiRequest } from './client';
import type {
  BenchmarkDefinition,
  BenchmarkListResponse,
  BenchmarkResultListResponse,
  BenchmarkStatus,
  ChipDetail,
  ChipListResponse,
} from '../types/benchmark';

function segment(value: string) {
  return encodeURIComponent(value);
}

export const benchmarkApi = {
  getStatus() {
    return apiRequest<BenchmarkStatus>('/api/benchmark/status');
  },

  listChips() {
    return apiRequest<ChipListResponse>('/api/benchmark/chips');
  },

  getChip(vendor: string, chip: string) {
    return apiRequest<ChipDetail>(`/api/benchmark/chips/${segment(vendor)}/${segment(chip)}`);
  },

  listBenchmarks(vendor: string, chip: string) {
    return apiRequest<BenchmarkListResponse>(
      `/api/benchmark/chips/${segment(vendor)}/${segment(chip)}/benchmarks`,
    );
  },

  getBenchmark(vendor: string, chip: string, benchmarkName: string) {
    return apiRequest<BenchmarkDefinition>(
      `/api/benchmark/chips/${segment(vendor)}/${segment(chip)}/benchmarks/${segment(benchmarkName)}`,
    );
  },

  listResults(vendor: string, chip: string, benchmarkName: string) {
    return apiRequest<BenchmarkResultListResponse>(
      `/api/benchmark/chips/${segment(vendor)}/${segment(chip)}/benchmarks/${segment(benchmarkName)}/results`,
    );
  },
};
