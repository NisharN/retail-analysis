"""Health/readiness endpoint.

Returns 200 while the dataset is still loading (so health probes don't
mistake the ~25-30s pipeline startup for a service outage), and 503 only
when the pipeline has actually failed.
"""
from __future__ import annotations

from fastapi import APIRouter, Response, status

from ..schemas import HealthResponse, HealthStatus
from ..state import get_state

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    state = get_state()

    if state.load_error is not None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            ready=False,
            status=HealthStatus.ERROR,
            dataset_loaded=False,
            load_error=state.load_error,
        )

    if not state.is_ready():
        return HealthResponse(
            ready=False,
            status=HealthStatus.LOADING,
            dataset_loaded=False,
            load_error=None,
        )

    return HealthResponse(
        ready=True,
        status=HealthStatus.OK,
        dataset_loaded=True,
        load_error=None,
    )