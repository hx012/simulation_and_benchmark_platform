from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from app.auth.constants import BENCHMARK_VIEW_RESOURCE
from app.auth.service import require_resource
from app.benchmark.config import get_benchmark_settings
from app.benchmark.exceptions import (
    BenchmarkChipNotFoundError,
    BenchmarkDefinitionNotFoundError,
    BenchmarkNotConfiguredError,
    BenchmarkRegistryFormatError,
    BenchmarkRegistryNotFoundError,
)
from app.benchmark.registry_reader import BenchmarkRegistryReader
from app.benchmark.result_provider import EmptyBenchmarkResultProvider
from app.benchmark.schemas import (
    BenchmarkDefinition,
    BenchmarkListResponse,
    BenchmarkResultListResponse,
    BenchmarkStatusResponse,
    ChipDetail,
    ChipListResponse,
)
from app.benchmark.service import BenchmarkService


router = APIRouter(
    prefix="/api/benchmark",
    tags=["benchmark"],
    dependencies=[Depends(require_resource(BENCHMARK_VIEW_RESOURCE))],
)


@lru_cache
def get_benchmark_service() -> BenchmarkService:
    settings = get_benchmark_settings()
    return BenchmarkService(
        registry_reader=BenchmarkRegistryReader(settings.aibench_home),
        result_provider=EmptyBenchmarkResultProvider(),
    )


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, BenchmarkNotConfiguredError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (BenchmarkChipNotFoundError, BenchmarkDefinitionNotFoundError)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, BenchmarkRegistryNotFoundError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, BenchmarkRegistryFormatError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected Benchmark backend error")


@router.get("/status", response_model=BenchmarkStatusResponse)
def get_benchmark_status(
    service: BenchmarkService = Depends(get_benchmark_service),
) -> BenchmarkStatusResponse:
    registry_available = False
    if service.registry_available:
        try:
            service.list_chips()
            registry_available = True
        except Exception:
            registry_available = False

    return BenchmarkStatusResponse(
        registry_available=registry_available,
        results_available=service.results_available,
    )


@router.get("/chips", response_model=ChipListResponse)
def list_chips(
    service: BenchmarkService = Depends(get_benchmark_service),
) -> ChipListResponse:
    try:
        items = service.list_chips()
    except Exception as exc:
        raise _translate_error(exc) from exc
    return ChipListResponse(items=items, total=len(items))


@router.get("/chips/{vendor}/{chip}", response_model=ChipDetail)
def get_chip(
    vendor: str,
    chip: str,
    service: BenchmarkService = Depends(get_benchmark_service),
) -> ChipDetail:
    try:
        return service.get_chip(vendor, chip)
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.get(
    "/chips/{vendor}/{chip}/benchmarks",
    response_model=BenchmarkListResponse,
)
def list_benchmarks(
    vendor: str,
    chip: str,
    service: BenchmarkService = Depends(get_benchmark_service),
) -> BenchmarkListResponse:
    try:
        items = service.list_benchmarks(vendor, chip)
    except Exception as exc:
        raise _translate_error(exc) from exc
    return BenchmarkListResponse(
        vendor=vendor,
        chip=chip,
        items=items,
        total=len(items),
    )


@router.get(
    "/chips/{vendor}/{chip}/benchmarks/{benchmark_name}",
    response_model=BenchmarkDefinition,
)
def get_benchmark(
    vendor: str,
    chip: str,
    benchmark_name: str,
    service: BenchmarkService = Depends(get_benchmark_service),
) -> BenchmarkDefinition:
    try:
        return service.get_benchmark(vendor, chip, benchmark_name)
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.get(
    "/chips/{vendor}/{chip}/benchmarks/{benchmark_name}/results",
    response_model=BenchmarkResultListResponse,
)
def list_benchmark_results(
    vendor: str,
    chip: str,
    benchmark_name: str,
    service: BenchmarkService = Depends(get_benchmark_service),
) -> BenchmarkResultListResponse:
    try:
        return service.list_results(vendor, chip, benchmark_name)
    except Exception as exc:
        raise _translate_error(exc) from exc
