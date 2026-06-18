---
name: data-cleaning
description: Use this skill whenever loading, cleaning, or validating the raw sales data (testdata1.xlsx or any future export with the same ShopCode/DepartmentName/ArticleCode/QtySold/SaleValue schema) before aggregation or analysis. Covers duplicate removal, return/zero-sale/anomaly flagging, and non-product row exclusion with exact validated rules.
---

# Data Cleaning

## When to use this

Any time raw sales data is being loaded for the first time in a session, or
a new export file is being validated against the expected schema. This is
Phase 1 of the pipeline described in `CLAUDE.md` — read that file too for
the measured baseline counts on the reference dataset.

## Schema contract

Exactly 5 columns expected: `ShopCode` (int), `DepartmentName` (str),
`ArticleCode` (int, except for literal `"DUMMY"` string rows),
`QtySold` (int, can be negative or zero), `SaleValue` (float, can be
negative or zero).

If a new file doesn't match this schema, stop and report the actual columns
found rather than coercing them to fit.

## Cleaning steps, in order

1. **Drop exact duplicates.** `df.drop_duplicates()` across all columns. Log
   the count removed.

2. **Flag, don't drop, returns.** A return is `QtySold < 0` OR
   `SaleValue < 0` (these are not always the same rows — check both
   independently and flag the union). Add `IsReturn = True/False`. Returns
   affect net sales and must stay in every downstream aggregation.

3. **Flag, don't drop, zero-sales.** `QtySold == 0` OR `SaleValue == 0`.
   Add `IsZeroSale = True/False`. These represent free items, promos, or
   attempted transactions — keep them.

4. **Flag, don't drop, anomalies.** Sign mismatch between quantity and
   value: (`QtySold > 0` AND `SaleValue < 0`) OR (`QtySold < 0` AND
   `SaleValue > 0`). Add `IsAnomaly = True/False`. Keep these rows but make
   sure they're visible in any data-quality report — they may indicate a
   data entry error worth surfacing to the user, not just silently
   tolerated.

5. **Drop non-product rows.** Remove rows where `ArticleCode == "DUMMY"`
   (string comparison — this column has mixed types, so don't assume it's
   all-int) OR `DepartmentName == "GROUP INCOME/EXPENSE"`. These are
   accounting/admin entries, not real products, and should never appear in
   product-level analysis.

   Order matters: do this **after** the duplicate/flag steps above, since a
   DUMMY row could theoretically also be a duplicate, and you want the
   duplicate count to reflect the raw file, not a pre-filtered one.

6. **No date column.** Don't fabricate one. If a date filter is requested by
   a user, surface that the current dataset has no date column rather than
   making one up. Only generate synthetic dates if explicitly asked, and
   label them as synthetic everywhere they appear (UI, exports, code
   comments).

## Validation checklist after cleaning

Report all of these numbers whenever this skill runs, and compare against
`CLAUDE.md`'s recorded baseline if running against `testdata1.xlsx`
specifically:

- Rows before cleaning
- Duplicates removed
- Returns flagged (and whether by QtySold, SaleValue, or both)
- Zero-sales flagged
- Anomalies flagged
- DUMMY rows removed
- GROUP INCOME/EXPENSE rows removed
- Rows after cleaning
- Unique ArticleCode, ShopCode, DepartmentName counts after cleaning

If any number differs from a previously recorded baseline for the same
file, flag it explicitly — don't just overwrite silently, since that could
mean either the source file changed or the cleaning logic has a bug.

## Common mistakes to avoid

- Don't drop returns or zero-sales rows — they're flagged, not removed.
  Dropping them will under-count `NumShopsSelling` and skew `ChainAverage`.
- Don't compare `ArticleCode == "DUMMY"` after already casting the whole
  column to int — that cast will throw or silently produce NaN/garbage for
  the DUMMY rows. Filter the DUMMY rows first, then cast.
- Don't assume row count after cleaning by simple subtraction
  (`raw - dupes - dummy - group_income`) — there can be overlap (e.g. a
  duplicate that is also a DUMMY row). Always re-measure the final count
  directly rather than computing it arithmetically.
