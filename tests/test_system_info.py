from types import SimpleNamespace

from optimizer_pc import system_info


class FakePsutil:
    @staticmethod
    def virtual_memory():
        return SimpleNamespace(
            total=16 * 1024**3,
            used=6 * 1024**3,
            available=10 * 1024**3,
            percent=37.5,
        )

    @staticmethod
    def cpu_count(logical=False):
        return 8 if not logical else 16

    @staticmethod
    def disk_usage(path):
        assert path.endswith("\\")
        return SimpleNamespace(
            total=512 * 1024**3,
            used=300 * 1024**3,
            free=212 * 1024**3,
            percent=58.6,
        )


def test_get_system_snapshot_windows_reads_ram_and_storage(monkeypatch):
    monkeypatch.setattr(system_info.platform, "system", lambda: "Windows")
    monkeypatch.setattr(system_info.platform, "release", lambda: "11")
    monkeypatch.setattr(system_info.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(system_info.os, "cpu_count", lambda: 16)
    monkeypatch.setattr(
        system_info.os,
        "getenv",
        lambda key, default=None: {
            "SystemDrive": "C:",
            "TEMP": "C:\\Temp",
            "TMP": "C:\\Temp",
        }.get(key, default),
    )
    monkeypatch.setattr(system_info, "psutil", FakePsutil)

    def fake_run(*args, **kwargs):
        command = args[0][-1]
        if "Get-Partition" in command:
            return SimpleNamespace(stdout="SSD|Samsung SSD 970 EVO\n")
        if "Win32_BaseBoard" in command:
            return SimpleNamespace(stdout="ASUSTeK COMPUTER INC.|TUF GAMING B550M-PLUS|ABC123\n")
        if "Win32_PhysicalMemoryArray" in command:
            return SimpleNamespace(stdout="4|2|2|16.0|64.0|True\n")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(system_info.subprocess, "run", fake_run)

    snapshot = system_info.get_system_snapshot()

    assert snapshot.os_name == "Windows"
    assert snapshot.memory_total_gb == 16.0
    assert snapshot.memory_used_gb == 6.0
    assert snapshot.memory_available_gb == 10.0
    assert snapshot.storage_type == "SSD"
    assert snapshot.storage_model == "Samsung SSD 970 EVO"
    assert snapshot.system_drive == "C:"
    assert snapshot.motherboard is not None
    assert snapshot.motherboard.manufacturer == "ASUSTeK COMPUTER INC."
    assert snapshot.motherboard.model == "TUF GAMING B550M-PLUS"
    assert snapshot.memory_upgrade is not None
    assert snapshot.memory_upgrade.total_slots == 4
    assert snapshot.memory_upgrade.used_slots == 2
    assert snapshot.memory_upgrade.free_slots == 2
    assert snapshot.memory_upgrade.installed_gb == 16.0
    assert snapshot.memory_upgrade.max_supported_gb == 64.0
    assert snapshot.memory_upgrade.can_upgrade is True


def test_get_system_snapshot_windows_uses_wmi_fallback_for_motherboard(monkeypatch):
    monkeypatch.setattr(system_info.platform, "system", lambda: "Windows")
    monkeypatch.setattr(system_info.platform, "release", lambda: "11")
    monkeypatch.setattr(system_info.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(system_info.os, "cpu_count", lambda: 16)
    monkeypatch.setattr(
        system_info.os,
        "getenv",
        lambda key, default=None: {
            "SystemDrive": "C:",
            "TEMP": "C:\\Temp",
            "TMP": "C:\\Temp",
        }.get(key, default),
    )
    monkeypatch.setattr(system_info, "psutil", FakePsutil)

    def fake_run(*args, **kwargs):
        command = args[0][-1]
        if "Get-CimInstance Win32_BaseBoard" in command:
            raise system_info.subprocess.CalledProcessError(returncode=1, cmd=command)
        if "Get-WmiObject Win32_BaseBoard" in command:
            return SimpleNamespace(stdout="ASUSTeK COMPUTER INC.|TUF GAMING B550M-PLUS|ABC123\n")
        if "Win32_PhysicalMemoryArray" in command:
            return SimpleNamespace(stdout="4|2|2|16.0|64.0|True\n")
        if "Get-Partition" in command:
            return SimpleNamespace(stdout="SSD|Samsung SSD 970 EVO\n")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(system_info.subprocess, "run", fake_run)

    snapshot = system_info.get_system_snapshot()

    assert snapshot.motherboard is not None
    assert snapshot.motherboard.manufacturer == "ASUSTeK COMPUTER INC."
    assert snapshot.motherboard.model == "TUF GAMING B550M-PLUS"
    assert snapshot.memory_upgrade is not None
    assert snapshot.memory_upgrade.can_upgrade is True


def test_get_system_snapshot_windows_uses_wmi_fallback_for_memory(monkeypatch):
    monkeypatch.setattr(system_info.platform, "system", lambda: "Windows")
    monkeypatch.setattr(system_info.platform, "release", lambda: "11")
    monkeypatch.setattr(system_info.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(system_info.os, "cpu_count", lambda: 16)
    monkeypatch.setattr(
        system_info.os,
        "getenv",
        lambda key, default=None: {
            "SystemDrive": "C:",
            "TEMP": "C:\\Temp",
            "TMP": "C:\\Temp",
        }.get(key, default),
    )
    monkeypatch.setattr(system_info, "psutil", FakePsutil)

    def fake_run(*args, **kwargs):
        command = args[0][-1]
        if "Get-Partition" in command:
            return SimpleNamespace(stdout="SSD|Samsung SSD 970 EVO\n")
        if "Get-CimInstance Win32_BaseBoard" in command:
            return SimpleNamespace(stdout="ASUSTeK COMPUTER INC.|TUF GAMING B550M-PLUS|ABC123\n")
        if "Get-CimInstance Win32_PhysicalMemoryArray" in command:
            raise system_info.subprocess.CalledProcessError(returncode=1, cmd=command)
        if "Get-CimInstance Win32_PhysicalMemory" in command:
            raise system_info.subprocess.CalledProcessError(returncode=1, cmd=command)
        if "Get-WmiObject Win32_PhysicalMemoryArray" in command:
            return SimpleNamespace(stdout="4|2|2|16.0|64.0|True\n")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(system_info.subprocess, "run", fake_run)

    snapshot = system_info.get_system_snapshot()

    assert snapshot.memory_upgrade is not None
    assert snapshot.memory_upgrade.total_slots == 4
    assert snapshot.memory_upgrade.used_slots == 2
    assert snapshot.memory_upgrade.free_slots == 2
    assert snapshot.memory_upgrade.installed_gb == 16.0
    assert snapshot.memory_upgrade.max_supported_gb == 64.0
    assert snapshot.memory_upgrade.can_upgrade is True


def test_get_system_snapshot_without_psutil_uses_fallback(monkeypatch):
    monkeypatch.setattr(system_info.platform, "system", lambda: "Linux")
    monkeypatch.setattr(system_info.platform, "release", lambda: "6.8")
    monkeypatch.setattr(system_info.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(system_info.os, "cpu_count", lambda: 8)
    monkeypatch.setattr(
        system_info.os,
        "getenv",
        lambda key, default=None: None,
    )
    monkeypatch.setattr(system_info, "psutil", None)
    monkeypatch.setattr(
        system_info.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(
            total=256 * 1024**3,
            used=100 * 1024**3,
            free=156 * 1024**3,
        ),
    )

    snapshot = system_info.get_system_snapshot()

    assert snapshot.os_name == "Linux"
    assert snapshot.memory_total_gb is None
    assert snapshot.memory_available_gb is None
    assert snapshot.disk.total_gb == 256.0
    assert snapshot.storage_type is None
    assert snapshot.storage_model is None
    assert snapshot.motherboard is None
    assert snapshot.memory_upgrade is None
