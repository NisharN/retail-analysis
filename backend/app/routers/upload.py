"""
File-upload endpoint.

Accepts a `.xlsx` multipart upload, re-runs the pipeline, and atomically
swaps the in-memory state. The user's UI shows a loading spinner during
the ~25-30s pipeline run.

Validation:
  - Extension must be `.xlsx` (415 otherwise).
  - Content-Length <= MAX_UPLOAD_BYTES (413 otherwise).
  - Schema must contain the 5 required columns (422 from pipeline ValueError).
"""
from __future__ import annotations

import logging
import tempfile
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from ..config import MAX_UPLOAD_BYTES
from ..schemas import CleaningReport, UploadResponse
from ..state import reload_from_path

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])


@router.post(
    "/api/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload(file: UploadFile = File(...)) -> UploadResponse:
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error": "unsupported_file_type",
                "filename": filename,
                "allowed": [".xlsx"],
            },
        )

    # Read into memory; tempfile on disk for the pipeline to consume.
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "file_too_large",
                "size_bytes": len(content),
                "max_bytes": MAX_UPLOAD_BYTES,
            },
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "empty_file"},
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".xlsx", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            report = reload_from_path(tmp_path)
        except ValueError as exc:
            # Schema mismatch from pipeline._validate_schema
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "invalid_schema", "message": str(exc)},
            ) from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("Upload pipeline failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "pipeline_failed", "message": str(exc)},
            ) from exc

        return UploadResponse(
            cleaning=CleaningReport(**asdict(report)),
            rows_replaced=True,
        )
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass
