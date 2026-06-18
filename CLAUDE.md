# Missing Winners Analysis System — Project Memory

This file is read by Claude Code at the start of every session in this repo.
It encodes facts that have been **validated against the actual data**, not
just assumed from the original spec. Where the spec (`docs/spec.md`) and the
real dataset disagree, the real dataset wins — note the discrepancies below.

## What this project is

A tool for retail category managers: given chain-wide sales data across many
shops, find products that sell well across the chain but are missing or
under-selling in one specific shop ("missing winners"), rank them by lost
revenue opportunity, and surface them in a filterable dashboard.

Original one-line brief (from the person who commissioned this, found in
`Sheet1` of the source workbook): *"Are my branches readily stocking my
popular products?"* — find products that are top sellers overall but don't
show sales at a selected shop code, using ABC analysis.

## Source data — validated facts

File: `data/testdata1.xlsx`, sheet `testdata1` (there is also a `Sheet1`
containing the original task brief as plain text — not data, don't parse it
as a dataframe).

Columns (exactly 5, confirmed via `pd.read_excel`):

| Column | dtype | Notes |
|---|---|---|
| ShopCode | int64 | range 102–197, **80 distinct shops** |
| DepartmentName | str | **41 distinct departments**, not 30 as the original spec's mockup claims |
| ArticleCode | int64 / str | mostly int64; **74 rows have the literal string `"DUMMY"`**, all under `DepartmentName == "TALAL_RETAIL"` |
| QtySold | int64 | can be negative (returns) or zero |
| SaleValue | float64 | can be negative (returns) or zero |

Validated counts on the raw file (521,102 rows, 5 columns) — these have
been confirmed twice: once by direct inspection, and once by actually
running `backend/app/pipeline.py` end to end against the file:

- Exact duplicate rows: **48** → drop with `df.drop_duplicates()`.
- Returns: `QtySold < 0` alone is **152** rows; `SaleValue < 0` alone is
  **196** rows; these are *not* the same 152/196 rows, and `IsReturn` should
  be the **union** (`QtySold<0 OR SaleValue<0`), which is **198** rows
  total. Don't report 152 or 196 as "the" return count — those are the two
  sub-conditions, not the flag total.
- Zero-sales: `QtySold == 0` alone is **1,696**; `SaleValue == 0` alone is
  **1,630**; the union `IsZeroSale` (`QtySold==0 OR SaleValue==0`) is
  **1,706** rows total. Same caveat as above — 1,696/1,630 are
  sub-conditions, not the flag total.
- Anomalous rows (`QtySold>0 & SaleValue<0` or `QtySold<0 & SaleValue>0`):
  **5** → flag with `IsAnomaly = True`, keep.
- `ArticleCode == "DUMMY"` (string comparison): **74** rows, all under
  `DepartmentName == "TALAL_RETAIL"` → non-product/admin rows, **drop**.
