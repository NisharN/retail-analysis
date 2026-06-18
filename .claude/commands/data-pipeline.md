---
description: Run the data cleaning + aggregation + ABC pipeline against data/testdata1.xlsx and report row counts at each stage
allowed-tools: Bash(python3:*), Read, Write
---

Run the full data preparation pipeline described in `CLAUDE.md` (Phase 1 and
Phase 2) against `data/testdata1.xlsx`, sheet `testdata1`. Specifically:

1. Load the raw file with pandas.
2. Drop exact duplicates, report the count removed.
3. Flag returns (`IsReturn`), zero-sales (`IsZeroSale`), and anomalies
   (`IsAnomaly`) as described in CLAUDE.md — do not drop these rows.
4. Drop `ArticleCode == "DUMMY"` and `DepartmentName == "GROUP INCOME/EXPENSE"`
   rows.
5. Build the chain-wide product summary (group by `ArticleCode`) and the
   shop×product summary (group by `ShopCode` + `ArticleCode`).
6. Run ABC classification on the chain-wide summary.
7. Print a report: rows at each stage, counts of each flag, ABC class
   distribution (A/B/C counts and % of total revenue each class
   represents).

Compare every number you produce against the validated figures already
recorded in `CLAUDE.md`. If anything differs, stop and explain the
discrepancy before continuing — don't silently proceed with different
numbers than what's documented.

If `backend/app/pipeline.py` (or equivalent) doesn't exist yet, write it as a
reusable module rather than a one-off script, since this same logic will be
called by the FastAPI backend on every file upload.

Argument (optional): $ARGUMENTS — a path to a different Excel file to run
the pipeline against instead of the default test data, useful for testing
with a fresh export. If given, validate it has the same 5 columns before
proceeding and call out any structural differences.
