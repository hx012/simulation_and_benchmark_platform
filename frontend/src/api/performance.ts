import { apiRequest } from './client';
import type {
  TraceProducer,
  TraceTimeAnalysisResponse,
} from '../types/performance';

const BASE = '/api/performance';

export const performanceApi = {
  analyzeTaskTrace(taskId: string) {
    return apiRequest<TraceTimeAnalysisResponse>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/trace-time`,
    );
  },

  analyzeUploadedTrace(file: File, producer: TraceProducer) {
    const formData = new FormData();
    formData.append('producer', producer);
    formData.append('file', file, file.name);
    return apiRequest<TraceTimeAnalysisResponse>(`${BASE}/trace-time`, {
      method: 'POST',
      body: formData,
    });
  },
};
