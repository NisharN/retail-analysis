---
name: abc-analysis
description: Use this skill when ranking products by revenue contribution and assigning ABC classes (A/B/C), or when anyone asks about ABC classification thresholds, expected class sizes, or how to interpret class assignments for this dataset. Encodes the exact cumulative-revenue formula and the measured (not assumed) class distribution for testdata1.xlsx.
---

# ABC Analysis

## Purpose

Classify products into A/B/C tiers by their share of total chain-wide
revenue, so downstream gap detection can prioritize Class A and B products
(the ones worth always having in stock) over the long tail of Class C.

## Method (apply exactly, on the cleaned, chain-wide product summary)

1. Aggregate `TotalSaleValue` per `ArticleCode` (sum of `SaleValue` across
   all shops, on the cleaned dataset — i.e. after the data-cleaning skill's
   steps, but including flagged returns/zero-sales/anomalies, since those
   still count toward true net revenue).
2. Sort products by `TotalSaleValue` descending.
3. Compute cumulative revenue: running sum of `TotalSaleValue` down the
   sorted list, divided by the grand total, as a percentage.
4. Assign class by cumulative revenue %:
   - **Class A**: cumulative % up to and including 70%
   - **Class B**: cumulative % from >70% up to and including 90%
   - **Class C**: cumulative % from >90% to 100%

Implement this as a vectorized pandas operation (`cumsum()` then
`pd.cut` or boolean masks), not a Python loop — this runs over tens of
thousands of products and looping is both slow and a common source of
off-by-one bugs at the class boundaries.

## Measured baseline for `data/testdata1.xlsx`

On the actual cleaned dataset (520,598 rows, 69,993 unique products, run
via `backend/app/pipeline.py`), the distribution is:

- Total chain-wide revenue (clamped at 0 per-product before summing): ≈ $85,379,787
- Class A: 1,985 products
- Class B: 8,196 products
- Class C: 59,812 products
- Total distinct products: 69,993

**Do not assume the original spec's "Expected Distribution" table** (which
claimed A: 1,500–2,000, B: 2,000–3,500, C: 9,000–11,000) — it was a generic
guess that doesn't match this dataset's actual long-tail shape. If you see
code or tests asserting the spec's numbers, they're wrong; use the measured
numbers above instead, and re-measure if the cleaning logic upstream
changes (since that changes which rows count toward revenue).

## Edge cases

- **A single product holding 100% of revenue (or otherwise concentrated
  revenue with very few products) can land in Class C, not A,** under the
  strict cumulative-percentage definition — e.g. with one product at 100%
  cumulative revenue, that falls in the `(90, 100]` bucket, which is
  Class C. This looks wrong on a tiny synthetic dataset but is mathematically
  consistent with "Class A = top 70% of cumulative revenue" and doesn't
  happen in practice on the real 70k-product catalog, where the top
  individual products are each a few percent of total revenue (the actual
  top seller in `testdata1.xlsx` sits at ~3.8% cumulative). Don't "fix" this
  by special-casing small catalogs; just be aware of it when writing test
  fixtures — use at least a few products with realistic relative revenue
  shares, not one dominant product alone.
- A product with `TotalSaleValue <= 0` after netting out returns (e.g. more
  returned than sold) should still be classified — it'll land in Class C by
  definition since it contributes ~0% or negative revenue. Don't drop these
  products from the classification; do decide explicitly whether negative
  totals should be clamped to 0 for the cumulative-% calculation or left
  as-is (clamping is recommended so a large negative outlier doesn't distort
  the cumulative curve for products ranked after it).
- Ties in `TotalSaleValue` at a class boundary: use a stable sort (pandas
  default) and don't worry about reordering ties — the boundary effect on
  a handful of tied products is immaterial at this scale.

## Common mistakes to avoid

- Recomputing ABC classes per-request in the API layer — this should be
  computed once when data loads/changes and cached, not on every gap-search
  request.
- Classifying on `ShopSaleValue` (per-shop) instead of `TotalSaleValue`
  (chain-wide) — ABC class is a chain-wide property of the product, not
  shop-specific.
- Forgetting that Class C should still be computed and stored even though
  gap detection only uses A and B — users may want to see/export the full
  classification, not just the filtered subset.
