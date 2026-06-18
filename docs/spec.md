# Missing Winners Analysis System — Original Spec (reference only)

> **Note:** This document is preserved verbatim as the design brief that was
> provided for this project. It has been validated against the actual
> `data/testdata1.xlsx` file. Several numbers in it are wrong or illustrative
> rather than measured — see "Known discrepancies" in `/CLAUDE.md` for the
> authoritative corrections. When this document and `CLAUDE.md` disagree,
> follow `CLAUDE.md`.

## Overview

The Missing Winners Analysis System identifies high-performing products that
are missing or underperforming in a selected store compared to the rest of
the retail chain. The system analyzes sales data, performs ABC
classification, detects assortment gaps, calculates lost revenue
opportunities, and presents actionable recommendations through an
interactive dashboard.

## Business Problem

Retail chains often have products that perform exceptionally well across
many stores but are absent or selling poorly in specific locations. These
products represent missed revenue opportunities. This system answers:

- Which products are top sellers chain-wide?
- Which of those products are missing in a selected shop?
- Which products are significantly underperforming?
- How much revenue is potentially being lost?

## System Workflow

```
RAW EXCEL → DATA CLEANING → PRODUCT AGGREGATION → ABC ANALYSIS →
SHOP GAP ANALYSIS → LOST REVENUE CALCULATION → RESULTS DASHBOARD
```

## Phase 1: Data Preparation

1.1 Load `testdata1.xlsx`, sheet `testdata1`. Spec claimed 521,102 rows / 5
columns (confirmed correct).

1.2 Remove exact duplicates via `df.drop_duplicates()`. Spec claimed 48
duplicates removed, 521,054 remaining (confirmed correct on raw drop, though
see CLAUDE.md for the order of operations relative to the other filters).

1.3 Flag returns: `QtySold < 0` (152, confirmed) or `SaleValue < 0` (196,
confirmed). New column `IsReturn = True`. Preserve these rows.

1.4 Flag zero-sales: `QtySold = 0` (1,696, confirmed) or `SaleValue = 0`
(1,630, confirmed). New column `IsZeroSale = True`. Preserve these rows.

1.5 Remove non-product entries: `ArticleCode = "DUMMY"` OR
`DepartmentName = "GROUP INCOME/EXPENSE"`.

1.6 Handle missing dates: dataset has no date column. Option A (current):
treat entire dataset as one period. Option B (future): generate synthetic
dates distributing rows across 90 days — **do not implement this without
explicit user request, and always label any synthetic dates as synthetic.**

1.7 Data validation: flag rows where sign of `QtySold` and `SaleValue`
disagree. Spec claimed 5 anomalous rows (confirmed correct). New column
`IsAnomaly = True`. Keep rows.

## Phase 2: Product Aggregation

2.1 Chain-wide product summary, grouped by `ArticleCode`:
`TotalQtySold = SUM(QtySold)`, `TotalSaleValue = SUM(SaleValue)`,
`NumShopsSelling = COUNT(DISTINCT ShopCode)`,
`AvgSaleValuePerShop = TotalSaleValue / NumShopsSelling`.

2.2 Product performance by shop, grouped by `ShopCode + ArticleCode`:
`ShopQtySold = SUM(QtySold)`, `ShopSaleValue = SUM(SaleValue)`.

## Phase 3: ABC Analysis

3.1 Rank products by `TotalSaleValue DESC`.

3.2 Cumulative revenue % = running total / total revenue × 100.

3.3 Assign classes: A = top 70% of cumulative revenue, B = next 20%
(70–90%), C = remaining 10% (90–100%).

Business meaning: Class A = top revenue drivers, must always be stocked.
Class B = strong sellers, should generally be available. Class C = long-tail,
lower priority.

**Spec's "Expected Distribution" (A: 1,500–2,000, B: 2,000–3,500,
C: 9,000–11,000) is wrong for this dataset** — see CLAUDE.md for the actual
measured distribution (A≈1,953, B≈8,140, C≈59,912 out of 70,005 products).

Only A and B products are used for gap detection.

## Phase 4: Gap Detection Engine

User filters: Shop (e.g. 184), Department (e.g. BEVERAGES), ABC Classes
(A+B), Minimum Shops Selling (≥3), Gap Threshold (<20%).

Logic per product: skip if not in selected department; skip if
`NumShopsSelling < MinShopsSelling`; if shop has no sales → Missing Winner;
else if `ShopSales < GapThreshold × ChainAverage` → Underperforming; else OK.

Missing Winner: `ShopSaleValue = 0`. Underperforming:
`ShopSaleValue < 20% × ChainAverage` (configurable).

Gap Score = `(ChainAvgSaleValue - ShopSaleValue) / ChainAvgSaleValue`.

Potential Lost Revenue = `ChainAvgSaleValue - ShopSaleValue`.

## Phase 5: Ranking & Reporting

5.1 Rank opportunities descending by `PotentialLostRevenue`.

5.2 Executive Dashboard KPIs: Missing Winners count, Potential Revenue
total, Class A Gaps, Class B Gaps. **The sample numbers in the spec (23
missing winners, $287,500, 8 Class A gaps, 15 Class B gaps) are illustrative
mockup numbers, not measured outputs — do not hardcode them as test
fixtures.**

5.3 Export: Excel (full detailed analysis), PDF (executive summary report).

## Web Application Design (wireframes, illustrative)

Screen 1 — Upload: shows file loaded, row count, **"30 Departments"** — this
count is wrong, the actual file has 41 departments.

Screen 2 — Filters: Shop dropdown, Department dropdown, ABC checkboxes, Min
Shops dropdown, Gap Limit dropdown, "Find Missing Winners" button.

Screen 3 — Results: KPI header (count + $ opportunity) + results table
(Product, ABC, Gap %, Revenue Lost).

## Technology Stack (as proposed; see CLAUDE.md for actual decisions)

Frontend: Next.js, React, TypeScript, Tailwind CSS, ShadCN UI, Recharts.
Backend: FastAPI or Node.js, Pandas, NumPy. Database (optional): PostgreSQL
or SQLite. Export: OpenPyXL, XlsxWriter, ReportLab.

## Expected Business Impact

Identify missing best-selling products, detect assortment gaps, increase
store revenue, improve inventory decisions, standardize product availability
across locations. By focusing on Class A and Class B products, the system
prioritizes the highest-impact opportunities.
