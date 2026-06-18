"""
Gap-detection endpoint.

`GET /api/gaps?shop=...&department=...&abc_classes=A,B&min_shops_selling=3&gap_threshold=0.20`

The central business endpoint of the whole system. Wraps
`pipeline.detect_gaps` with:

  - shop validation against the cleaned-data ShopCodes (rejects the 6
    "ghost" shops with HTTP 400 `shop_not_in_cleaned_data`),
  - department validation (rejects unknown departments with HTTP 400),
  - ABC class validation,
  - per-class KPI rollup from the returned rows,
  - a hard `limit` cap to prevent runaway payloads,
  - export endpoints that stream Excel/PDF for the same query.
"""
from __future__ import annotations

import io
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..config import MAX_GAP_ROWS
from ..export import build_excel, build_pdf
from ..pipeline import GapFilters, detect_gaps
from ..schemas import (
    ABCClass,
    GapFiltersIn,
    GapKPIs,
    GapResponse,
    GapRow,
    Status,
)
from ..state import get_state

router = APIRouter(tags=["gaps"])


def _parse_abc_classes(raw: str) -> list[ABCClass]:
    items = [s.strip().upper() for s in raw.split(",") if s.strip()]
    try:
        return [ABCClass(v) for v in items]
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_abc_classes",
                "received": items,
                "allowed": [c.value for c in ABCClass],
            },
        ) from exc


def _build_response(
    shop: int,
    department: Optional[str],
    abc_classes_str: str,
    min_shops_selling: int,
    gap_threshold: float,
    limit: int,
) -> GapResponse:
    state = get_state()
    if not state.is_ready():
        raise HTTPException(status_code=503, detail="dataset_not_ready")

    cleaned_shops = set(int(c) for c in state.cleaned["ShopCode"].unique())
    if shop not in cleaned_shops:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "shop_not_in_cleaned_data",
                "shop": shop,
                "hint": "This shop has no product rows in the cleaned dataset "
                        "(see CLAUDE.md §'Known discrepancies' for why).",
            },
        )

    cleaned_departments = set(state.cleaned["DepartmentName"].unique())
    if department is not None and department not in cleaned_departments:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_department",
                "department": department,
                "allowed_count": len(cleaned_departments),
            },
        )

    abc_classes = _parse_abc_classes(abc_classes_str)

    filters = GapFilters(
        shop_code=shop,
        department=department,
        abc_classes=tuple(c.value for c in abc_classes),
        min_shops_selling=min_shops_selling,
        gap_threshold=gap_threshold,
    )

    t0 = time.perf_counter()
    df = detect_gaps(state.chain_summary, state.shop_product, filters)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if limit > 0 and len(df) > limit:
        df = df.head(limit)

    # Build Pydantic rows (cap to limit; already done above).
    rows = [
        GapRow(
            ArticleCode=int(r.ArticleCode),
            DepartmentName=str(r.DepartmentName),
            ABCClass=ABCClass(r.ABCClass),
            NumShopsSelling=int(r.NumShopsSelling),
            ShopSaleValue=float(r.ShopSaleValue),
            ChainAvgSaleValue=float(r.ChainAvgSaleValue),
            GapScore=float(r.GapScore),
            PotentialLostRevenue=float(r.PotentialLostRevenue),
            Status=Status(r.Status),
            NeverStocked=bool(r.NeverStocked),
        )
        for r in df.itertuples(index=False)
    ]

    if rows:
        mw = sum(1 for r in rows if r.Status == Status.MISSING_WINNER)
        up = sum(1 for r in rows if r.Status == Status.UNDERPERFORMING)
        a = sum(1 for r in rows if r.ABCClass == ABCClass.A)
        b = sum(1 for r in rows if r.ABCClass == ABCClass.B)
        potential = sum(r.PotentialLostRevenue for r in rows)
    else:
        mw = up = a = b = 0
        potential = 0.0

    kpis = GapKPIs(
        missing_winners=mw,
        underperforming=up,
        potential_revenue=potential,
        class_a_gaps=a,
        class_b_gaps=b,
        total_gaps=len(rows),
    )

    filters_in = GapFiltersIn(
        shop=shop,
        department=department,
        abc_classes=abc_classes,
        min_shops_selling=min_shops_selling,
        gap_threshold=gap_threshold,
    )

    return GapResponse(
        kpis=kpis,
        rows=rows,
        filters=filters_in,
        generated_in_ms=round(elapsed_ms, 3),
    )


@router.get("/api/gaps", response_model=GapResponse)
def get_gaps(
    shop: int = Query(..., description="ShopCode to analyze"),
    department: Optional[str] = Query(None),
    abc_classes: str = Query("A,B", description="Comma-separated, e.g. 'A,B'"),
    min_shops_selling: int = Query(3, ge=1),
    gap_threshold: float = Query(0.20, gt=0.0, le=1.0),
    limit: int = Query(MAX_GAP_ROWS, ge=1, le=MAX_GAP_ROWS),
) -> GapResponse:
    return _build_response(
        shop=shop,
        department=department,
        abc_classes_str=abc_classes,
        min_shops_selling=min_shops_selling,
        gap_threshold=gap_threshold,
        limit=limit,
    )


# --- Export endpoints ----------------------------------------------------


def _stream_export(content: bytes, filename: str, media_type: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.get("/api/gaps/export.xlsx")
def export_xlsx(
    shop: int = Query(...),
    department: Optional[str] = Query(None),
    abc_classes: str = Query("A,B"),
    min_shops_selling: int = Query(3, ge=1),
    gap_threshold: float = Query(0.20, gt=0.0, le=1.0),
) -> StreamingResponse:
    response = _build_response(
        shop=shop,
        department=department,
        abc_classes_str=abc_classes,
        min_shops_selling=min_shops_selling,
        gap_threshold=gap_threshold,
        limit=MAX_GAP_ROWS,
    )
    blob = build_excel(response.rows, response.kpis, response.filters)
    filename = f"missing_winners_{shop}.xlsx"
    return _stream_export(
        blob,
        filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/api/gaps/export.pdf")
def export_pdf(
    shop: int = Query(...),
    department: Optional[str] = Query(None),
    abc_classes: str = Query("A,B"),
    min_shops_selling: int = Query(3, ge=1),
    gap_threshold: float = Query(0.20, gt=0.0, le=1.0),
) -> StreamingResponse:
    response = _build_response(
        shop=shop,
        department=department,
        abc_classes_str=abc_classes,
        min_shops_selling=min_shops_selling,
        gap_threshold=gap_threshold,
        limit=MAX_GAP_ROWS,
    )
    blob = build_pdf(response.rows, response.kpis, response.filters)
    filename = f"missing_winners_{shop}.pdf"
    return _stream_export(blob, filename, "application/pdf")
