"""ADAM OS Control Center — Files API Endpoints

Provides file system exploration, reading, writing, and search
through the FileTree service, with path traversal guardrails.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Query, HTTPException

from app.services.file_tree import file_tree
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.get("/tree")
async def file_tree_endpoint(
    path: str = Query("", description="Relative path from adam-os-system root"),
    max_depth: int = Query(3, ge=1, le=10, description="Maximum recursion depth"),
) -> Dict[str, Any]:
    """Return a directory tree structure.

    Walks the filesystem up to max_depth levels and returns a
    recursive tree of directories and files.
    """
    try:
        return file_tree.get_tree(path=path, max_depth=max_depth)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/read")
async def read_file(
    file_path: str = Query(..., description="Relative path to the file"),
) -> Dict[str, Any]:
    """Read a file's contents with metadata.

    Returns content, size, extension, line count, and modification date.
    Max file size: 500 KB.
    """
    try:
        result = file_tree.read_file(file_path=file_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/write")
async def write_file(
    body: Dict[str, Any] = Body(..., description="Request body with file_path and content"),
) -> Dict[str, Any]:
    """Write content to a file.

    Guardrails:
    - File writes are disabled unless FILES_WRITE_ENABLED=True (D-C7)
    - Path traversal is blocked
    - Only .yaml .json .md .py .txt .sh .toml .env extensions allowed
    - Won't overwrite files larger than 1 MB

    Request body:
    ```json
    {
        "file_path": "config/settings.yaml",
        "content": "key: value\\n"
    }
    ```
    """
    if not settings.FILES_WRITE_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="File writes disabled by config (FILES_WRITE_ENABLED=False)",
        )

    file_path = body.get("file_path")
    content = body.get("content", "")

    if not file_path:
        raise HTTPException(status_code=400, detail="'file_path' is required")

    if not isinstance(content, str):
        raise HTTPException(status_code=400, detail="'content' must be a string")

    try:
        result = file_tree.write_file(file_path=file_path, content=content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/search")
async def search_files(
    query: str = Query(..., description="Substring to match against file names"),
) -> List[Dict[str, Any]]:
    """Search for files by name within the adam-os-system directory.

    Case-insensitive substring matching against file names.
    """
    return file_tree.search_files(query=query)
