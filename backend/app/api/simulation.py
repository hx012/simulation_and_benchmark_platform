from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.common.config import get_settings
from app.common.database import get_db
from app.simulation.enums import TaskStatus
from app.simulation.exceptions import (
    InvalidTaskStateError,
    InvalidUploadSessionStateError,
    TaskIOError,
    TaskNotFoundError,
    TaskQuotaExceededError,
    TaskSubmissionError,
    TaskWorkspaceError,
    UploadSessionNotFoundError,
)
from app.simulation.repository import SimulationRepository
from app.simulation.sample_service import SimulationSampleService
from app.simulation.schemas import (
    ApplySimulationSampleRequest,
    ApplySimulationSampleResponse,
    SimulationCapabilitiesResponse,
    SimulatorCapabilityResponse,
    ChipVariantCapabilityResponse,
    SimulationModeCapabilityResponse,
    SimulationLogResponse,
    SimulationQueueResponse,
    SimulationQueuedTaskResponse,
    SimulationRerunRequest,
    SimulationResultResponse,
    SimulationTraceResponse,
    SimulationSubmitRequest,
    SimulationSubmitResponse,
    SimulationTaskListResponse,
    SimulationTaskQuotaResponse,
    SimulationBatchDeleteRequest,
    SimulationDeleteResponse,
    SimulationTaskResponse,
    UploadFileContentResponse,
    UploadFileContentUpdateRequest,
    UploadFileContentUpdateResponse,
    UploadFileInfoResponse,
    UploadFileListResponse,
    UploadFilesResponse,
    UploadSessionCreateRequest,
    UploadSessionResponse,
    UploadValidationResponse,
)
from app.simulation.simulator.profiles import (
    SimulatorProfileNotFoundError,
    SimulatorProfileRegistry,
)
from app.simulation.submission_service import SimulationSubmissionService
from app.simulation.task_io_service import SimulationTaskIOService
from app.simulation.task_management_service import SimulationTaskManagementService
from app.simulation.task_service import SimulationTaskService
from app.simulation.upload_repository import UploadSessionRepository
from app.simulation.upload_file_service import UploadSessionFileService
from app.simulation.upload_service import UploadSessionService
from app.simulation.upload_validator import UploadSessionValidator
from app.simulation.workspace_manager import TaskWorkspaceManager


BACKEND_ROOT = Path(__file__).resolve().parents[2]

router = APIRouter(
    prefix="/api/simulation",
    tags=["simulation"],
)

settings = get_settings()

repository = SimulationRepository()
task_service = SimulationTaskService(repository=repository)

upload_repository = UploadSessionRepository()
upload_service = UploadSessionService(
    settings=settings,
    repository=upload_repository,
    simulation_repository=repository,
)
upload_validator = UploadSessionValidator()
sample_service = SimulationSampleService(
    settings=settings,
    upload_repository=upload_repository,
)
upload_file_service = UploadSessionFileService(
    settings=settings,
    upload_repository=upload_repository,
)

profile_registry = SimulatorProfileRegistry(
    BACKEND_ROOT
    / "config"
    / "simulator_profiles.yml"
)
workspace_manager = TaskWorkspaceManager(settings)
task_management_service = SimulationTaskManagementService(
    settings=settings,
    simulation_repository=repository,
    upload_repository=upload_repository,
    workspace_manager=workspace_manager,
)
submission_service = SimulationSubmissionService(
    settings=settings,
    simulation_repository=repository,
    upload_repository=upload_repository,
    workspace_manager=workspace_manager,
    profile_registry=profile_registry,
)

task_io_service = SimulationTaskIOService(settings)


def _task_response(task) -> SimulationTaskResponse:
    response = SimulationTaskResponse.model_validate(task)
    try:
        profile = profile_registry.get_profile(
            simulator_version=task.simulator_version,
            chip_variant=task.chip_variant,
            simulation_mode=task.simulation_mode,
        )
        return response.model_copy(
            update={
                "simulator_label": profile.simulator_label,
                "chip_variant_label": profile.chip_variant_label,
                "simulation_mode_label": profile.simulation_mode_label,
            }
        )
    except SimulatorProfileNotFoundError:
        return response.model_copy(
            update={
                "simulator_label": task.simulator_version,
                "chip_variant_label": task.chip_variant or "默认",
                "simulation_mode_label": task.simulation_mode.value,
            }
        )


