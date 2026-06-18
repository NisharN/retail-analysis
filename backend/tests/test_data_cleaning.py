"""
Tests for `app.pipeline.clean` — Phase 1 data cleaning.

Each assertion below is derived from the known, hand-built composition of
the `raw_df` fixture (see conftest.py), mirroring the validation checklist
in `.claude/skills/data-cleaning/SKILL.md`.
"""
from __future__ import annotations

import pandas as pd

from app.pipeline import clean


def test_duplicate_rows_are_dropped(raw_df: pd.DataFrame) -> None:
    cleaned, report = clean(raw_df)
    # raw_df contains exactly one exact duplicate (article 1001 / shop 1).
    assert report.duplicates_removed == 1
    assert report.rows_before == len(raw_df)
    assert len(cleaned) == report.rows_after


def test_returns_are_flagged_not_dropped(raw_df: pd.DataFrame) -> None:
    cleaned, report = clean(raw_df)
    # Article 9001 (QtySold=-5, SaleValue=-100) is a pure return. Article
    # 9003 (QtySold=5>0, SaleValue=-20<0) satisfies SaleValue<0 too, so it
    # is ALSO flagged as a return -- IsReturn and IsAnomaly are independent
    # boolean columns, not mutually exclusive categories (any row with a
    # sign mismatch necessarily also has SaleValue<0 or QtySold<0, so every
    # anomaly is, by construction, also a return). returns_flagged is 2.
    assert report.returns_flagged == 2
    return_rows = cleaned[cleaned["ArticleCode"].isin([9001, 9003])]
    assert len(return_rows) == 2
    assert return_rows["IsReturn"].all()


def test_zero_sales_are_flagged_not_dropped(raw_df: pd.DataFrame) -> None:
    cleaned, report = clean(raw_df)
    # Article 9002 (QtySold=0, SaleValue=0) is the one deliberate zero-sale row.
    assert report.zero_sales_flagged == 1
    zero_rows = cleaned[cleaned["ArticleCode"] == 9002]
    assert len(zero_rows) == 1
    assert bool(zero_rows.iloc[0]["IsZeroSale"]) is True


def test_anomalies_are_flagged_not_dropped(raw_df: pd.DataFrame) -> None:
    cleaned, report = clean(raw_df)
    # Article 9003 (QtySold=5 > 0, SaleValue=-20 < 0) is the sign-mismatch row.
    assert report.anomalies_flagged == 1
    anomaly_rows = cleaned[cleaned["ArticleCode"] == 9003]
    assert len(anomaly_rows) == 1
    assert bool(anomaly_rows.iloc[0]["IsAnomaly"]) is True


def test_flags_are_independent_columns_not_mutually_exclusive(raw_df: pd.DataFrame) -> None:
    """
    IsReturn / IsZeroSale / IsAnomaly are three independently-computed
    boolean columns, not a single mutually-exclusive category -- CLAUDE.md
    explicitly warns the real dataset's return/zero-sale sub-condition
    counts (152/196 and 1,696/1,630) are NOT disjoint either. On this
    fixture, article 9003 (QtySold=5>0, SaleValue=-20<0) is flagged BOTH
    IsReturn (via SaleValue<0) and IsAnomaly. Every anomaly is, by
    construction, necessarily also a return (a sign mismatch always means
    QtySold<0 or SaleValue<0) -- assert that subset relationship holds
    rather than assuming the flags are disjoint.
    """
    cleaned, _ = clean(raw_df)
    anomaly_rows = cleaned[cleaned["IsAnomaly"]]
    assert len(anomaly_rows) == 1
    assert anomaly_rows["IsReturn"].all()  # anomaly => return, always

    # The pure zero-sale row (9002) must not also be flagged as a return
    # or anomaly -- it has QtySold==0 and SaleValue==0, no sign mismatch.
    zero_sale_row = cleaned[cleaned["ArticleCode"] == 9002].iloc[0]
    assert bool(zero_sale_row["IsReturn"]) is False
    assert bool(zero_sale_row["IsAnomaly"]) is False

    # The pure return (9001, both QtySold and SaleValue negative, same
    # sign) must not be flagged as an anomaly.
    pure_return_row = cleaned[cleaned["ArticleCode"] == 9001].iloc[0]
    assert bool(pure_return_row["IsAnomaly"]) is False


def test_dummy_rows_are_dropped(raw_df: pd.DataFrame) -> None:
    cleaned, report = clean(raw_df)
    assert report.dummy_rows_removed == 1
    assert "DUMMY" not in cleaned["ArticleCode"].astype(str).values
    assert "TALAL_RETAIL" not in cleaned["DepartmentName"].values


def test_group_income_rows_are_dropped(raw_df: pd.DataFrame) -> None:
    cleaned, report = clean(raw_df)
    assert report.group_income_rows_removed == 2
    assert "GROUP INCOME/EXPENSE" not in cleaned["DepartmentName"].values


def test_ghost_shop_disappears_after_cleaning(raw_df: pd.DataFrame) -> None:
    """
    ShopCode 9 only ever appears on a GROUP INCOME/EXPENSE row in the raw
    fixture (mirroring the real dataset's 6 ghost shops per CLAUDE.md).
    Once that admin row is dropped, shop 9 must vanish from the cleaned
    data's ShopCode set entirely.
    """
    assert 9 in raw_df["ShopCode"].values
    cleaned, _ = clean(raw_df)
    assert 9 not in cleaned["ShopCode"].unique()


def test_article_code_is_int64_after_cleaning(raw_df: pd.DataFrame) -> None:
    cleaned, _ = clean(raw_df)
    assert cleaned["ArticleCode"].dtype == "int64"


def test_row_count_is_measured_not_computed_by_subtraction(raw_df: pd.DataFrame) -> None:
    """
    Per the data-cleaning skill's "common mistakes" section: don't assume
    rows_after == rows_before - dupes - dummy - group_income, since a row
    could double-count across categories. Here it happens to hold exactly
    (no overlap in the fixture), but we assert `rows_after` matches the
    *actual* cleaned frame length, not an arithmetic prediction.
    """
    cleaned, report = clean(raw_df)
    assert report.rows_after == len(cleaned)
