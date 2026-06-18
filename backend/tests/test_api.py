"""
HTTP-level integration tests for the Missing Winners API.

Uses the `api_client` fixture (conftest.py), which boots the real FastAPI
app + lifespan against a tiny synthetic xlsx instead of the real
data/testdata1.xlsx, so these run in well under a second per test instead
of paying the ~25-30s real-file load cost documented in CLAUDE.md.
"""
from __future__ import annotations

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient


def test_health_reports_ready_after_load(api_client: TestClient) -> None:
    resp = api_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["status"] == "ok"
    assert body["dataset_loaded"] is True
    assert body["load_error"] is None


def test_summary_reports_cleaning_counts(api_client: TestClient) -> None:
    resp = api_client.get("/api/summary")
    assert resp.status_code == 200
    body = resp.json()
    # From the synthetic fixture: 51 raw rows, 1 duplicate, 1 dummy, 2
    # group-income rows removed -> 47 rows after cleaning.
    assert body["cleaning"]["rows_before"] == 51
    assert body["cleaning"]["duplicates_removed"] == 1
    assert body["cleaning"]["rows_after"] == 47
    assert body["abc_distribution"]["total"] == body["total_products"]
    assert body["total_revenue"] > 0


def test_shops_endpoint_excludes_ghost_shop(api_client: TestClient) -> None:
    resp = api_client.get("/api/shops")
    assert resp.status_code == 200
    codes = [s["code"] for s in resp.json()]
    assert sorted(codes) == [1, 2, 3, 4]
    assert 9 not in codes  # ghost shop, only ever on a GROUP INCOME/EXPENSE row


def test_departments_endpoint_excludes_dropped_departments(api_client: TestClient) -> None:
    resp = api_client.get("/api/departments")
    assert resp.status_code == 200
    names = {d["name"] for d in resp.json()}
    assert names == {"BEVERAGES", "GROCERY"}
    assert "TALAL_RETAIL" not in names
    assert "GROUP INCOME/EXPENSE" not in names


def test_gaps_for_shop_4_returns_missing_winners(api_client: TestClient) -> None:
    resp = api_client.get("/api/gaps", params={"shop": 4})
    assert resp.status_code == 200
    body = resp.json()
    article_codes = {r["ArticleCode"] for r in body["rows"]}
    assert 1001 in article_codes
    row = next(r for r in body["rows"] if r["ArticleCode"] == 1001)
    assert row["Status"] == "Missing Winner"
    assert row["NeverStocked"] is True
    assert body["kpis"]["missing_winners"] >= 1
    assert body["kpis"]["total_gaps"] == len(body["rows"])


def test_gaps_for_shop_1_returns_underperforming(api_client: TestClient) -> None:
    resp = api_client.get("/api/gaps", params={"shop": 1})
    assert resp.status_code == 200
    body = resp.json()
    row = next(r for r in body["rows"] if r["ArticleCode"] == 1002)
    assert row["Status"] == "Underperforming"
    assert row["NeverStocked"] is False


def test_gaps_rejects_ghost_shop_with_400(api_client: TestClient) -> None:
    resp = api_client.get("/api/gaps", params={"shop": 9})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "shop_not_in_cleaned_data"


def test_gaps_rejects_unknown_department_with_400(api_client: TestClient) -> None:
    resp = api_client.get("/api/gaps", params={"shop": 1, "department": "NOT_A_REAL_DEPT"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "unknown_department"


def test_gaps_rejects_invalid_abc_class_with_400(api_client: TestClient) -> None:
    resp = api_client.get("/api/gaps", params={"shop": 1, "abc_classes": "Z"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "invalid_abc_classes"


def test_gaps_respects_department_filter(api_client: TestClient) -> None:
    resp = api_client.get("/api/gaps", params={"shop": 4, "department": "BEVERAGES"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(r["DepartmentName"] == "BEVERAGES" for r in body["rows"])


def test_gaps_respects_limit_param(api_client: TestClient) -> None:
    resp = api_client.get("/api/gaps", params={"shop": 4, "limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["rows"]) == 1


def test_export_xlsx_returns_valid_workbook(api_client: TestClient) -> None:
    resp = api_client.get("/api/gaps/export.xlsx", params={"shop": 4})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert resp.content[:2] == b"PK"


def test_export_pdf_returns_valid_pdf(api_client: TestClient) -> None:
    resp = api_client.get("/api/gaps/export.pdf", params={"shop": 4})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"


def test_upload_rejects_non_xlsx_with_415(api_client: TestClient) -> None:
    resp = api_client.post(
        "/api/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 415
    assert resp.json()["detail"]["error"] == "unsupported_file_type"


def test_upload_rejects_empty_file_with_422(api_client: TestClient) -> None:
    resp = api_client.post(
        "/api/upload",
        files={"file": ("empty.xlsx", io.BytesIO(b""), "application/octet-stream")},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "empty_file"


def test_upload_rejects_missing_columns_with_422(api_client: TestClient) -> None:
    bad_df = pd.DataFrame({"ShopCode": [1], "ArticleCode": [100]})  # missing 3 columns
    buf = io.BytesIO()
    bad_df.to_excel(buf, sheet_name="testdata1", index=False)
    buf.seek(0)
    resp = api_client.post(
        "/api/upload",
        files={"file": ("bad_schema.xlsx", buf, "application/octet-stream")},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "invalid_schema"


def test_upload_replaces_state_and_gaps_reflect_new_data(api_client: TestClient) -> None:
    """
    After a successful upload, /api/gaps should reflect the NEW dataset,
    not the original fixture -- proves the atomic state swap actually
    takes effect for subsequent requests.
    """
    new_rows = [
        dict(ShopCode=10, DepartmentName="BAKERY", ArticleCode=42, QtySold=5, SaleValue=100.0),
        dict(ShopCode=11, DepartmentName="BAKERY", ArticleCode=42, QtySold=5, SaleValue=100.0),
        dict(ShopCode=12, DepartmentName="BAKERY", ArticleCode=42, QtySold=5, SaleValue=100.0),
    ]
    new_df = pd.DataFrame(new_rows)
    buf = io.BytesIO()
    new_df.to_excel(buf, sheet_name="testdata1", index=False)
    buf.seek(0)

    resp = api_client.post(
        "/api/upload",
        files={"file": ("replacement.xlsx", buf, "application/octet-stream")},
    )
    assert resp.status_code == 200
    assert resp.json()["rows_replaced"] is True

    # Old shop 1 from the original fixture should no longer validate.
    resp_old_shop = api_client.get("/api/gaps", params={"shop": 1})
    assert resp_old_shop.status_code == 400

    # New shop 10 should now be queryable.
    resp_new_shop = api_client.get("/api/gaps", params={"shop": 10, "min_shops_selling": 1})
    assert resp_new_shop.status_code == 200