def _upload_session_response(upload_session) -> UploadSessionResponse:
    return UploadSessionResponse(
        upload_session_id=upload_session.upload_session_id,
        owner_id=upload_session.owner_id,
        status=upload_session.status,
        submitted_task_id=upload_session.submitted_task_id,
        created_at=upload_session.created_at,
        last_activity_at=upload_session.last_activity_at,
    )


@router.get(
    "/capabilities",
    response_model=SimulationCapabilitiesResponse,
)
def get_simulation_capabilities() -> SimulationCapabilitiesResponse:
    return SimulationCapabilitiesResponse(
        simulators=[
            SimulatorCapabilityResponse(
                key=simulator.key,
                label=simulator.label,
                variants=[
                    ChipVariantCapabilityResponse(
                        key=variant.key,
                        label=variant.label,
                        modes=[
                            SimulationModeCapabilityResponse(
                                key=mode.key,
                                label=mode.label,
                            )
                            for mode in variant.modes
                        ],
                    )
                    for variant in simulator.variants
                ],
            )
            for simulator in profile_registry.get_capabilities()
        ]
    )


def _raise_task_http_error(exc: Exception) -> None:
    if isinstance(exc, TaskNotFoundError):
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if isinstance(exc, InvalidTaskStateError):
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    raise exc


def _raise_upload_http_error(exc: Exception) -> None:
    if isinstance(exc, UploadSessionNotFoundError):
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if isinstance(exc, InvalidUploadSessionStateError):
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    if isinstance(exc, TaskQuotaExceededError):
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    if isinstance(
        exc,
        (
            TaskSubmissionError,
            TaskWorkspaceError,
            SimulatorProfileNotFoundError,
            ValueError,
        ),
    ):
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    raise exc


def _upload_package(
    *,
    upload_session_id: str,
    package_type: str,
    files: list[UploadFile],
    relative_paths: list[str],
    db: Session,
) -> UploadFilesResponse:
    try:
        uploaded_count = upload_service.upload_files(
            db=db,
            upload_session_id=upload_session_id,
            package_type=package_type,
            files=files,
            relative_paths=relative_paths,
        )
        db.commit()

    except Exception as exc:
        db.rollback()
        _raise_upload_http_error(exc)
        raise

    upload_session = upload_repository.get(
        db,
        upload_session_id,
    )

    if upload_session is None:
        raise HTTPException(
            status_code=404,
            detail="Upload session not found",
        )

    return UploadFilesResponse(
        upload_session_id=upload_session.upload_session_id,
        package_type=package_type,
        uploaded_files=uploaded_count,
        status=upload_session.status,
    )


