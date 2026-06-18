"""
Pydantic v2 schemas for the HTTP API.

Field names are chosen to mirror `backend.app.pipeline.detect_gaps` output
verbatim so the frontend can type them 1:1 (see frontend/src/types.ts).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Enums ---------------------------------------------------------------


class ABCClass(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class Status(str, Enum):
    MISSING_WINNER = "Missing Winner"
    UNDERPERFORMING = "Underperforming"


class HealthStatus(str, Enum):
    OK = "ok"
    LOADING = "loading"
    ERROR = "error"


# --- Cleaning & summary --------------------------------------------------


class CleaningReport(BaseModel):
    """Output of pipeline.clean(). Mirrors CleaningReport dataclass."""

    model_config = ConfigDict(frozen=True)

    rows_before: int
    duplicates_removed: int
    returns_flagged: int
    zero_sales_flagged: int
    anomalies_flagged: int
    dummy_rows_removed: int
    group_income_rows_removed: int
    rows_after: int
    unique_articles: int
    unique_shops: int
    unique_departments: int


class ABCDistribution(BaseModel):
    A: int
    B: int
    C: int
    total: int


class SummaryResponse(BaseModel):
    cleaning: CleaningReport
    abc_distribution: ABCDistribution
    total_products: int
    total_revenue: float


# --- Dimensions ----------------------------------------------------------


class Shop(BaseModel):
    code: int
    label: str  # e.g. "184 — Shop 184"


class Department(BaseModel):
    name: str


# --- Gap detection -------------------------------------------------------


class GapFiltersIn(BaseModel):
    """Server-side representation of the /api/gaps query parameters."""

    shop: int
    department: Optional[str] = None
    abc_classes: list[ABCClass] = Field(
        default_factory=lambda: [ABCClass.A, ABCClass.B]
    )
    min_shops_selling: int = Field(default=3, ge=1)
    gap_threshold: float = Field(default=0.20, gt=0.0, le=1.0)


class GapRow(BaseModel):
    ArticleCode: int
    DepartmentName: str
    ABCClass: ABCClass
    NumShopsSelling: int
    ShopSaleValue: float
    ChainAvgSaleValue: float
    GapScore: float  # already clamped to [0, 1]
    PotentialLostRevenue: float
    Status: Status
    NeverStocked: bool


class GapKPIs(BaseModel):
    missing_winners: int
    underperforming: int
    potential_revenue: float
    class_a_gaps: int
    class_b_gaps: int
    total_gaps: int


class GapResponse(BaseModel):
    kpis: GapKPIs
    rows: list[GapRow]
    filters: GapFiltersIn
    generated_in_ms: float


# --- Health & upload -----------------------------------------------------


class HealthResponse(BaseModel):
    ready: bool
    status: HealthStatus
    dataset_loaded: bool
    load_error: Optional[str] = None


class UploadResponse(BaseModel):
    cleaning: CleaningReport
    rows_replaced: bool
