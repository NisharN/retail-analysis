"""
Shared pytest fixtures for the Missing Winners backend test suite.

Design notes
------------
- `raw_df` is a small, hand-built synthetic dataset (not the 521k-row real
  file) so unit tests run in milliseconds. It deliberately exercises every
  rule in `.claude/skills/data-cleaning/SKILL.md`: an exact duplicate, a
  return (QtySold<0), a separate zero-sale row, a sign-mismatch anomaly, a
  string "DUMMY" ArticleCode, and a GROUP INCOME/EXPENSE row tagged with a
  "ghost" ShopCode (9) that only ever appears on that admin row -- mirroring
  the real dataset's 6 ghost shops described in CLAUDE.md.
- Revenue across the filler products (2000-2011) decays geometrically so
  the ABC cumulative-revenue curve produces a believable A/B/C split
  instead of the small-catalog edge case the abc-analysis skill warns
  about (a single dominant product folding into Class C). The resulting
  class assignments are asserted directly in test_abc_analysis.py rather
  than assumed.
- `api_client` boots the real FastAPI app (real lifespan, real /health
  state machine) but points `app.state.DEFAULT_DATA_PATH` at a tiny xlsx
  built from `raw_df` instead of `data/testdata1.xlsx`, so the ~25-30s
  load cost documented in CLAUDE.md never hits the test suite.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# --- Synthetic raw dataset -------------------------------------------------


def _build_raw_rows() -> list[dict]:
    # Geometric revenue decay across "filler" products gives a realistic
    # long-tail ABC curve, similar in shape to the real dataset.
    fillers = [50_000 * (0.78**i) for i in range(14)]

    rows: list[dict] = []

    # Article 1001: Class A, sold in shops 1/2/3 but NEVER in shop 4.
    # -> the canonical "Missing Winner" candidate for shop 4.
    for shop in (1, 2, 3):
        rows.append(
            dict(
                ShopCode=shop,
                DepartmentName="BEVERAGES",
                ArticleCode=1001,
                QtySold=100,
                SaleValue=fillers[0] / 3,
            )
        )

    # Article 1002: Class A, sold in ALL of shops 1/2/3/4, but shop 1's
    # row is far below chain average -> "Underperforming" candidate.
    rows.append(
        dict(ShopCode=1, DepartmentName="BEVERAGES", ArticleCode=1002, QtySold=2, SaleValue=50.0)
    )
    for shop in (2, 3, 4):
        rows.append(
            dict(
                ShopCode=shop,
                DepartmentName="BEVERAGES",
                ArticleCode=1002,
                QtySold=50,
                SaleValue=fillers[3] / 3,
            )
        )

    # Article 1003: high revenue but sold in only ONE shop -> must be
    # excluded by the default min_shops_selling=3 filter regardless of
    # its ABC class.
    rows.append(
        dict(ShopCode=1, DepartmentName="GROCERY", ArticleCode=1003, QtySold=200, SaleValue=fillers[1])
    )

    # Filler products 2000-2011: sold in shops 1/2/3 (never shop 4), build
    # the rest of the revenue curve (Class A tail, Class B, Class C).
    article_id = 2000
    for i in range(2, 14):
        rev = fillers[i]
        for shop in (1, 2, 3):
            rows.append(
                dict(
                    ShopCode=shop,
                    DepartmentName="GROCERY",
                    ArticleCode=article_id,
                    QtySold=10,
                    SaleValue=rev / 3,
                )
            )
        article_id += 1

    # Return (QtySold<0), zero-sale (QtySold==0 & SaleValue==0), and
    # anomaly (QtySold>0 & SaleValue<0) rows on otherwise-unused articles
    # so they don't interfere with the ABC curve above.
    rows.append(dict(ShopCode=1, DepartmentName="GROCERY", ArticleCode=9001, QtySold=-5, SaleValue=-100.0))
    rows.append(dict(ShopCode=2, DepartmentName="GROCERY", ArticleCode=9002, QtySold=0, SaleValue=0.0))
    rows.append(dict(ShopCode=3, DepartmentName="GROCERY", ArticleCode=9003, QtySold=5, SaleValue=-20.0))

    # Exact duplicate of the article 1001 / shop 1 row above.
    rows.append(
        dict(ShopCode=1, DepartmentName="BEVERAGES", ArticleCode=1001, QtySold=100, SaleValue=fillers[0] / 3)
    )

    # DUMMY non-product row (string ArticleCode, mixed dtype column).
    rows.append(dict(ShopCode=1, DepartmentName="TALAL_RETAIL", ArticleCode="DUMMY", QtySold=1, SaleValue=10.0))

    # GROUP INCOME/EXPENSE admin rows. ShopCode=9 appears ONLY here, so it
    # must vanish from the cleaned data's ShopCode set entirely (mirrors
    # the 6 real "ghost" shops in CLAUDE.md).
    rows.append(dict(ShopCode=9, DepartmentName="GROUP INCOME/EXPENSE", ArticleCode=5000, QtySold=1, SaleValue=500.0))
    rows.append(dict(ShopCode=1, DepartmentName="GROUP INCOME/EXPENSE", ArticleCode=5001, QtySold=1, SaleValue=500.0))

    return rows


@pytest.fixture
def raw_df() -> pd.DataFrame:
    """The synthetic raw dataset described in the module docstring."""
    return pd.DataFrame(_build_raw_rows())


@pytest.fixture
def pipeline_result(raw_df: pd.DataFrame):
    """Run the full Phase 1-3 pipeline (clean -> aggregate -> ABC) on raw_df."""
    from app.pipeline import (
        aggregate_chain,
        aggregate_shop_product,
        classify_abc,
        clean,
    )

    cleaned, report = clean(raw_df)
    chain_summary = classify_abc(aggregate_chain(cleaned))
    shop_product = aggregate_shop_product(cleaned)
    return dict(
        cleaned=cleaned,
        report=report,
        chain_summary=chain_summary,
        shop_product=shop_product,
    )


# --- API test client ---------------------------------------------------


@pytest.fixture
def api_client(tmp_path: Path, raw_df: pd.DataFrame, monkeypatch: pytest.MonkeyPatch):
    """
    A TestClient for the real FastAPI app, with app.state.DEFAULT_DATA_PATH
    monkeypatched to a tiny xlsx built from raw_df instead of the real
    data/testdata1.xlsx. This exercises the real lifespan/loading-state
    machinery end-to-end without paying the ~25-30s real-file cost.
    """
    from fastapi.testclient import TestClient

    from app import state as state_module
    from app.main import app

    tiny_path = tmp_path / "tiny_testdata.xlsx"
    raw_df.to_excel(tiny_path, sheet_name="testdata1", index=False)

    monkeypatch.setattr(state_module, "DEFAULT_DATA_PATH", tiny_path)

    with TestClient(app) as client:
        # The lifespan kicks off loading in a background thread; poll
        # /health until ready (the tiny file loads in well under a
        # second, so this should resolve almost immediately).
        deadline = time.time() + 10
        while time.time() < deadline:
            resp = client.get("/health")
            if resp.json().get("ready"):
                break
            time.sleep(0.05)
        else:
            pytest.fail("Tiny fixture dataset did not finish loading within 10s")

        yield client
