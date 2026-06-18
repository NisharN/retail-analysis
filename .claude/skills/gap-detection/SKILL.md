---
name: gap-detection
description: Use this skill when implementing or modifying the core "missing winners" logic - determining whether a product is missing, underperforming, or OK at a selected shop, computing gap scores, and calculating potential lost revenue. This is the central business logic of the whole system; apply these exact definitions rather than re-deriving them.
---

# Gap Detection Engine

## Inputs

- A selected `ShopCode`.
- Optional filters: `DepartmentName`, ABC classes to include (default A+B),
  `MinShopsSelling` (default 3), `GapThreshold` (default 0.20, i.e. 20%).
- The chain-wide product summary (from abc-analysis: `TotalSaleValue`,
  `NumShopsSelling`, ABC class per `ArticleCode`).
- The shop×product summary (`ShopSaleValue`, `ShopQtySold` per
  `ShopCode`+`ArticleCode` pair — only pairs that actually have a row;
  absence of a row is meaningful, see below).

## Core logic, per candidate product

Apply filters first to cut down the candidate set, then classify:

```
for each ArticleCode where ABCClass in selected_classes
                       and NumShopsSelling >= MinShopsSelling
                       and (no department filter, or DepartmentName matches):

    ChainAvgSaleValue = TotalSaleValue / NumShopsSelling

    look up (ShopCode, ArticleCode) in the shop×product summary:

    if no row exists for this shop:
        status = "Missing Winner"
        ShopSaleValue = 0           # for display/scoring purposes only —
                                     # this is "never sold here", distinct
                                     # from "sold here, but $0"
    elif ShopSaleValue == 0:
        status = "Missing Winner"   # row exists but literally zero revenue
    elif ShopSaleValue < GapThreshold * ChainAvgSaleValue:
        status = "Underperforming"
    else:
        status = "OK" (exclude from results)
```

**Important distinction the original spec glossed over:** "no row at all for
this shop" and "a row with `ShopSaleValue == 0`" are different situations —
the first means the product was likely never stocked there, the second
means it was stocked but didn't sell (possibly due to the zero-sale flag
from data-cleaning, e.g. a promo item). Both count as "Missing Winner" for
the purposes of this tool, but if building a detailed view, expose which
case it was (e.g. a `NeverStocked: bool` field) since it changes the
recommended action (start stocking it, vs. investigate why it's not
moving).

## Gap Score

```
GapScore = (ChainAvgSaleValue - ShopSaleValue) / ChainAvgSaleValue
```

Clamp to `[0, 1]` before displaying as a percentage (a shop selling *above*
chain average for a product it does carry would otherwise produce a
negative gap score, which is meaningless in this context and should just
not appear in results since it's not a gap at all).

## Potential Lost Revenue

```
PotentialLostRevenue = ChainAvgSaleValue - ShopSaleValue
```

This is the headline metric for ranking and for the KPI summary. Sum it
across all returned rows for the "Potential Revenue" KPI.

## Output ranking

Sort descending by `PotentialLostRevenue`. This is the single most
important sort for the results table — category managers care most about
the biggest dollar opportunities, not the highest percentage gaps (a 100%
gap on a $50 average product matters less than an 85% gap on a $5,000
average product).

## KPI summary fields

- Total count of Missing Winners (status == "Missing Winner")
- Total count of Underperforming
- Sum of PotentialLostRevenue across all returned rows ("Potential Revenue")
- Count broken down by ABC class ("Class A Gaps", "Class B Gaps")

## Common mistakes to avoid

- Computing `ChainAvgSaleValue` using all 80 shops in the chain instead of
  only `NumShopsSelling` (the shops that actually carry the product) — this
  would understate the true average for products that aren't universally
  stocked, which is the majority of products in this dataset.
- Re-running the full chain-wide ABC computation inside the gap-detection
  request handler — ABC classes should already be precomputed and just
  joined/filtered here.
- Iterating row-by-row in Python over the ~70,000-product candidate set
  instead of using vectorized pandas filtering/merging. With 80 shops ×
  70,005 products as the theoretical join space, this needs to stay
  vectorized to be responsive in a web UI.
- Treating `MinShopsSelling` as a department-level filter — it's a
  per-product threshold on `NumShopsSelling` (chain-wide), applied before
  any department filtering.
