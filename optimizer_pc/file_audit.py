from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from typing import Iterable, Optional


try:
    import pytsk3  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    pytsk3 = None


_HIGH_RISK_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".exe",
    ".js",
    ".jse",
    ".lnk",
    ".msi",
    ".msp",
    ".ps1",
    ".scr",
    ".vbs",
}

_SUSPICIOUS_DIR_HINTS = (
    "\\appdata\\local\\temp\\",
    "\\appdata\\roaming\\",
    "\\downloads\\",
    "\\temp\\",
    "\\tmp\\",
)


@dataclass(frozen=True)
class FileAuditEntry:
    path: str
    name: str
    extension: str
    size_bytes: Optional[int]
    created_at: Optional[str]
    modified_at: Optional[str]
    accessed_at: Optional[str]
    risk_level: str
    risk_score: int
    risk_reasons: tuple[str, ...]


@dataclass(frozen=True)
class FileAuditSnapshot:
    status: str
    warning: Optional[str]
    generated_at: str
    backend: str
    scanned_roots: list[str]
    recent_days: int
    total_files: int
    suspicious_files: int
    entries: list[FileAuditEntry]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, timezone.utc).astimezone().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _default_scan_roots() -> list[Path]:
    home = Path.home()
    candidates = [
        Path(os.getenv("TEMP") or home / "AppData" / "Local" / "Temp"),
        home / "Desktop",
        home / "Downloads",
        home / "Documents",
        home / "AppData" / "Roaming",
        home / "AppData" / "Local",
    ]

    unique: list[Path] = []
    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        key = str(resolved).lower()
        if key not in seen and resolved.exists():
            seen.add(key)
            unique.append(resolved)
    return unique


def _safe_name(name: object) -> str:
    if isinstance(name, bytes):
        return name.decode("utf-8", errors="ignore")
    return str(name or "")


def _score_path(path_text: str, extension: str, modified_at: Optional[datetime]) -> tuple[int, tuple[str, ...]]:
    score = 0
    reasons: list[str] = []
    normalized = path_text.replace("/", "\\").lower()

    if extension in _HIGH_RISK_EXTENSIONS:
        score += 3
        reasons.append("extensao de alto risco")

    if any(marker in normalized for marker in _SUSPICIOUS_DIR_HINTS):
        score += 2
        reasons.append("localizacao sensivel")

    if modified_at is not None:
        age = datetime.now(timezone.utc) - modified_at.astimezone(timezone.utc)
        if age <= timedelta(hours=24):
            score += 2
            reasons.append("modificado nas ultimas 24h")
        elif age <= timedelta(days=7):
            score += 1
            reasons.append("modificado recentemente")

    name_lower = Path(path_text).name.lower()
    if extension in {".ps1", ".bat", ".cmd", ".vbs", ".js"} and len(name_lower) > 18:
        score += 1
        reasons.append("nome incomum para script")

    if name_lower.startswith("tmp") or name_lower.startswith("upd") or "drop" in name_lower:
        score += 1
        reasons.append("nome sugestivo de dropper")

    return score, tuple(dict.fromkeys(reasons))


def _risk_level(score: int) -> str:
    if score >= 5:
        return "alto"
    if score >= 3:
        return "medio"
    return "baixo"


def _build_entry(
    path_text: str,
    size_bytes: Optional[int],
    created_ts: Optional[float],
    modified_ts: Optional[float],
    accessed_ts: Optional[float],
) -> FileAuditEntry:
    path = Path(path_text)
    extension = path.suffix.lower()
    modified_at = datetime.fromtimestamp(modified_ts, timezone.utc) if modified_ts is not None else None
    score, reasons = _score_path(path_text, extension, modified_at)
    return FileAuditEntry(
        path=path_text,
        name=path.name or path_text,
        extension=extension or "",
        size_bytes=size_bytes,
        created_at=_to_iso(created_ts),
        modified_at=_to_iso(modified_ts),
        accessed_at=_to_iso(accessed_ts),
        risk_level=_risk_level(score),
        risk_score=score,
        risk_reasons=reasons,
    )


