"""
Project-wide configuration constants.

Centralizes paths, defaults, and external-facing limits so the rest of the
backend never hardcodes magic numbers. Importable as `from backend.app.config
import DEFAULT_DATA_PATH` etc.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"

# Default source data file. Pre-loaded at backend startup.
DEFAULT_DATA_PATH: Final[Path] = DATA_DIR / "testdata1.xlsx"
DEFAULT_SHEET: Final[str] = "testdata1"

# Default gap-detection filters (see .claude/skills/gap-detection/SKILL.md).
DEFAULT_MIN_SHOPS_SELLING: Final[int] = 3
DEFAULT_GAP_THRESHOLD: Final[float] = 0.20
DEFAULT_ABC_CLASSES: Final[tuple[str, ...]] = ("A", "B")

# Hard cap on rows returned by /api/gaps so a runaway query can't OOM the
# server. 5,000 is well above what fits in any reasonable UI table and
# comfortably below memory limits.
MAX_GAP_ROWS: Final[int] = 5_000

# Maximum upload size for POST /api/upload (100 MB). The reference file
# is 14 MB; allow generous headroom for future exports.
MAX_UPLOAD_BYTES: Final[int] = 100 * 1024 * 1024

# CORS allowlist. Vite default = 5173, Next.js default = 3000.
CORS_ORIGINS: Final[tuple[str, ...]] = (
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
)
