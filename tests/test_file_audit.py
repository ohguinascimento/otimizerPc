from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import tempfile

from optimizer_pc.file_audit import collect_file_audit


def _set_file_times(path: Path, dt: datetime) -> None:
    timestamp = dt.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_collect_file_audit_marks_recent_executable_in_temp_as_high_risk():
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        temp_root = Path(temp_dir) / "Temp"
        temp_root.mkdir()
        suspicious_file = temp_root / "dropper.exe"
        suspicious_file.write_text("binary", encoding="utf-8")
        _set_file_times(suspicious_file, datetime.now(timezone.utc) - timedelta(hours=2))

        snapshot = collect_file_audit(roots=[str(temp_root)], limit=10, recent_days=7)

        assert snapshot.status == "ok"
        assert snapshot.backend == "filesystem"
        assert snapshot.total_files == 1
        assert snapshot.suspicious_files == 1
        assert len(snapshot.entries) == 1
        assert snapshot.entries[0].risk_level == "alto"
        assert "extensao de alto risco" in snapshot.entries[0].risk_reasons
        assert "localizacao sensivel" in snapshot.entries[0].risk_reasons


def test_collect_file_audit_ignores_old_low_risk_files():
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir) / "Documents"
        root.mkdir()
        file_path = root / "notes.txt"
        file_path.write_text("hello", encoding="utf-8")
        _set_file_times(file_path, datetime.now(timezone.utc) - timedelta(days=30))

        snapshot = collect_file_audit(roots=[str(root)], limit=10, recent_days=7)

        assert snapshot.status == "ok"
        assert snapshot.total_files == 1
        assert snapshot.suspicious_files == 0
        assert snapshot.entries == []