def _scan_filesystem_roots(roots: Iterable[Path], recent_days: int, limit: int) -> tuple[list[FileAuditEntry], int, list[str]]:
    findings: list[FileAuditEntry] = []
    total_files = 0
    warnings: list[str] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=recent_days)

    for root in roots:
        if not root.exists():
            continue

        try:
            walker = os.walk(root, followlinks=False)
        except (OSError, RuntimeError) as exc:
            warnings.append(f"{root}: {exc.__class__.__name__}")
            continue

        for current_root, dirnames, filenames in walker:
            current_path = Path(current_root)
            try:
                if current_path.is_symlink():
                    dirnames[:] = []
                    continue
            except OSError:
                dirnames[:] = []
                continue

            for filename in filenames:
                file_path = current_path / filename
                try:
                    stat = file_path.stat()
                except (FileNotFoundError, PermissionError, OSError):
                    continue

                total_files += 1
                modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                if modified_at < cutoff:
                    continue

                entry = _build_entry(
                    str(file_path),
                    stat.st_size,
                    getattr(stat, "st_ctime", None),
                    stat.st_mtime,
                    getattr(stat, "st_atime", None),
                )
                if entry.risk_level != "baixo":
                    findings.append(entry)

    findings.sort(key=lambda item: ({"alto": 0, "medio": 1, "baixo": 2}.get(item.risk_level, 3), -item.risk_score, item.modified_at or "", item.path.lower()))
    return findings[: max(1, limit)], total_files, warnings


def _default_pytsk_source() -> Optional[str]:
    if os.name != "nt":
        return None
    system_drive = os.getenv("SystemDrive") or "C:"
    drive = system_drive.rstrip("\\/")
    return rf"\\.\{drive}"


def _collect_with_pytsk3(source: str, recent_days: int, limit: int) -> tuple[list[FileAuditEntry], int, Optional[str]]:
    if pytsk3 is None:
        return [], 0, "pytsk3 nao esta instalado."

    try:
        image = pytsk3.Img_Info(source)
        filesystem = pytsk3.FS_Info(image)
    except Exception as exc:  # pragma: no cover - depends on local environment
        return [], 0, f"pytsk3 nao conseguiu abrir a origem: {exc.__class__.__name__}"

    findings: list[FileAuditEntry] = []
    total_files = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=recent_days)

    def walk(directory_path: str) -> None:
        nonlocal total_files

        try:
            directory = filesystem.open_dir(path=directory_path)
        except Exception:
            return

        for entry in directory:
            try:
                name = _safe_name(entry.info.name.name)
                meta = entry.info.meta
            except Exception:
                continue

            if not name or name in {".", ".."}:
                continue

            child_path = directory_path.rstrip("/")
            child_path = f"{child_path}/{name}" if child_path else f"/{name}"

            if meta is not None and getattr(meta, "type", None) == getattr(pytsk3, "TSK_FS_META_TYPE_DIR", object()):
                walk(child_path)
                continue

            if meta is None:
                continue

            total_files += 1
            modified_ts = getattr(meta, "mtime", None)
            modified_at = datetime.fromtimestamp(modified_ts, timezone.utc) if modified_ts else None
            if modified_at is not None and modified_at < cutoff:
                continue

            entry_data = _build_entry(
                child_path,
                int(getattr(meta, "size", 0) or 0),
                getattr(meta, "crtime", None),
                modified_ts,
                getattr(meta, "atime", None),
            )
            if entry_data.risk_level != "baixo":
                findings.append(entry_data)

    walk("/")
    findings.sort(key=lambda item: ({"alto": 0, "medio": 1, "baixo": 2}.get(item.risk_level, 3), -item.risk_score, item.modified_at or "", item.path.lower()))
    return findings[: max(1, limit)], total_files, None


def collect_file_audit(
    roots: Optional[Iterable[str]] = None,
    limit: int = 40,
    recent_days: int = 7,
    source: Optional[str] = None,
) -> FileAuditSnapshot:
    scanned_roots: list[str] = []
    warnings: list[str] = []

    if source:
        findings, total_files, warning = _collect_with_pytsk3(source, recent_days=recent_days, limit=limit)
        if warning is not None:
            warnings.append(warning)
        if findings or warning is None:
            return FileAuditSnapshot(
                status="ok" if warning is None else "limited",
                warning="; ".join(warnings) or None,
                generated_at=_now_iso(),
                backend="pytsk3",
                scanned_roots=[source],
                recent_days=recent_days,
                total_files=total_files,
                suspicious_files=sum(1 for item in findings if item.risk_level != "baixo"),
                entries=findings,
            )

    roots_to_scan = [Path(item) for item in roots] if roots else _default_scan_roots()
    scanned_roots = [str(root) for root in roots_to_scan]
    findings, total_files, fs_warnings = _scan_filesystem_roots(roots_to_scan, recent_days=recent_days, limit=limit)
    warnings.extend(fs_warnings)

    status = "ok"
    if warnings and not findings:
        status = "limited"

    return FileAuditSnapshot(
        status=status,
        warning="; ".join(warnings) or None,
        generated_at=_now_iso(),
        backend="filesystem",
        scanned_roots=scanned_roots,
        recent_days=recent_days,
        total_files=total_files,
        suspicious_files=sum(1 for item in findings if item.risk_level != "baixo"),
        entries=findings,
    )
