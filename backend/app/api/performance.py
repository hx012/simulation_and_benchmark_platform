import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from chip_performance_analysis import (
    TraceAnalysisError,
    TraceProducer,
    analyze_trace,
    normalize_trace_json,
)

from app.auth.constants import PERFORMANCE_VIEW_RESOURCE
from app.auth.service import AuthenticatedUser, get_current_user, require_resource
from app.common.config import get_settings
from app.common.database import get_db
from app.performance.schemas import TraceTimeAnalysisResponse
from app.performance.service import trace_time_response
from app.simulation.exceptions import TaskIOError, TaskNotFoundError
from app.simulation.access_control import require_task_read_access
from app.simulation.repository import SimulationRepository
from app.simulation.task_io_service import SimulationTaskIOService
from app.simulation.task_service import SimulationTaskService


router = APIRouter(
    prefix="/api/performance",
    tags=["performance"],
    dependencies=[Depends(require_resource(PERFORMANCE_VIEW_RESOURCE))],
)

settings = get_settings()
repository = SimulationRepository()
task_service = SimulationTaskService(repository=repository)
task_io_service = SimulationTaskIOService(settings)


@router.get(
    "/tasks/{task_id}/trace-time",
    response_model=TraceTimeAnalysisResponse,
)
def analyze_task_trace_time(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TraceTimeAnalysisResponse:
    try:
        task = task_service.get_task(db, task_id)
        require_task_read_access(current_user, task)
        events = task_io_service.read_trace_events(task)
        result = analyze_trace(events, TraceProducer.MSKPP)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TaskIOError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TraceAnalysisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return trace_time_response(
        result,
        source="simulation_task",
        source_name=task.task_name,
        task_id=task.task_id,
    )


@router.post(
    "/trace-time",
    response_model=TraceTimeAnalysisResponse,
)
def analyze_uploaded_trace_time(
    producer: TraceProducer = Form(),
    file: UploadFile = File(),
) -> TraceTimeAnalysisResponse:
    filename = file.filename or "trace.json"
    if not filename.lower().endswith(".json"):
        raise HTTPException(
            status_code=422,
            detail="Trace time analysis currently accepts JSON files only",
        )

    raw = file.file.read(settings.sim_trace_max_bytes + 1)
    if len(raw) > settings.sim_trace_max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                "Trace file exceeds upload limit: "
                f"{settings.sim_trace_max_bytes} bytes"
            ),
        )

    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        events = normalize_trace_json(payload)
        result = analyze_trace(events, producer)
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail="Trace file must use UTF-8 encoding",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid trace JSON at line {exc.lineno}, column {exc.colno}",
        ) from exc
    except TraceAnalysisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return trace_time_response(
        result,
        source="local_file",
        source_name=filename,
    )