@router.get(
    "/tasks",
    response_model=SimulationTaskListResponse,
)
def list_simulation_tasks(
    owner_id: str | None = None,
    status: TaskStatus | None = None,
    archived: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SimulationTaskListResponse:
    offset = (page - 1) * page_size

    tasks = repository.list_tasks(
        db,
        owner_id=owner_id,
        status=status,
        archived=archived,
        offset=offset,
        limit=page_size,
    )

    total = repository.count_tasks(
        db,
        owner_id=owner_id,
        status=status,
        archived=archived,
    )

    return SimulationTaskListResponse(
        items=[
            _task_response(task)
            for task in tasks
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/tasks/quota",
    response_model=SimulationTaskQuotaResponse,
)
def get_simulation_task_quota(
    owner_id: str = Query(min_length=1, max_length=128),
    db: Session = Depends(get_db),
) -> SimulationTaskQuotaResponse:
    quota = task_management_service.get_quota(db, owner_id)
    return SimulationTaskQuotaResponse(
        owner_id=quota.owner_id,
        limit=quota.limit,
        retained_count=quota.retained_count,
        reserved_count=quota.reserved_count,
        used_count=quota.used_count,
        remaining=quota.remaining,
        can_create=quota.can_create,
    )


@router.post(
    "/tasks/batch-delete",
    response_model=SimulationDeleteResponse,
)
def batch_delete_simulation_tasks(
    request: SimulationBatchDeleteRequest,
    db: Session = Depends(get_db),
) -> SimulationDeleteResponse:
    try:
        deleted = task_management_service.delete_tasks(
            db,
            owner_id=request.owner_id,
            task_ids=request.task_ids,
        )
    except Exception as exc:
        _raise_task_http_error(exc)
        raise

    return SimulationDeleteResponse(
        deleted_task_ids=deleted,
        deleted_count=len(deleted),
    )


@router.get(
    "/tasks/{task_id}",
    response_model=SimulationTaskResponse,
)
def get_simulation_task(
    task_id: str,
    db: Session = Depends(get_db),
) -> SimulationTaskResponse:
    try:
        task = task_service.get_task(db, task_id)
    except Exception as exc:
        _raise_task_http_error(exc)
        raise

    return _task_response(task)


@router.delete(
    "/tasks/{task_id}",
    response_model=SimulationDeleteResponse,
)
def delete_simulation_task(
    task_id: str,
    owner_id: str = Query(min_length=1, max_length=128),
    db: Session = Depends(get_db),
) -> SimulationDeleteResponse:
    try:
        deleted = task_management_service.delete_task(
            db,
            owner_id=owner_id,
            task_id=task_id,
        )
    except Exception as exc:
        _raise_task_http_error(exc)
        raise

    return SimulationDeleteResponse(
        deleted_task_ids=deleted,
        deleted_count=len(deleted),
    )


@router.get(
    "/tasks/{task_id}/queue",
    response_model=SimulationQueueResponse,
)
def get_simulation_queue(
    task_id: str,
    db: Session = Depends(get_db),
) -> SimulationQueueResponse:
    try:
        task = task_service.get_task(db, task_id)
        queued_ahead = task_service.get_queue_ahead(
            db,
            task_id,
        )
    except Exception as exc:
        _raise_task_http_error(exc)
        raise

    return SimulationQueueResponse(
        task_id=task.task_id,
        status=task.status,
        queued_ahead=queued_ahead,
    )


@router.get(
    "/tasks/{task_id}/logs",
    response_model=SimulationLogResponse,
)
def get_simulation_log(
    task_id: str,
    offset: int = Query(default=0, ge=0),
    limit_bytes: int = Query(
        default=64 * 1024,
        ge=1,
    ),
    db: Session = Depends(get_db),
) -> SimulationLogResponse:
    try:
        task = task_service.get_task(db, task_id)
        chunk = task_io_service.read_log(
            task,
            offset=offset,
            limit_bytes=limit_bytes,
        )
    except TaskIOError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _raise_task_http_error(exc)
        raise

    return SimulationLogResponse(
        task_id=task_id,
        available=chunk.available,
        offset=chunk.offset,
        next_offset=chunk.next_offset,
        eof=chunk.eof,
        reset=chunk.reset,
        text=chunk.text,
    )


@router.get(
    "/tasks/{task_id}/result",
    response_model=SimulationResultResponse,
)
def get_simulation_result(
    task_id: str,
    db: Session = Depends(get_db),
) -> SimulationResultResponse:
    try:
        task = task_service.get_task(db, task_id)
        artifacts = task_io_service.read_result_artifacts(task)
    except TaskIOError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _raise_task_http_error(exc)
        raise

    return SimulationResultResponse(
        task_id=task.task_id,
        status=task.status,
        execution_phase=task.execution_phase,
        current_cycle=task.current_cycle,
        total_cycle=task.total_cycle,
        simulated_time_seconds=task.simulated_time_seconds,
        runtime_seconds=task.runtime_seconds,
        exit_code=task.exit_code,
        trace_status=task.trace_status,
        trace_available=artifacts.trace_available,
        summary_available=artifacts.summary_available,
        summary=artifacts.summary,
        summary_error=artifacts.summary_error,
        error_code=task.error_code,
        error_message=task.error_message,
        submit_time=task.submit_time,
        start_time=task.start_time,
        end_time=task.end_time,
    )


@router.get(
    "/tasks/{task_id}/trace",
    response_model=SimulationTraceResponse,
)
def get_simulation_trace(
    task_id: str,
    db: Session = Depends(get_db),
) -> SimulationTraceResponse:
    try:
        task = task_service.get_task(db, task_id)
        events = task_io_service.read_trace_events(task)
    except TaskIOError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _raise_task_http_error(exc)
        raise

    return SimulationTraceResponse(
        task_id=task_id,
        event_count=len(events),
        events=events,
    )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=SimulationTaskResponse,
)
def cancel_simulation_task(
    task_id: str,
    db: Session = Depends(get_db),
) -> SimulationTaskResponse:
    try:
        task = task_service.request_cancel(db, task_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_task_http_error(exc)
        raise

    return _task_response(task)


@router.post(
    "/tasks/{task_id}/terminate",
    response_model=SimulationTaskResponse,
)
def terminate_simulation_task(
    task_id: str,
    db: Session = Depends(get_db),
) -> SimulationTaskResponse:
    try:
        task = task_service.request_terminate(db, task_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_task_http_error(exc)
        raise

    return _task_response(task)


@router.post(
    "/tasks/{task_id}/archive",
    response_model=SimulationTaskResponse,
)
def archive_simulation_task(
    task_id: str,
    db: Session = Depends(get_db),
) -> SimulationTaskResponse:
    try:
        task = task_service.archive_task(db, task_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_task_http_error(exc)
        raise

    return _task_response(task)


@router.post(
    "/tasks/{task_id}/unarchive",
    response_model=SimulationTaskResponse,
)
def unarchive_simulation_task(
    task_id: str,
    db: Session = Depends(get_db),
) -> SimulationTaskResponse:
    try:
        task = task_service.unarchive_task(db, task_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_task_http_error(exc)
        raise

    return _task_response(task)


@router.post(
    "/tasks/{task_id}/rerun",
    response_model=SimulationQueuedTaskResponse,
    status_code=201,
)
def rerun_simulation_task(
    task_id: str,
    request: SimulationRerunRequest,
    db: Session = Depends(get_db),
) -> SimulationQueuedTaskResponse:
    try:
        task = submission_service.rerun_task(
            db,
            source_task_id=task_id,
            task_name=request.task_name,
        )
        queued_ahead = task_service.get_queue_ahead(
            db,
            task.task_id,
        )
    except Exception as exc:
        db.rollback()
        if isinstance(exc, TaskQuotaExceededError):
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc
        if isinstance(exc, (TaskWorkspaceError, TaskSubmissionError)):
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        _raise_task_http_error(exc)
        raise

    return SimulationQueuedTaskResponse(
        task=_task_response(task),
        queued_ahead=queued_ahead,
    )


@router.post(
    "/upload-sessions",
    response_model=UploadSessionResponse,
    status_code=201,
)
def create_upload_session(
    request: UploadSessionCreateRequest,
    db: Session = Depends(get_db),
) -> UploadSessionResponse:
    upload_session = upload_service.create_session(
        db,
        owner_id=request.owner_id,
    )

    db.commit()
    db.refresh(upload_session)
    return _upload_session_response(upload_session)


@router.get(
    "/upload-sessions/{upload_session_id}",
    response_model=UploadSessionResponse,
)
def get_upload_session(
    upload_session_id: str,
    db: Session = Depends(get_db),
) -> UploadSessionResponse:
    try:
        upload_session = upload_service.get_session(
            db,
            upload_session_id,
        )
    except Exception as exc:
        _raise_upload_http_error(exc)
        raise

    return _upload_session_response(upload_session)


@router.put(
    "/upload-sessions/{upload_session_id}/chip-config",
    response_model=UploadFilesResponse,
)
def upload_chip_config(
    upload_session_id: str,
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    db: Session = Depends(get_db),
) -> UploadFilesResponse:
    return _upload_package(
        upload_session_id=upload_session_id,
        package_type="chip_config",
        files=files,
        relative_paths=relative_paths,
        db=db,
    )


@router.put(
    "/upload-sessions/{upload_session_id}/workload",
    response_model=UploadFilesResponse,
)
def upload_workload(
    upload_session_id: str,
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    db: Session = Depends(get_db),
) -> UploadFilesResponse:
    return _upload_package(
        upload_session_id=upload_session_id,
        package_type="workload",
        files=files,
        relative_paths=relative_paths,
        db=db,
    )


@router.post(
    "/upload-sessions/{upload_session_id}/apply-sample",
    response_model=ApplySimulationSampleResponse,
)
def apply_simulation_sample(
    upload_session_id: str,
    request: ApplySimulationSampleRequest,
    db: Session = Depends(get_db),
) -> ApplySimulationSampleResponse:
    try:
        # Validate the selected capability tuple before looking up a sample.
        profile_registry.get_profile(
            simulator_version=request.simulator_version,
            chip_variant=request.chip_variant,
            simulation_mode=request.simulation_mode,
        )
        chip_count, workload_count = sample_service.apply_sample(
            db,
            upload_session_id=upload_session_id,
            simulator_version=request.simulator_version,
            chip_variant=request.chip_variant,
            simulation_mode=request.simulation_mode,
        )
        upload_session = upload_service.get_session(
            db,
            upload_session_id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_upload_http_error(exc)
        raise

    return ApplySimulationSampleResponse(
        upload_session_id=upload_session_id,
        simulator_version=request.simulator_version,
        chip_variant=request.chip_variant,
        simulation_mode=request.simulation_mode,
        status=upload_session.status,
        chip_config_files=chip_count,
        workload_files=workload_count,
    )


@router.get(
    "/upload-sessions/{upload_session_id}/files",
    response_model=UploadFileListResponse,
)
def list_upload_session_files(
    upload_session_id: str,
    package_type: str = Query(..., pattern="^(chip_config|workload)$"),
    db: Session = Depends(get_db),
) -> UploadFileListResponse:
    try:
        files = upload_file_service.list_files(
            db,
            upload_session_id=upload_session_id,
            package_type=package_type,
        )
    except Exception as exc:
        _raise_upload_http_error(exc)
        raise

    return UploadFileListResponse(
        upload_session_id=upload_session_id,
        package_type=package_type,
        files=[
            UploadFileInfoResponse(
                path=item.path,
                name=item.name,
                size_bytes=item.size_bytes,
                editable=item.editable,
            )
            for item in files
        ],
    )


@router.get(
    "/upload-sessions/{upload_session_id}/files/content",
    response_model=UploadFileContentResponse,
)
def get_upload_session_file_content(
    upload_session_id: str,
    package_type: str = Query(..., pattern="^(chip_config|workload)$"),
    path: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> UploadFileContentResponse:
    try:
        info, content = upload_file_service.read_content(
            db,
            upload_session_id=upload_session_id,
            package_type=package_type,
            relative_path=path,
        )
    except Exception as exc:
        _raise_upload_http_error(exc)
        raise

    return UploadFileContentResponse(
        upload_session_id=upload_session_id,
        package_type=package_type,
        path=info.path,
        name=info.name,
        size_bytes=info.size_bytes,
        editable=info.editable,
        content=content,
    )


@router.put(
    "/upload-sessions/{upload_session_id}/files/content",
    response_model=UploadFileContentUpdateResponse,
)
def update_upload_session_file_content(
    upload_session_id: str,
    request: UploadFileContentUpdateRequest,
    db: Session = Depends(get_db),
) -> UploadFileContentUpdateResponse:
    try:
        info = upload_file_service.write_content(
            db,
            upload_session_id=upload_session_id,
            package_type=request.package_type,
            relative_path=request.path,
            content=request.content,
        )
        upload_session = upload_service.get_session(
            db,
            upload_session_id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_upload_http_error(exc)
        raise

    return UploadFileContentUpdateResponse(
        upload_session_id=upload_session_id,
        package_type=request.package_type,
        path=info.path,
        size_bytes=info.size_bytes,
        status=upload_session.status,
    )


@router.post(
    "/upload-sessions/{upload_session_id}/validate",
    response_model=UploadValidationResponse,
)
def validate_upload_session(
    upload_session_id: str,
    db: Session = Depends(get_db),
) -> UploadValidationResponse:
    try:
        upload_session = upload_service.get_session(
            db,
            upload_session_id,
        )

        upload_service.begin_validation(
            db,
            upload_session_id,
        )
        db.commit()

        validation_result = upload_validator.validate(
            upload_session.temp_path
        )

        upload_session = upload_service.finish_validation(
            db,
            upload_session_id,
            valid=validation_result.valid,
        )
        db.commit()

    except Exception as exc:
        db.rollback()
        _raise_upload_http_error(exc)
        raise

    return UploadValidationResponse(
        upload_session_id=upload_session.upload_session_id,
        status=upload_session.status,
        valid=validation_result.valid,
        errors=validation_result.errors,
    )


@router.post(
    "/upload-sessions/{upload_session_id}/submit",
    response_model=SimulationSubmitResponse,
    status_code=201,
)
def submit_upload_session(
    upload_session_id: str,
    request: SimulationSubmitRequest,
    db: Session = Depends(get_db),
) -> SimulationSubmitResponse:
    try:
        task = submission_service.submit_upload(
            db,
            upload_session_id=upload_session_id,
            task_name=request.task_name,
            simulator_version=request.simulator_version,
            chip_variant=request.chip_variant,
            simulation_mode=request.simulation_mode,
        )

        queued_ahead = task_service.get_queue_ahead(
            db,
            task.task_id,
        )

    except Exception as exc:
        db.rollback()
        _raise_upload_http_error(exc)
        raise

    return SimulationSubmitResponse(
        upload_session_id=upload_session_id,
        task=_task_response(task),
        queued_ahead=queued_ahead,
    )
