export type TraceProducer = 'mskpp' | 'esl';

export interface TraceTimeItem {
  name: string;
  cycles: number;
  ratio_percent: number;
}

export interface TraceTimeAnalysisResponse {
  data_type: 'trace';
  source: 'simulation_task' | 'local_file';
  source_name: string;
  task_id: string | null;
  producer: TraceProducer;
  unit: string;
  event_count: number;
  analyzed_event_count: number;
  skipped_event_count: number;
  sync_event_count: number;
  total_cycles: number;
  items: TraceTimeItem[];
  warnings: string[];
}
