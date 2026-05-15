from optimizer_pc.cleanup import CleanupResult, clean_temp_files


def test_clean_temp_files_dry_run_keeps_files(tmp_path, monkeypatch):
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    sample_file = temp_root / "cache.txt"
    sample_file.write_text("temporary data", encoding="utf-8")

    monkeypatch.setenv("TEMP", str(temp_root))
    monkeypatch.setenv("TMP", str(temp_root))

    result = clean_temp_files(confirm=False)

    assert result == CleanupResult(
        deleted_files=0,
        deleted_folders=0,
        freed_mb=0.0,
        skipped=0,
    )
    assert sample_file.exists()


def test_clean_temp_files_removes_direct_entries_and_folders(tmp_path, monkeypatch):
    temp_root = tmp_path / "temp"
    nested_root = temp_root / "nested"
    nested_root.mkdir(parents=True)
    file_one = temp_root / "cache.txt"
    file_two = nested_root / "nested.txt"
    file_one.write_text("temporary data", encoding="utf-8")
    file_two.write_text("more temporary data", encoding="utf-8")

    monkeypatch.setenv("TEMP", str(temp_root))
    monkeypatch.setenv("TMP", str(temp_root))

    result = clean_temp_files(confirm=True)

    assert result.deleted_files >= 1
    assert result.deleted_folders >= 1
    assert result.freed_mb > 0
    assert not file_one.exists()
    assert not nested_root.exists()
