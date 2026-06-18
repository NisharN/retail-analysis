---
description: Start (or restart) the FastAPI backend locally for development
allowed-tools: Bash(uvicorn:*), Bash(pip install:*), Bash(python3:*)
---

Start the FastAPI backend defined in `backend/app/main.py` with
auto-reload, on port 8000. If dependencies aren't installed yet, install
from `backend/requirements.txt` first (remember `--break-system-packages`
when using pip in this environment).

Before starting, run a quick import check
(`python3 -c "import backend.app.main"`) so import errors surface clearly
rather than as a uvicorn traceback. If the import fails, fix it before
attempting to start the server.

Once running, hit `GET /health` and `GET /api/summary` (or whatever the
current summary endpoint is called) to confirm the pipeline loaded data
successfully, and report the response.

Argument (optional): $ARGUMENTS — a different port number if 8000 is in use.
