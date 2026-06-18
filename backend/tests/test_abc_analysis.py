"""
Tests for `app.pipeline.classify_abc` — Phase 3 ABC classification.

Class assignments for the `pipeline_result` fixture below were verified by
direct inspection (see CLAUDE.md-style derivation in conftest.py's
docstring) before being hardcoded here, per the abc-analysis skill's
warning not to assume distributions on small synthetic catalogs without
checking the actual cumulative curve.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app.pipeline import classify_abc


def test_measured_class_assignments_on_synthetic_fixture(pipeline_result: dict) -> None:
    chain = pipeline_result["chain_summary"].set_index("ArticleCode")
    expected = {
        1001: "A",
        1003: "A",
        2000: "A",
        1002: "A",
        2001: "A",
        2002: "B",
        2003: "B",
        2004: "B",
        2005: "C",
        2006: "C",
        2007: "C",
        2008: "C",
        2009: "C",
        2010: "C",
        2011: "C",
        9001: "C",  # net negative revenue (a pure return) -> always Class C
        9002: "C",  # zero revenue -> always Class C
        9003: "C",  # net negative revenue -> always Class C
    }
    for article, expected_class in expected.items():
        assert chain.loc[article, "ABCClass"] == expected_class, (
            f"article {article} expected class {expected_class}"
        )


def test_class_a_products_are_higher_revenue_than_class_b(pipeline_result: dict) -> None:
    chain = pipeline_result["chain_summary"]
    min_a_revenue = chain[chain["ABCClass"] == "A"]["TotalSaleValue"].min()
    max_b_revenue = chain[chain["ABCClass"] == "B"]["TotalSaleValue"].max()
    assert min_a_revenue >= max_b_revenue


def test_cumulative_revenue_pct_is_monotonic(pipeline_result: dict) -> None:
    chain = pipeline_result["chain_summary"].sort_values(
        "TotalSaleValue", ascending=False
    )
    cum = chain["CumulativeRevenuePct"].to_numpy()
    assert all(cum[i] <= cum[i + 1] + 1e-9 for i in range(len(cum) - 1))
    assert cum[-1] == pytest.approx(100.0)


def test_class_boundaries_are_70_and_90_percent() -> None:
    """
    Direct boundary test on a hand-built chain summary, independent of the
    synthetic fixture: three equal-revenue products land exactly on the
    70/90 cumulative boundaries.
    """
    chain_summary = pd.DataFrame(
        {
            "ArticleCode": [1, 2, 3],
            "TotalSaleValue": [70.0, 20.0, 10.0],  # cumulative: 70%, 90%, 100%
            "NumShopsSelling": [3, 3, 3],
            "DepartmentName": ["X", "X", "X"],
        }
    )
    out = classify_abc(chain_summary).set_index("ArticleCode")
    assert out.loc[1, "ABCClass"] == "A"  # cumulative == 70% -> A (inclusive)
    assert out.loc[2, "ABCClass"] == "B"  # cumulative == 90% -> B (inclusive)
    assert out.loc[3, "ABCClass"] == "C"  # cumulative == 100% -> C


def test_negative_total_revenue_is_clamped_for_cumulative_curve() -> None:
    """
    A large negative outlier (net returns) must not distort the
    cumulative curve for products ranked after it — classify_abc clamps
    at 0 for the purposes of the cumulative-% calculation.
    """
    chain_summary = pd.DataFrame(
        {
            "ArticleCode": [1, 2, 3],
            "TotalSaleValue": [100.0, -500.0, 50.0],
            "NumShopsSelling": [3, 3, 3],
            "DepartmentName": ["X", "X", "X"],
        }
    )
    out = classify_abc(chain_summary).set_index("ArticleCode")
    # Total clamped revenue = 100 + 0 + 50 = 150. Product 1: 100/150=66.7% -> A.
    # Product 3: (100+50)/150=100% -> C. Product 2 (negative): always C.
    assert out.loc[1, "ABCClass"] == "A"
    assert out.loc[2, "ABCClass"] == "C"
    assert out.loc[3, "ABCClass"] == "C"


def test_all_zero_revenue_does_not_crash() -> None:
    chain_summary = pd.DataFrame(
        {
            "ArticleCode": [1, 2],
            "TotalSaleValue": [0.0, 0.0],
            "NumShopsSelling": [1, 1],
            "DepartmentName": ["X", "X"],
        }
    )
    out = classify_abc(chain_summary)
    assert (out["ABCClass"] == "C").all()
