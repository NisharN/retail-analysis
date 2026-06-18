"""
Tests for `app.pipeline.aggregate_chain` and `aggregate_shop_product` —
Phase 2 product aggregation.
"""
from __future__ import annotations

import pandas as pd
import pytest


def test_chain_summary_has_one_row_per_article(pipeline_result: dict) -> None:
    chain = pipeline_result["chain_summary"]
    cleaned = pipeline_result["cleaned"]
    assert len(chain) == cleaned["ArticleCode"].nunique()
    assert chain["ArticleCode"].is_unique


def test_chain_summary_totals_match_raw_sums(pipeline_result: dict) -> None:
    chain = pipeline_result["chain_summary"]
    cleaned = pipeline_result["cleaned"]

    article_1001 = chain[chain["ArticleCode"] == 1001].iloc[0]
    raw_total = cleaned[cleaned["ArticleCode"] == 1001]["SaleValue"].sum()
    assert article_1001["TotalSaleValue"] == pytest.approx(raw_total)

    # Article 1001 sells in shops 1, 2, 3 only (never shop 4).
    assert article_1001["NumShopsSelling"] == 3


def test_avg_sale_value_per_shop_uses_num_shops_selling_not_total_shops(
    pipeline_result: dict,
) -> None:
    """
    Per CLAUDE.md / gap-detection skill: ChainAvgSaleValue must divide by
    NumShopsSelling (shops that actually carry the product), not the
    total shop count in the chain. Article 1003 sells in exactly 1 shop.
    """
    chain = pipeline_result["chain_summary"]
    row = chain[chain["ArticleCode"] == 1003].iloc[0]
    assert row["NumShopsSelling"] == 1
    assert row["AvgSaleValuePerShop"] == pytest.approx(row["TotalSaleValue"])


def test_shop_product_summary_has_one_row_per_shop_article_pair(
    pipeline_result: dict,
) -> None:
    shop_product = pipeline_result["shop_product"]
    cleaned = pipeline_result["cleaned"]
    expected_pairs = cleaned.groupby(["ShopCode", "ArticleCode"]).ngroups
    assert len(shop_product) == expected_pairs


def test_shop_product_summary_excludes_absent_shop_article_pairs(
    pipeline_result: dict,
) -> None:
    """
    Article 1001 never has a row for shop 4 in the cleaned data, so the
    shop x product summary must NOT contain a (4, 1001) row at all — its
    absence is what signals "missing winner" downstream, not a zero-value
    row.
    """
    shop_product = pipeline_result["shop_product"]
    match = shop_product[
        (shop_product["ShopCode"] == 4) & (shop_product["ArticleCode"] == 1001)
    ]
    assert match.empty


def test_returns_and_zero_sales_count_toward_aggregation(pipeline_result: dict) -> None:
    """
    Flagged rows (returns/zero-sales/anomalies) must still contribute to
    NumShopsSelling and TotalSaleValue — they are flagged, not excluded,
    per the data-cleaning skill.
    """
    chain = pipeline_result["chain_summary"]
    # Article 9001 is a pure return row (QtySold=-5, SaleValue=-100) and
    # must still appear in the chain summary with its negative value
    # intact (not dropped, not zeroed).
    row = chain[chain["ArticleCode"] == 9001]
    assert len(row) == 1
    assert row.iloc[0]["TotalSaleValue"] == pytest.approx(-100.0)
    assert row.iloc[0]["NumShopsSelling"] == 1
