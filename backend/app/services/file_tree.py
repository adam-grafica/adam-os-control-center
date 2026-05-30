"""ADAM OS Control Center — File Tree Service

Safe file-system exploration service with guardrails against
path traversal, writes to non-whitelisted extensions, and large files.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Allowed extensions for write operations ──

ALLOWED_EXTENSIONS = {".yaml", ".json", ".md", ".py", ".txt", ".sh", ".toml", ".env"}

# ── Default max sizes ──

DEFAULT_MAX_DEPTH = 3
MAX_READ_SIZE = 500 * 1024  # 500 KB


class FileTree:
    """Safe file-system exploration and editing service.

    Operates within a configured root path and prevents path traversal
    attacks. Write operations only allow whitelisted extensions.
    """

    def __init__(self, root_path: str):
        self._root = Path(root_path).resolve()
        if not self._root.is_dir():
            logger.warning("Root path does not exist: %s", self._root)
        logger.info("FileTree root: %s", self._root)

    def get_tree(
        self, path: str = "", max_depth: int = DEFAULT_MAX_DEPTH
    ) -> Dict[str, Any]:
        """Build a recursive directory tree.

        Args:
            path: relative path from root (or absolute within root).
            max_depth: maximum recursion depth.

        Returns:
            Tree dict with ``name``, ``path``, ``type``, ``size``, and
            ``children`` (for directories).
        """
        full_path = self._resolve(path)
        if not full_path.exists():
            return {"error": f"Path does not exist: {path}", "path": path}
        if not full_path.is_dir():
            return self._file_info(full_path)

        return self._build_tree(full_path, max_depth=max_depth, current_depth=0)

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read a file's content with metadata.

        Args:
            file_path: relative path from root or absolute within root.

        Returns:
            Dict with ``content``, ``path``, ``size``, ``extension``,
            ``lines``, ``modified_at``.
        """
        full_path = self._resolve(file_path)

        if not full_path.exists():
            return {"error": f"File not found: {file_path}", "path": file_path}
        if not full_path.is_file():
            return {"error": f"Not a file: {file_path}", "path": file_path}

        stat = full_path.stat()
        if stat.st_size > MAX_READ_SIZE:
            return {
                "error": f"File too large ({stat.st_size:,} bytes > {MAX_READ_SIZE:,} max)",
                "path": str(full_path),
                "size": stat.st_size,
            }

        try:
            content = full_path.read_text(encoding="utf-8")
            return {
                "content": content,
                "path": str(full_path),
                "size": stat.st_size,
                "extension": full_path.suffix,
                "lines": len(content.splitlines()),
                "modified_at": stat.st_mtime,
            }
        except UnicodeDecodeError:
            return {
                "error": "File is not UTF-8 text",
                "path": str(full_path),
                "size": stat.st_size,
            }
        except OSError as exc:
            return {"error": f"Could not read file: {exc}", "path": str(full_path)}

    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write content to a file with guardrails.

        Guardrails:
          - Prevents path traversal (path must resolve within root)
          - Only allows whitelisted extensions (.yaml .json .md .py .txt .sh .toml .env)
          - Does not overwrite existing files larger than 1 MB (safety)

        Args:
            file_path: relative path from root or absolute within root.
            content: text content to write.

        Returns:
            Dict with success info or error.
        """
        full_path = self._resolve(file_path)

        # Extension whitelist
        ext = full_path.suffix.lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            return {
                "error": f"Extension not allowed: '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                "path": str(full_path),
            }

        # Safety check: don't overwrite large files
        if full_path.exists() and full_path.is_file():
            stat = full_path.stat()
            if stat.st_size > 1024 * 1024:  # 1 MB
                return {
                    "error": (
                        f"Refusing to overwrite large file ({stat.st_size:,} bytes). "
                        f"Delete it first or use a different path."
                    ),
                    "path": str(full_path),
                }

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            new_stat = full_path.stat()
            return {
                "success": True,
                "path": str(full_path),
                "size": new_stat.st_size,
                "lines": len(content.splitlines()),
            }
        except OSError as exc:
            return {"error": f"Could not write file: {exc}", "path": str(full_path)}

    def search_files(self, query: str) -> List[Dict[str, Any]]:
        """Search for files by name within the root directory.

        Args:
            query: substring to match against file names (case-insensitive).

        Returns:
            List of matching files with path, size, and modified date.
        """
        if not self._root.is_dir():
            return []

        results: List[Dict[str, Any]] = []
        query_lower = query.lower()

        try:
            for root_dir, _dirs, files in os.walk(str(self._root)):
                for fname in files:
                    if query_lower in fname.lower():
                        full = os.path.join(root_dir, fname)
                        try:
                            stat = os.stat(full)
                            results.append(
                                {
                                    "path": full,
                                    "name": fname,
                                    "size": stat.st_size,
                                    "modified_at": stat.st_mtime,
                                }
                            )
                        except OSError:
                            continue
        except OSError as exc:
            logger.warning("Error searching files: %s", exc)

        return results

    # ── Internal helpers ──

    def _resolve(self, path: str) -> Path:
        """Resolve a path safely within the root directory.

        Raises ValueError if the path traverses outside root.
        """
        p = Path(path)
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (self._root / p).resolve()

        # Guard: must be within root
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise ValueError(
                f"Path traversal detected: '{path}' resolves outside root "
                f"({resolved} not under {self._root})"
            )
        return resolved

    def _file_info(self, full_path: Path) -> Dict[str, Any]:
        """Return file metadata as a tree node."""
        stat = full_path.stat()
        return {
            "name": full_path.name,
            "path": str(full_path),
            "type": "file",
            "size": stat.st_size,
            "modified_at": stat.st_mtime,
        }

    def _build_tree(
        self, dir_path: Path, max_depth: int, current_depth: int = 0
    ) -> Dict[str, Any]:
        """Recursively build a directory tree."""
        node: Dict[str, Any] = {
            "name": dir_path.name,
            "path": str(dir_path),
            "type": "directory",
            "children": [],
        }

        if current_depth >= max_depth:
            node["truncated"] = True
            return node

        try:
            entries = sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            node["error"] = "Permission denied"
            return node
        except OSError as exc:
            node["error"] = str(exc)
            return node

        for entry in entries:
            try:
                if entry.is_dir():
                    child = self._build_tree(
                        entry, max_depth, current_depth + 1
                    )
                    node["children"].append(child)
                elif entry.is_file():
                    node["children"].append(self._file_info(entry))
            except PermissionError:
                continue

        return node


# ── Module-level singleton ──

# Detect Docker vs local: inside container the system is at /app/adam-os-system
_DOCKER_PATH = "/app/adam-os-system"
_LOCAL_PATH = os.environ.get(
    "ADAM_OS_ROOT", "/home/adamcloud/adam-os-system"
)
_ADAM_OS_ROOT = _DOCKER_PATH if os.path.isdir(_DOCKER_PATH) else _LOCAL_PATH

file_tree = FileTree(_ADAM_OS_ROOT)
