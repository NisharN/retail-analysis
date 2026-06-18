"""
Dataset summary endpoint.

Reports cleaning counts, ABC distribution, and total revenue. Used by
the dashboard header and any "data quality" sub-view.

Total revenue is computed with the same `clip(lower=0)` clamp that
`pipeline.classify_abc` uses, so the figure here is the same denominator
used by the cumulative-revenue calculation.
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from ..pipeline import CleaningReport
from ..schemas import ABCDistribution, CleaningReport as CleaningReportModel, SummaryResponse
from ..state import get_state

router = APIRouter(tags=["summary"])


@router.get("/api/summary", response_model=SummaryResponse)
def summary() -> SummaryResponse:
    state = get_state()
    if not state.is_ready():
        raise HTTPException(status_code=503, detail="dataset_not_ready")

    report: CleaningReport = state.cleaning_report  # type: ignore[assignment]

    counts = state.chain_summary["ABCClass"].value_counts().to_dict()  # type: ignore[union-attr]
    abc = ABCDistribution(
        A=int(counts.get("A", 0)),
        B=int(counts.get("B", 0)),
        C=int(counts.get("C", 0)),
        total=int(sum(counts.values())),
    )

    # Match the classify_abc clamp so the totals are consistent.
    total_revenue = float(state.chain_summary["TotalSaleValue"].clip(lower=0).sum())  # type: ignore[union-attr]

    return SummaryResponse(
        cleaning=CleaningReportModel(**asdict(report)),
        abc_distribution=abc,
        total_products=report.unique_articles,
        total_revenue=total_revenue,
    )
