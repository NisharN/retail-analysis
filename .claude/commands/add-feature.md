---
description: Plan and implement a new feature end-to-end (backend endpoint + frontend UI), following project conventions in CLAUDE.md
---

Feature request: $ARGUMENTS

Before writing code:

1. Re-read `CLAUDE.md` for the relevant business rules (gap detection, ABC
   classification, missing-winner definition) so the implementation matches
   the documented logic exactly, not a re-derived version of it.
2. Check whether the feature touches the data pipeline (`backend/app/pipeline.py`),
   the API layer (`backend/app/main.py` / routers), or only the frontend, and
   scope the plan accordingly.
3. If the feature is ambiguous (e.g. unclear which "missing winner"
   definition to use, or what should happen when a filter combination
   returns zero results), state the ambiguity and your chosen interpretation
   explicitly rather than guessing silently.

Then implement:

- Backend changes first, with a corresponding test in `backend/tests/`
  that exercises the new logic against `data/testdata1.xlsx` (or a small
  synthetic fixture if the real file is too slow for a unit test).
- Frontend changes second, wiring up to the new/changed endpoint.
- Run `pytest backend/tests` and confirm the frontend builds
  (`npm run build` in `frontend/`) before considering the feature done.

Report back: what changed, what you decided about any ambiguity, and what
manual testing (if any) is still recommended before shipping.
