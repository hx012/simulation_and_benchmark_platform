from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.simulation.enums import (
    ExecutionPhase,
    SimulationMode,
    TaskStatus,
    TraceStatus,
    UploadSessionStatus,
)


class SimulationModeCapabilityResponse(BaseModel):
    key: SimulationMode
    label: str


class ChipVariantCapabilityResponse(BaseModel):
    key: str
    label: str
    modes: list[SimulationModeCapabilityResponse]


class SimulatorCapabilityResponse(BaseModel):
    key: str
    label: str
    variants: list[ChipVariantCapabilityResponse]


class SimulationCapabilitiesResponse(BaseModel):
    simulators: list[SimulatorCapabilityResponse]


class SimulationTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    task_name: str
    owner_id: str

    simulator_version: str
    simulator_label: str | None = None
    chip_variant: str | None
    chip_variant_label: str | None = None
    simulation_mode: SimulationMode
    simulation_mode_label: str | None = None
    rerun_from_task_id: str | None

    status: TaskStatus
    execution_phase: ExecutionPhase

    current_cycle: int | None
    total_cycle: int | None
    simulated_time_seconds: float | None
    runtime_seconds: float | None

    trace_status: TraceStatus
    exit_code: int | None

    cancel_requested: bool
    terminate_requested: bool

    error_code: str | None
    error_message: str | None

    archived: bool
    archived_at: datetime | None

    submit_time: datetime | None
    start_time: datetime | None
    end_time: datetime | None


class SimulationTaskListResponse(BaseModel):
    items: list[SimulationTaskResponse]
    total: int
    page: int
    page_size: int


class SimulationQueueResponse(BaseModel):
    task_id: str
    status: TaskStatus
    queued_ahead: int


class SimulationTaskQuotaResponse(BaseModel):
    owner_id: str
    limit: int
    retained_count: int
    reserved_count: int
    used_count: int
    remaining: int
    can_create: bool


class SimulationBatchDeleteRequest(BaseModel):
    owner_id: str = Field(min_length=1, max_length=128)
    task_ids: list[str] = Field(min_length=1, max_length=100)


class SimulationDeleteResponse(BaseModel):
    deleted_task_ids: list[str]
    deleted_count: int


class SimulationQueuedTaskResponse(BaseModel):
    task: SimulationTaskResponse
    queued_ahead: int


class SimulationRerunRequest(BaseModel):
    task_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )


class SimulationLogResponse(BaseModel):
    task_id: str
    available: bool
    offset: int
    next_offset: int
    eof: bool
    reset: bool
    text: str


class SimulationResultResponse(BaseModel):
    task_id: str
    status: TaskStatus
    execution_phase: ExecutionPhase

    current_cycle: int | None
    total_cycle: int | None
    simulated_time_seconds: float | None
    runtime_seconds: float | None
    exit_code: int | None

    trace_status: TraceStatus
    trace_available: bool
    summary_available: bool
    summary: dict[str, Any] | None
    summary_error: str | None

    error_code: str | None
    error_message: str | None

    submit_time: datetime | None
    start_time: datetime | None
    end_time: datetime | None


class SimulationTraceResponse(BaseModel):
    task_id: str
    event_count: int
    events: list[dict[str, Any]]


class UploadSessionCreateRequest(BaseModel):
    owner_id: str = Field(
        min_length=1,
        max_length=128,
    )


class UploadSessionResponse(BaseModel):
    upload_session_id: str
    owner_id: str
    status: UploadSessionStatus
    submitted_task_id: str | None
    created_at: datetime
    last_activity_at: datetime


class UploadFilesResponse(BaseModel):
    upload_session_id: str
    package_type: str
    uploaded_files: int
    status: UploadSessionStatus


class UploadValidationResponse(BaseModel):
    upload_session_id: str
    status: UploadSessionStatus
    valid: bool
    errors: list[str]


class ApplySimulationSampleRequest(BaseModel):
    simulator_version: str = Field(
        default="v310",
        min_length=1,
        max_length=64,
    )
    chip_variant: str | None = Field(
        default="default",
        max_length=64,
    )
    simulation_mode: SimulationMode = SimulationMode.SINGLE_CHIP


class ApplySimulationSampleResponse(BaseModel):
    upload_session_id: str
    simulator_version: str
    chip_variant: str | None
    simulation_mode: SimulationMode
    status: UploadSessionStatus
    chip_config_files: int
    workload_files: int


class UploadFileInfoResponse(BaseModel):
    path: str
    name: str
    size_bytes: int
    editable: bool


class UploadFileListResponse(BaseModel):
    upload_session_id: str
    package_type: Literal["chip_config", "workload"]
    files: list[UploadFileInfoResponse]


class UploadFileContentResponse(BaseModel):
    upload_session_id: str
    package_type: Literal["chip_config", "workload"]
    path: str
    name: str
    size_bytes: int
    editable: bool
    content: str | None


class UploadFileContentUpdateRequest(BaseModel):
    package_type: Literal["chip_config", "workload"]
    path: str = Field(min_length=1, max_length=2048)
    content: str


class UploadFileContentUpdateResponse(BaseModel):
    upload_session_id: str
    package_type: Literal["chip_config", "workload"]
    path: str
    size_bytes: int
    status: UploadSessionStatus


class SimulationSubmitRequest(BaseModel):
    task_name: str = Field(
        min_length=1,
        max_length=255,
    )
    simulator_version: str = Field(
        min_length=1,
        max_length=64,
    )
    chip_variant: str | None = Field(
        default=None,
        max_length=64,
    )
    simulation_mode: SimulationMode = SimulationMode.SINGLE_CHIP


class SimulationSubmitResponse(BaseModel):
    upload_session_id: str
    task: SimulationTaskResponse
    queued_ahead: int
