---
description: Install deps (if needed) and start the frontend dev server
allowed-tools: Bash(npm:*), Bash(npx:*)
---

In `frontend/`, install dependencies if `node_modules` doesn't exist yet
(`npm install`), then start the Vite dev server (`npm run dev`).

Confirm the backend is reachable first — check `backend/app/main.py` for the
configured CORS origins and make sure the frontend's API base URL
(`frontend/src/lib/api.ts` or equivalent) points at the right backend port.
If the backend isn't running, say so and suggest `/run-backend` rather than
starting the frontend against a dead API.

Argument (optional): $ARGUMENTS — passed through to `npm run dev -- $ARGUMENTS`
(e.g. a different port).