- `DepartmentName == "GROUP INCOME/EXPENSE"`: **382** rows after dedup (a
  few of the raw count's "405-ish" rows were duplicates already removed in
  step 1 — always measure this post-dedup, don't hardcode either number) →
  non-product/admin rows, **drop**.
- No nulls in any column.
- **Confirmed by running the actual pipeline:** after dedup + dropping
  DUMMY + dropping GROUP INCOME/EXPENSE, **520,598** rows remain, with
  **69,993** unique `ArticleCode`, **74** unique `ShopCode` (not 80 — 6 shop
  codes apparently only ever appear in dropped rows, e.g. GROUP
  INCOME/EXPENSE entries), and **39** unique `DepartmentName` (down from 41
  raw, since DUMMY's department `TALAL_RETAIL` and `GROUP INCOME/EXPENSE`
  itself both disappear once those rows are dropped).
- Always re-run `/data-pipeline` to re-verify these numbers rather than
  trusting this table blindly if the cleaning logic changes at all.

## Known discrepancies between `docs/spec.md` and reality — trust this section

1. **No date column exists anywhere in the data.** The original brief
   (Sheet1) asks for a "date range" filter, and the spec's screen mockups
   imply a single reporting period. There is no way to filter by date with
   this file. Do not invent a date column or silently fabricate one. Phase
   1.6 "Option B: synthetic dates" in the spec is explicitly **not** to be
   implemented unless the user asks for it — and if asked, it must be
   clearly labeled as synthetic/demo data, never presented as real.
2. **41 departments raw, 39 after cleaning** — not 30 as the spec's mockup
   claims. Don't hardcode either 30 or 41 in code; always derive the count
   from the cleaned data.
3. **ABC distribution is far more long-tail than the spec assumed.**
   Measured on the cleaned dataset (520,598 rows, 69,993 products): Class A
   = 1,985 products, Class B = 8,196, Class C = 59,812. The spec's "Expected
   Distribution" table (B: 2,000–3,500, C: 9,000–11,000) is wrong — it
   assumed a much smaller catalog. Build the ABC engine generically
   (cumulative % of revenue, thresholds at 70/90), don't bake in expected
   counts anywhere.
4. **74 DUMMY rows are strings, not the integer dtype the rest of the column
   uses.** Read `ArticleCode` as a generic object/string column when
   cleaning, then decide whether to cast to int *after* dropping DUMMY rows
   — otherwise `pd.read_excel`/dtype inference can throw or silently coerce.
5. **6 shop codes (120, 129, 131, 173, 177, 185) have zero real product
   rows** — in the raw file they only ever appear on `GROUP INCOME/EXPENSE`
   rows (8 rows total across all 6), so once those admin rows are dropped
   in cleaning, these shops vanish from the cleaned dataset entirely. The
   shop dropdown in the UI must be populated from the **cleaned** data (74
   shops), not the raw file's 80, or a user could select one of these 6
   "ghost" shops and get a confusing empty result instead of a clear
   "this shop has no product data" message.
6. Sample KPI numbers in the spec (23 missing winners, $287,500 opportunity,
   shop 184, dept BEVERAGES) are illustrative mock numbers from the spec
   author, not verified outputs of this dataset. Don't treat them as ground
   truth or test fixtures — generate real fixtures from the actual data
   instead (see `scripts/`).

## Architecture decisions

- **Performance note, measured:** `pd.read_excel` on the 521k-row file takes
  roughly 25-30 seconds — this is the dominant cost, not the cleaning or
  aggregation (which together run in well under a second). Load and cache
  the cleaned dataframe + both aggregation tables + ABC classification
  **once** at backend startup (or once per file upload), never per-request.
  Gap detection itself (`detect_gaps`) runs in ~0.1s once the cached tables
  exist, so the API should feel instant after the initial load — show a
  loading state on first upload, not on every filter change.
- **Frontend:** React + TypeScript + Tailwind, calling the FastAPI backend's
  JSON endpoints. Keep it simple — a filter panel (shop, department, ABC
  class, min shops selling, gap threshold) and a results table, per the
  spec's Screen 2 / Screen 3 mockups. No need for Next.js SSR for a single
  internal analytics tool; plain Vite + React is enough unless the user asks
  for Next.js specifically.
- **No database required** for the current dataset size (521k rows fits
  comfortably in memory as a pandas DataFrame, well under a second to
  groupby). Don't add Postgres/SQLite unless the user explicitly wants
  persistence across server restarts or multi-file history.
- Export: `openpyxl`/`XlsxWriter` for Excel export, `reportlab` for PDF
  summary — only build these once the core analysis + dashboard work, they
  are not on the critical path.

## Conventions

- All money figures are in whatever currency `SaleValue` is in — the dataset
  doesn't specify currency. Don't assume USD in UI copy; just show the raw
  number or a generic currency symbol the user can configure.
- Gap Score formula: `(ChainAvgSaleValue - ShopSaleValue) / ChainAvgSaleValue`,
  clamped to `[0, 1]` for display as a percentage. `ChainAvgSaleValue` for a
  product = `TotalSaleValue / NumShopsSelling` (only counting shops where the
  product has a sales row at all — a shop with zero rows for that product is
  the "missing" case, distinct from a shop with a sales row of 0).
- "Missing Winner" = product is Class A or B chain-wide, sells in
  `NumShopsSelling >= MinShopsSelling` shops, and has **no row at all** for
  the selected shop (or a row with `ShopSaleValue == 0`, after deciding which
  definition the user wants — clarify if ambiguous, the spec uses
  `ShopSaleValue = 0` which conflates "never stocked" with "stocked but sold
  nothing"; consider exposing both as separate flags).
- "Underperforming" = has a row in the selected shop with
  `0 < ShopSaleValue < GapThreshold × ChainAvgSaleValue`.
- Run `pytest backend/tests` before considering any backend change done.
- Run the data-cleaning pipeline against `data/testdata1.xlsx` as the
  integration test fixture — see `/data-pipeline` command and the
  `data-cleaning` skill.

## Commands & skills

- Slash commands live in `.claude/commands/` — see `/data-pipeline`,
  `/run-backend`, `/run-frontend`, `/add-feature`.
- Skills live in `.claude/skills/` — `data-cleaning`, `abc-analysis`,
  `gap-detection` encode the exact business rules above so they're applied
  consistently instead of re-derived each time.
- Full original spec preserved verbatim at `docs/spec.md` for reference, but
  this file overrides it wherever they conflict.
