"""
Core data pipeline for the Missing Winners Analysis System.

Implements, in order:
  Phase 1 - data cleaning (see .claude/skills/data-cleaning/SKILL.md)
  Phase 2 - product aggregation
  Phase 3 - ABC analysis (see .claude/skills/abc-analysis/SKILL.md)
  Phase 4 - gap detection (see .claude/skills/gap-detection/SKILL.md)

All operations are vectorized pandas; nothing here should loop row-by-row
over the raw dataframe.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

REQUIRED_COLUMNS = ["ShopCode", "DepartmentName", "ArticleCode", "QtySold", "SaleValue"]


@dataclass
class CleaningReport:
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


def load_raw(path: str, sheet_name: str = "testdata1") -> pd.DataFrame:
    """Load the raw sales data sheet and validate its schema."""
    df = pd.read_excel(path, sheet_name=sheet_name)
    return _validate_schema(df)


def load_raw_csv(path: str) -> pd.DataFrame:
    """
    Load raw sales data from a CSV file. Useful for tests with small synthetic
    fixtures (avoids the 25-30s cost of pd.read_excel on the 14 MB xlsx).

    Accepts the same 5-column schema as load_raw; the cleaning/aggregation/
    ABC/gap-detection pipeline downstream is file-format agnostic.
    """
    df = pd.read_csv(path)
    return _validate_schema(df)


def _validate_schema(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Input file is missing required columns {missing}. "
            f"Found columns: {df.columns.tolist()}"
        )
    return df[REQUIRED_COLUMNS].copy()


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """
    Apply Phase 1 cleaning rules. Returns (cleaned_df, report).

    Flags IsReturn / IsZeroSale / IsAnomaly are added but those rows are
    NOT dropped. Only exact duplicates, DUMMY article rows, and
    GROUP INCOME/EXPENSE department rows are dropped.
    """
    rows_before = len(df)

    df = df.drop_duplicates().copy()
    duplicates_removed = rows_before - len(df)

    is_return = (df["QtySold"] < 0) | (df["SaleValue"] < 0)
    is_zero_sale = (df["QtySold"] == 0) | (df["SaleValue"] == 0)
    is_anomaly = ((df["QtySold"] > 0) & (df["SaleValue"] < 0)) | (
        (df["QtySold"] < 0) & (df["SaleValue"] > 0)
    )

    df["IsReturn"] = is_return
    df["IsZeroSale"] = is_zero_sale
    df["IsAnomaly"] = is_anomaly

    returns_flagged = int(is_return.sum())
    zero_sales_flagged = int(is_zero_sale.sum())
    anomalies_flagged = int(is_anomaly.sum())

    # ArticleCode has mixed types (int + literal "DUMMY" strings) - filter
    # the DUMMY rows BEFORE attempting any numeric cast of this column.
    is_dummy = df["ArticleCode"].astype(str).str.strip().str.upper() == "DUMMY"
    is_group_income = df["DepartmentName"] == "GROUP INCOME/EXPENSE"

    dummy_rows_removed = int((is_dummy & ~is_group_income).sum())
    group_income_rows_removed = int(is_group_income.sum())
    # Note: report dummy count excluding any overlap with group_income so
    # the two figures don't double count the same row; total removed below
    # uses the combined mask directly, which is always correct regardless
    # of overlap.

    cleaned = df[~(is_dummy | is_group_income)].copy()

    # Now safe to coerce ArticleCode to a consistent int type.
    cleaned["ArticleCode"] = cleaned["ArticleCode"].astype("int64")

    report = CleaningReport(
        rows_before=rows_before,
        duplicates_removed=duplicates_removed,
        returns_flagged=returns_flagged,
        zero_sales_flagged=zero_sales_flagged,
        anomalies_flagged=anomalies_flagged,
        dummy_rows_removed=dummy_rows_removed,
        group_income_rows_removed=group_income_rows_removed,
        rows_after=len(cleaned),
        unique_articles=cleaned["ArticleCode"].nunique(),
        unique_shops=cleaned["ShopCode"].nunique(),
        unique_departments=cleaned["DepartmentName"].nunique(),
    )
    return cleaned, report


def aggregate_chain(df: pd.DataFrame) -> pd.DataFrame:
    """Phase 2.1: chain-wide product summary, grouped by ArticleCode."""
    g = df.groupby("ArticleCode").agg(
        TotalQtySold=("QtySold", "sum"),
        TotalSaleValue=("SaleValue", "sum"),
        NumShopsSelling=("ShopCode", "nunique"),
        DepartmentName=("DepartmentName", "first"),
    )
    g["AvgSaleValuePerShop"] = g["TotalSaleValue"] / g["NumShopsSelling"]
    return g.reset_index()


def aggregate_shop_product(df: pd.DataFrame) -> pd.DataFrame:
    """Phase 2.2: shop x product summary."""
    g = df.groupby(["ShopCode", "ArticleCode"]).agg(
        ShopQtySold=("QtySold", "sum"),
        ShopSaleValue=("SaleValue", "sum"),
    )
    return g.reset_index()


def classify_abc(chain_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Phase 3: ABC classification by cumulative revenue share.
    Class A: cumulative % <= 70
    Class B: 70 < cumulative % <= 90
    Class C: 90 < cumulative % <= 100

    Negative/zero TotalSaleValue products are clamped to 0 for the purpose
    of the cumulative curve so a large negative outlier (net returns) can't
    distort ranking of products after it; they will always land in Class C.
    """
    out = chain_summary.sort_values("TotalSaleValue", ascending=False).copy()
    clamped = out["TotalSaleValue"].clip(lower=0)
    total_revenue = clamped.sum()

    if total_revenue <= 0:
        out["CumulativeRevenuePct"] = 0.0
        out["ABCClass"] = "C"
        return out

    out["CumulativeRevenuePct"] = clamped.cumsum() / total_revenue * 100
    out["ABCClass"] = pd.cut(
        out["CumulativeRevenuePct"],
        bins=[-0.01, 70, 90, 100.01],
        labels=["A", "B", "C"],
    ).astype(str)
    return out


