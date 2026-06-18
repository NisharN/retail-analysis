"""
Integration test against the real `data/testdata1.xlsx` file.

This is intentionally slow (~25-30s, per the performance note in
CLAUDE.md, dominated by `pd.read_excel` on the 521k-row file) and is kept
separate from the fast synthetic-fixture unit tests. It exists to catch
the exact failure mode CLAUDE.md warns about: silently drifting away from
the validated baseline numbers if the cleaning/aggregation/ABC logic
changes. Every assertion below is copied directly from CLAUDE.md's
"Source data — validated facts" and "Known discrepancies" sections, not
re-derived or guessed.

Marked `integration` (registered in pytest.ini) so it can be skipped with
`pytest -m "not integration"` during fast iteration, but runs by default.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.pipeline import GapFilters, detect_gaps, run_pipeline

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "testdata1.xlsx"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def real_pipeline_result():
    if not DATA_PATH.exists():
        pytest.skip(f"Real dataset not found at {DATA_PATH}")
    return run_pipeline(str(DATA_PATH))


def test_raw_row_count_matches_claude_md(real_pipeline_result) -> None:
    assert real_pipeline_result.cleaning_report.rows_before == 521_102


def test_cleaning_counts_match_claude_md(real_pipeline_result) -> None:
    report = real_pipeline_result.cleaning_report
    assert report.duplicates_removed == 48
    assert report.returns_flagged == 198  # union of QtySold<0 OR SaleValue<0
    assert report.zero_sales_flagged == 1_706  # union of QtySold==0 OR SaleValue==0
    assert report.anomalies_flagged == 5
    assert report.dummy_rows_removed == 74
    assert report.group_income_rows_removed == 382
    assert report.rows_after == 520_598


def test_post_cleaning_dimension_counts_match_claude_md(real_pipeline_result) -> None:
    report = real_pipeline_result.cleaning_report
    assert report.unique_articles == 69_993
    assert report.unique_shops == 74  # not 80 -- 6 ghost shops vanish
    assert report.unique_departments == 39  # not 41 raw


def test_ghost_shops_are_absent_from_cleaned_data(real_pipeline_result) -> None:
    ghost_shops = {120, 129, 131, 173, 177, 185}
    cleaned_shops = set(int(c) for c in real_pipeline_result.cleaned["ShopCode"].unique())
    assert ghost_shops.isdisjoint(cleaned_shops)


def test_abc_distribution_matches_claude_md(real_pipeline_result) -> None:
    counts = real_pipeline_result.chain_summary["ABCClass"].value_counts().to_dict()
    assert counts.get("A", 0) == 1_985
    assert counts.get("B", 0) == 8_196
    assert counts.get("C", 0) == 59_812
    assert sum(counts.values()) == 69_993


def test_total_revenue_matches_claude_md(real_pipeline_result) -> None:
    total = real_pipeline_result.chain_summary["TotalSaleValue"].clip(lower=0).sum()
    assert total == pytest.approx(85_379_787, rel=1e-4)


def test_dummy_rows_were_string_typed_before_cleaning() -> None:
    """
    Sanity check on the raw file itself (independent of run_pipeline) that
    the 74 DUMMY rows really are the literal string "DUMMY", all under
    TALAL_RETAIL, exactly as CLAUDE.md documents.
    """
    if not DATA_PATH.exists():
        pytest.skip(f"Real dataset not found at {DATA_PATH}")
    from app.pipeline import load_raw

    raw = load_raw(str(DATA_PATH))
    dummy_rows = raw[raw["ArticleCode"].astype(str).str.strip().str.upper() == "DUMMY"]
    assert len(dummy_rows) == 74
    assert set(dummy_rows["DepartmentName"]) == {"TALAL_RETAIL"}


def test_gap_detection_runs_fast_once_cached(real_pipeline_result) -> None:
    """
    CLAUDE.md: 'Gap detection itself (detect_gaps) runs in ~0.1s once the
    cached tables exist.' Assert it stays comfortably under 1s on the
    full real dataset for a representative shop.
    """
    import time

    shop = int(real_pipeline_result.cleaned["ShopCode"].unique()[0])
    t0 = time.perf_counter()
    detect_gaps(
        real_pipeline_result.chain_summary,
        real_pipeline_result.shop_product,
        GapFilters(shop_code=shop),
    )
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0
