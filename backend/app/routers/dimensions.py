"""
Dimension endpoints — shops and departments.

These drive the filter dropdowns in the UI. They are derived from the
**cleaned** data, not the raw file — so the 6 "ghost" shops (120, 129,
131, 173, 177, 185) that only ever appear on GROUP INCOME/EXPENSE rows
in the source never make it into the dropdown. A user selecting one of
those by hand-crafted URL is rejected by the gaps router with HTTP 400.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import Department, Shop
from ..state import get_state

router = APIRouter(tags=["dimensions"])


@router.get("/api/shops", response_model=list[Shop])
def list_shops() -> list[Shop]:
    state = get_state()
    if not state.is_ready():
        raise HTTPException(status_code=503, detail="dataset_not_ready")
    codes = sorted(int(c) for c in state.cleaned["ShopCode"].unique().tolist())
    return [Shop(code=code, label=f"{code} — Shop {code}") for code in codes]


@router.get("/api/departments", response_model=list[Department])
def list_departments() -> list[Department]:
    state = get_state()
    if not state.is_ready():
        raise HTTPException(status_code=503, detail="dataset_not_ready")
    names = sorted(state.cleaned["DepartmentName"].unique().tolist())
    return [Department(name=n) for n in names]