@dataclass
class GapFilters:
    shop_code: int
    department: Optional[str] = None
    abc_classes: tuple[str, ...] = ("A", "B")
    min_shops_selling: int = 3
    gap_threshold: float = 0.20


def detect_gaps(
    chain_summary: pd.DataFrame,
    shop_product: pd.DataFrame,
    filters: GapFilters,
) -> pd.DataFrame:
    """
    Phase 4 + 5: find Missing Winners and Underperforming products for a
    given shop, with gap score and potential lost revenue, ranked
    descending by potential lost revenue.
    """
    candidates = chain_summary[
        chain_summary["ABCClass"].isin(filters.abc_classes)
        & (chain_summary["NumShopsSelling"] >= filters.min_shops_selling)
    ].copy()

    if filters.department:
        candidates = candidates[candidates["DepartmentName"] == filters.department]

    shop_rows = shop_product[shop_product["ShopCode"] == filters.shop_code][
        ["ArticleCode", "ShopSaleValue", "ShopQtySold"]
    ]

    merged = candidates.merge(shop_rows, on="ArticleCode", how="left")

    # No row at all for this shop -> NaN after the left merge -> never stocked.
    merged["NeverStocked"] = merged["ShopSaleValue"].isna()
    merged["ShopSaleValue"] = merged["ShopSaleValue"].fillna(0.0)
    merged["ShopQtySold"] = merged["ShopQtySold"].fillna(0)

    chain_avg = merged["TotalSaleValue"] / merged["NumShopsSelling"]
    merged["ChainAvgSaleValue"] = chain_avg

    is_missing = merged["ShopSaleValue"] == 0
    is_underperforming = (~is_missing) & (
        merged["ShopSaleValue"] < filters.gap_threshold * chain_avg
    )

    merged["Status"] = "OK"
    merged.loc[is_underperforming, "Status"] = "Underperforming"
    merged.loc[is_missing, "Status"] = "Missing Winner"

    gaps = merged[merged["Status"] != "OK"].copy()

    gap_score = pd.Series(0.0, index=gaps.index)
    nonzero_avg = gaps["ChainAvgSaleValue"] != 0
    gap_score.loc[nonzero_avg] = (
        gaps.loc[nonzero_avg, "ChainAvgSaleValue"] - gaps.loc[nonzero_avg, "ShopSaleValue"]
    ) / gaps.loc[nonzero_avg, "ChainAvgSaleValue"]
    gaps["GapScore"] = gap_score.clip(lower=0, upper=1)
    gaps["PotentialLostRevenue"] = gaps["ChainAvgSaleValue"] - gaps["ShopSaleValue"]

    gaps = gaps.sort_values("PotentialLostRevenue", ascending=False)

    cols = [
        "ArticleCode",
        "DepartmentName",
        "ABCClass",
        "NumShopsSelling",
        "ShopSaleValue",
        "ChainAvgSaleValue",
        "GapScore",
        "PotentialLostRevenue",
        "Status",
        "NeverStocked",
    ]
    return gaps[cols].reset_index(drop=True)


@dataclass
class PipelineResult:
    cleaned: pd.DataFrame
    cleaning_report: CleaningReport
    chain_summary: pd.DataFrame
    shop_product: pd.DataFrame


def run_pipeline(path: str, sheet_name: str = "testdata1") -> PipelineResult:
    raw = load_raw(path, sheet_name=sheet_name)
    cleaned, report = clean(raw)
    chain = aggregate_chain(cleaned)
    chain = classify_abc(chain)
    shop_product = aggregate_shop_product(cleaned)
    return PipelineResult(
        cleaned=cleaned,
        cleaning_report=report,
        chain_summary=chain,
        shop_product=shop_product,
    )
