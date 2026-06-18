"""
Tests for `app.pipeline.detect_gaps` — Phase 4/5 gap detection.

Scenarios were verified against the actual function output before being
hardcoded as assertions (see the gap-detection skill for the business
rules being tested).
"""
from __future__ import annotations

import pandas as pd
import pytest

from app.pipeline import GapFilters, detect_gaps


def test_never_stocked_product_is_missing_winner(pipeline_result: dict) -> None:
    """Article 1001 (Class A, 3 shops) has no row at all for shop 4."""
    gaps = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=4, min_shops_selling=3),
    )
    row = gaps[gaps["ArticleCode"] == 1001].iloc[0]
    assert row["Status"] == "Missing Winner"
    assert bool(row["NeverStocked"]) is True
    assert row["ShopSaleValue"] == 0.0
    assert row["GapScore"] == pytest.approx(1.0)


def test_stocked_but_underperforming_is_not_never_stocked(pipeline_result: dict) -> None:
    """
    Article 1002 in shop 1 has a real (low) sales row -- it must be
    classified Underperforming, NOT Missing Winner, and NeverStocked must
    be False since a row genuinely exists.
    """
    gaps = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=1, min_shops_selling=3),
    )
    row = gaps[gaps["ArticleCode"] == 1002].iloc[0]
    assert row["Status"] == "Underperforming"
    assert bool(row["NeverStocked"]) is False
    assert row["ShopSaleValue"] == pytest.approx(50.0)


def test_zero_value_row_is_missing_winner_but_not_never_stocked() -> None:
    """
    A row that exists with ShopSaleValue == 0 ("stocked but sold nothing")
    is a different situation from no row at all ("never stocked"), but
    both count as Missing Winner per the gap-detection skill. NeverStocked
    distinguishes which case it was.
    """
    chain_summary = pd.DataFrame(
        {
            "ArticleCode": [7001],
            "TotalSaleValue": [3000.0],
            "NumShopsSelling": [3],
            "DepartmentName": ["GROCERY"],
            "ABCClass": ["A"],
        }
    )
    shop_product = pd.DataFrame(
        {
            "ShopCode": [1, 2, 3, 4],
            "ArticleCode": [7001, 7001, 7001, 7001],
            "ShopSaleValue": [1000.0, 1000.0, 1000.0, 0.0],
            "ShopQtySold": [10, 10, 10, 0],
        }
    )
    gaps = detect_gaps(chain_summary, shop_product, GapFilters(shop_code=4, min_shops_selling=3))
    row = gaps[gaps["ArticleCode"] == 7001].iloc[0]
    assert row["Status"] == "Missing Winner"
    assert bool(row["NeverStocked"]) is False  # a row genuinely exists
    assert row["ShopSaleValue"] == 0.0


def test_product_above_gap_threshold_is_excluded_as_ok(pipeline_result: dict) -> None:
    """Article 1002 in shop 2/3/4 sells at full chain-average value -> OK, excluded."""
    gaps = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=2, min_shops_selling=3),
    )
    assert 1002 not in gaps["ArticleCode"].values


def test_min_shops_selling_excludes_single_shop_products(pipeline_result: dict) -> None:
    """
    Article 1003 has high revenue (would be Class A) but sells in only 1
    shop -- it must be excluded by the default min_shops_selling=3 filter
    even though it's a high-value product.
    """
    gaps = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=4, min_shops_selling=3),
    )
    assert 1003 not in gaps["ArticleCode"].values

    # Lowering the threshold to 1 should surface it (it's never stocked in shop 4).
    gaps_relaxed = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=4, min_shops_selling=1),
    )
    assert 1003 in gaps_relaxed["ArticleCode"].values


def test_department_filter_narrows_results(pipeline_result: dict) -> None:
    gaps_all = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=4, min_shops_selling=3),
    )
    gaps_beverages = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=4, department="BEVERAGES", min_shops_selling=3),
    )
    assert len(gaps_beverages) < len(gaps_all)
    assert set(gaps_beverages["DepartmentName"]) == {"BEVERAGES"}
    assert 1001 in gaps_beverages["ArticleCode"].values  # BEVERAGES, never in shop 4
    assert 2000 not in gaps_beverages["ArticleCode"].values  # GROCERY, filtered out


def test_abc_class_filter_excludes_class_c(pipeline_result: dict) -> None:
    gaps_ab_only = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=4, abc_classes=("A", "B"), min_shops_selling=3),
    )
    assert set(gaps_ab_only["ABCClass"]).issubset({"A", "B"})

    gaps_c_only = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=4, abc_classes=("C",), min_shops_selling=1),
    )
    if not gaps_c_only.empty:
        assert set(gaps_c_only["ABCClass"]) == {"C"}


def test_gap_score_is_clamped_to_zero_one(pipeline_result: dict) -> None:
    gaps = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=1, abc_classes=("A", "B", "C"), min_shops_selling=1),
    )
    assert (gaps["GapScore"] >= 0).all()
    assert (gaps["GapScore"] <= 1).all()


def test_results_are_sorted_descending_by_potential_lost_revenue(pipeline_result: dict) -> None:
    gaps = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=4, min_shops_selling=3),
    )
    values = gaps["PotentialLostRevenue"].tolist()
    assert values == sorted(values, reverse=True)


def test_gap_threshold_is_configurable(pipeline_result: dict) -> None:
    """
    Article 1002 in shop 1 sells at 50 vs a chain average of ~5944 (~0.84%
    of average). A very strict 0.1% threshold (5944 * 0.001 = 5.94) should
    NOT flag it as underperforming since 50 > 5.94; the default 20%
    threshold (5944 * 0.20 = 1188.9) should, since 50 < 1188.9.
    """
    gaps_strict = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=1, min_shops_selling=3, gap_threshold=0.001),
    )
    gaps_default = detect_gaps(
        pipeline_result["chain_summary"],
        pipeline_result["shop_product"],
        GapFilters(shop_code=1, min_shops_selling=3, gap_threshold=0.20),
    )
    assert 1002 not in gaps_strict["ArticleCode"].values
    assert 1002 in gaps_default["ArticleCode"].values
