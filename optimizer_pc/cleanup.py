from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
from typing import Iterable, List


@dataclass(frozen=True)
class CleanupResult:
    deleted_files: int
    deleted_folders: int
    freed_mb: float
    skipped: int


def _safe_temp_roots() -> List[Path]:
    roots = []
    for raw in {
        os.getenv("TEMP"),
        os.getenv("TMP"),
        str(Path.home() / "AppData" / "Local" / "Temp"),
    }:
        if raw:
            roots.append(Path(raw).expanduser().resolve())
    return roots


def _iter_entries(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return root.iterdir()


def clean_temp_files(confirm: bool = False) -> CleanupResult:
    if not confirm:
        return CleanupResult(deleted_files=0, deleted_folders=0, freed_mb=0.0, skipped=0)

    roots = _safe_temp_roots()
    deleted_files = 0
    deleted_folders = 0
    freed_bytes = 0
    skipped = 0

    for root in roots:
        for entry in list(_iter_entries(root)):
            try:
                if entry.is_file() or entry.is_symlink():
                    freed_bytes += entry.stat().st_size
                    entry.unlink(missing_ok=True)
                    deleted_files += 1
                elif entry.is_dir():
                    folder_size = _folder_size(entry)
                    shutil.rmtree(entry)
                    freed_bytes += folder_size
                    deleted_folders += 1
            except (PermissionError, FileNotFoundError, OSError):
                skipped += 1

    return CleanupResult(
        deleted_files=deleted_files,
        deleted_folders=deleted_folders,
        freed_mb=round(freed_bytes / (1024 ** 2), 2),
        skipped=skipped,
    )


def _folder_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except (PermissionError, FileNotFoundError, OSError):
            continue
    return total
