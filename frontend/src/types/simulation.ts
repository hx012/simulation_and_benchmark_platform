export type SimulationMode = 'SINGLE_CHIP' | 'MULTI_CHIP';

export interface SimulationModeCapability {
  key: SimulationMode;
  label: string;
}

export interface ChipVariantCapability {
  key: string;
  label: string;
  modes: SimulationModeCapability[];
}

export interface SimulatorCapability {
  key: string;
  label: string;
  variants: ChipVariantCapability[];
}

export interface SimulationCapabilitiesResponse {
  simulators: SimulatorCapability[];
}

export type TaskStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'TERMINATED';

export type ExecutionPhase =
  | 'WAITING'
  | 'PREPARING'
  | 'STARTING'
  | 'EXECUTING'
  | 'COLLECTING'
  | 'FINISHED';

export type TraceStatus =
  | 'NOT_REQUESTED'
  | 'PENDING'
  | 'GENERATING'
  | 'READY'
  | 'FAILED';

export type UploadSessionStatus =
  | 'UPLOADING'
  | 'READY'
  | 'VALIDATING'
  | 'INVALID'
  | 'COMMITTING'
  | 'SUBMITTED'
  | 'EXPIRED';

export type UploadPackageType = 'chip_config' | 'workload';

export interface SimulationTask {
  task_id: string;
  task_name: string;
  owner_id: string;
  simulator_version: string;
  simulator_label?: string | null;
  chip_variant: string | null;
  chip_variant_label?: string | null;
  simulation_mode: SimulationMode;
  simulation_mode_label?: string | null;
  rerun_from_task_id: string | null;
  status: TaskStatus;
  execution_phase: ExecutionPhase;
  current_cycle: number | null;
  total_cycle: number | null;
  simulated_time_seconds: number | null;
  runtime_seconds: number | null;
  trace_status: TraceStatus;
  exit_code: number | null;
  cancel_requested: boolean;
  terminate_requested: boolean;
  error_code: string | null;
  error_message: string | null;
  archived: boolean;
  archived_at: string | null;
  submit_time: string | null;
  start_time: string | null;
  end_time: string | null;
}

export interface SimulationTaskListResponse {
  items: SimulationTask[];
  total: number;
  page: number;
  page_size: number;
}

export interface SimulationQueueResponse {
  task_id: string;
  status: TaskStatus;
  queued_ahead: number;
}

export interface SimulationTaskQuotaResponse {
  owner_id: string;
  limit: number;
  retained_count: number;
  reserved_count: number;
  used_count: number;
  remaining: number;
  can_create: boolean;
}

export interface SimulationDeleteResponse {
  deleted_task_ids: string[];
  deleted_count: number;
}

export interface SimulationQueuedTaskResponse {
  task: SimulationTask;
  queued_ahead: number;
}

export interface SimulationLogResponse {
  task_id: string;
  available: boolean;
  offset: number;
  next_offset: number;
  eof: boolean;
  reset: boolean;
  text: string;
}

export interface SimulationResultResponse {
  task_id: string;
  status: TaskStatus;
  execution_phase: ExecutionPhase;
  current_cycle: number | null;
  total_cycle: number | null;
  simulated_time_seconds: number | null;
  runtime_seconds: number | null;
  exit_code: number | null;
  trace_status: TraceStatus;
  trace_available: boolean;
  trace_source_available: boolean;
  trace_viewer_available: boolean;
  summary_available: boolean;
  summary: Record<string, unknown> | null;
  summary_error: string | null;
  error_code: string | null;
  error_message: string | null;
  submit_time: string | null;
  start_time: string | null;
  end_time: string | null;
}

export interface TraceEvent {
  name?: string;
  ph?: string;
  pid?: number | string;
  tid?: number | string;
  ts?: number;
  dur?: number;
  args?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface SimulationTraceResponse {
  task_id: string;
  event_count: number;
  events: TraceEvent[];
}

export interface UploadSession {
  upload_session_id: string;
  owner_id: string;
  status: UploadSessionStatus;
  submitted_task_id: string | null;
  created_at: string;
  last_activity_at: string;
}

export interface UploadValidationResponse {
  upload_session_id: string;
  status: UploadSessionStatus;
  valid: boolean;
  errors: string[];
}

export interface UploadFilesResponse {
  upload_session_id: string;
  package_type: string;
  uploaded_files: number;
  status: UploadSessionStatus;
}

export interface ApplySimulationSampleResponse {
  upload_session_id: string;
  simulator_version: string;
  chip_variant: string | null;
  simulation_mode: SimulationMode;
  status: UploadSessionStatus;
  chip_config_files: number;
  workload_files: number;
}

export interface UploadFileInfo {
  path: string;
  name: string;
  size_bytes: number;
  editable: boolean;
}

export interface UploadFileListResponse {
  upload_session_id: string;
  package_type: UploadPackageType;
  files: UploadFileInfo[];
}

export interface UploadFileContentResponse {
  upload_session_id: string;
  package_type: UploadPackageType;
  path: string;
  name: string;
  size_bytes: number;
  editable: boolean;
  content: string | null;
}

export interface UploadFileContentUpdateResponse {
  upload_session_id: string;
  package_type: UploadPackageType;
  path: string;
  size_bytes: number;
  status: UploadSessionStatus;
}

export interface SimulationSubmitRequest {
  task_name: string;
  simulator_version: string;
  chip_variant: string | null;
  simulation_mode: SimulationMode;
}

export interface SimulationSubmitResponse {
  upload_session_id: string;
  task: SimulationTask;
  queued_ahead: number;
}

export interface LocalFileEntry {
  file: File;
  relativePath: string;
}
