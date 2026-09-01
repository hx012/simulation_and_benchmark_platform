import { apiDownload, apiRequest, apiResourceUrl } from './client';
import type {
  ApplySimulationSampleResponse,
  LocalFileEntry,
  SimulationCapabilitiesResponse,
  SimulationLogResponse,
  SimulationMode,
  SimulationQueueResponse,
  SimulationQueuedTaskResponse,
  SimulationResultResponse,
  SimulationSubmitRequest,
  SimulationSubmitResponse,
  SimulationTask,
  SimulationTaskListResponse,
  SimulationTaskQuotaResponse,
  SimulationDeleteResponse,
  SimulationTraceResponse,
  TaskStatus,
  UploadFileContentResponse,
  UploadFileContentUpdateResponse,
  UploadFileListResponse,
  UploadFilesResponse,
  UploadPackageType,
  UploadSession,
  UploadValidationResponse,
} from '../types/simulation';

const BASE = '/api/simulation';

export interface ListTasksParams {
  ownerId?: string;
  status?: TaskStatus;
  archived?: boolean;
  page?: number;
  pageSize?: number;
}

export const simulationApi = {
  getCapabilities() {
    return apiRequest<SimulationCapabilitiesResponse>(`${BASE}/capabilities`);
  },

  listTasks(params: ListTasksParams = {}) {
    return apiRequest<SimulationTaskListResponse>(`${BASE}/tasks`, {}, {
      owner_id: params.ownerId,
      status: params.status,
      archived: params.archived,
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
    });
  },

  getTaskQuota(ownerId: string) {
    return apiRequest<SimulationTaskQuotaResponse>(
      `${BASE}/tasks/quota`,
      {},
      { owner_id: ownerId },
    );
  },

  deleteTask(taskId: string, ownerId: string) {
    return apiRequest<SimulationDeleteResponse>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}`,
      { method: 'DELETE' },
      { owner_id: ownerId },
    );
  },

  batchDeleteTasks(ownerId: string, taskIds: string[]) {
    return apiRequest<SimulationDeleteResponse>(
      `${BASE}/tasks/batch-delete`,
      {
        method: 'POST',
        body: JSON.stringify({ owner_id: ownerId, task_ids: taskIds }),
      },
    );
  },

  getTask(taskId: string) {
    return apiRequest<SimulationTask>(`${BASE}/tasks/${encodeURIComponent(taskId)}`);
  },

  getQueue(taskId: string) {
    return apiRequest<SimulationQueueResponse>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/queue`,
    );
  },

  getLogs(taskId: string, offset = 0, limitBytes = 64 * 1024, tail = false) {
    return apiRequest<SimulationLogResponse>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/logs`,
      {},
      { offset, limit_bytes: limitBytes, tail: tail || undefined },
    );
  },

  getResult(taskId: string) {
    return apiRequest<SimulationResultResponse>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/result`,
    );
  },

  getTrace(taskId: string) {
    return apiRequest<SimulationTraceResponse>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/trace`,
    );
  },

  getTraceViewerUrl(taskId: string, revision?: number) {
    return apiResourceUrl(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/trace/viewer`,
      revision === undefined ? undefined : { revision },
    );
  },

  cancelTask(taskId: string) {
    return apiRequest<SimulationTask>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/cancel`,
      { method: 'POST' },
    );
  },

  terminateTask(taskId: string) {
    return apiRequest<SimulationTask>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/terminate`,
      { method: 'POST' },
    );
  },

  archiveTask(taskId: string) {
    return apiRequest<SimulationTask>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/archive`,
      { method: 'POST' },
    );
  },

  unarchiveTask(taskId: string) {
    return apiRequest<SimulationTask>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/unarchive`,
      { method: 'POST' },
    );
  },

  rerunTask(taskId: string, taskName?: string) {
    return apiRequest<SimulationQueuedTaskResponse>(
      `${BASE}/tasks/${encodeURIComponent(taskId)}/rerun`,
      {
        method: 'POST',
        body: JSON.stringify({ task_name: taskName || null }),
      },
    );
  },

  createUploadSession(ownerId: string, payload: {
    simulator_version: string;
    chip_variant: string | null;
    simulation_mode: SimulationMode;
  }) {
    return apiRequest<UploadSession>(`${BASE}/upload-sessions`, {
      method: 'POST',
      body: JSON.stringify({ owner_id: ownerId, ...payload }),
    });
  },

  getUploadSession(uploadSessionId: string) {
    return apiRequest<UploadSession>(
      `${BASE}/upload-sessions/${encodeURIComponent(uploadSessionId)}`,
    );
  },

  applySample(
    uploadSessionId: string,
    payload: {
      simulator_version: string;
      chip_variant: string | null;
      simulation_mode: SimulationMode;
    },
  ) {
    return apiRequest<ApplySimulationSampleResponse>(
      `${BASE}/upload-sessions/${encodeURIComponent(uploadSessionId)}/apply-sample`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    );
  },

  downloadConfigTemplate(payload: {
    simulator_version: string;
    chip_variant: string | null;
    simulation_mode: SimulationMode;
  }) {
    return apiDownload(`${BASE}/config-template`, {
      simulator_version: payload.simulator_version,
      chip_variant: payload.chip_variant,
      simulation_mode: payload.simulation_mode,
    });
  },

  uploadPackage(
    uploadSessionId: string,
    endpoint: 'chip-config' | 'workload',
    entries: LocalFileEntry[],
  ) {
    const formData = new FormData();
    entries.forEach(({ file, relativePath }) => {
      formData.append('files', file, file.name);
      formData.append('relative_paths', relativePath);
    });

    return apiRequest<UploadFilesResponse>(
      `${BASE}/upload-sessions/${encodeURIComponent(uploadSessionId)}/${endpoint}`,
      { method: 'PUT', body: formData },
    );
  },

  listUploadFiles(uploadSessionId: string, packageType: UploadPackageType) {
    return apiRequest<UploadFileListResponse>(
      `${BASE}/upload-sessions/${encodeURIComponent(uploadSessionId)}/files`,
      {},
      { package_type: packageType },
    );
  },

  getUploadFileContent(
    uploadSessionId: string,
    packageType: UploadPackageType,
    path: string,
  ) {
    return apiRequest<UploadFileContentResponse>(
      `${BASE}/upload-sessions/${encodeURIComponent(uploadSessionId)}/files/content`,
      {},
      { package_type: packageType, path },
    );
  },

  updateUploadFileContent(
    uploadSessionId: string,
    packageType: UploadPackageType,
    path: string,
    content: string,
  ) {
    return apiRequest<UploadFileContentUpdateResponse>(
      `${BASE}/upload-sessions/${encodeURIComponent(uploadSessionId)}/files/content`,
      {
        method: 'PUT',
        body: JSON.stringify({ package_type: packageType, path, content }),
      },
    );
  },

  validateUploadSession(uploadSessionId: string) {
    return apiRequest<UploadValidationResponse>(
      `${BASE}/upload-sessions/${encodeURIComponent(uploadSessionId)}/validate`,
      { method: 'POST' },
    );
  },

  submitUploadSession(uploadSessionId: string, payload: SimulationSubmitRequest) {
    return apiRequest<SimulationSubmitResponse>(
      `${BASE}/upload-sessions/${encodeURIComponent(uploadSessionId)}/submit`,
      { method: 'POST', body: JSON.stringify(payload) },
    );
  },
};

export const DEFAULT_SIMULATION_MODE: SimulationMode = 'SINGLE_CHIP';
