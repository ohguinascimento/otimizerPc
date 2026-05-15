from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform
import subprocess
import shutil
from typing import Optional


try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    psutil = None


@dataclass(frozen=True)
class DiskUsage:
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


@dataclass(frozen=True)
class MotherboardInfo:
    manufacturer: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]


@dataclass(frozen=True)
class MemoryUpgradeAnalysis:
    installed_gb: Optional[float]
    total_slots: Optional[int]
    used_slots: Optional[int]
    free_slots: Optional[int]
    max_supported_gb: Optional[float]
    can_upgrade: Optional[bool]


@dataclass(frozen=True)
class SystemSnapshot:
    os_name: str
    os_release: str
    architecture: str
    cpu_cores_logical: Optional[int]
    cpu_cores_physical: Optional[int]
    memory_total_gb: Optional[float]
    memory_used_gb: Optional[float]
    memory_available_gb: Optional[float]
    memory_percent: Optional[float]
    disk: Optional[DiskUsage]
    system_drive: str
    storage_type: Optional[str]
    storage_model: Optional[str]
    motherboard: Optional[MotherboardInfo]
    memory_upgrade: Optional[MemoryUpgradeAnalysis]
    temp_dir: str


def _bytes_to_gb(value: float) -> float:
    return round(value / (1024 ** 3), 2)


def _get_system_drive() -> str:
    if platform.system().lower() == "windows":
        anchor = os.getenv("SystemDrive") or Path.cwd().anchor or "C:"
        anchor = anchor.rstrip("\\/")
        return anchor or "C:"
    return Path.cwd().anchor or "/"


def _get_disk_root_path(system_drive: str) -> str:
    if platform.system().lower() == "windows":
        return system_drive + "\\"
    return system_drive or "/"


def _detect_storage_type_windows(system_drive: str) -> tuple[Optional[str], Optional[str]]:
    drive_letter = system_drive.rstrip("\\/:")
    if len(drive_letter) == 2 and drive_letter[1] == ":":
        drive_letter = drive_letter[0]

    command = (
        f"$drive = '{drive_letter}'; "
        "$part = Get-Partition -DriveLetter $drive -ErrorAction Stop; "
        "$disk = $part | Get-Disk; "
        "if ($disk) { "
        "  $type = if ($disk.MediaType -and $disk.MediaType -ne 'Unspecified') { $disk.MediaType } else { 'Unknown' }; "
        "  $model = $disk.FriendlyName; "
        "  Write-Output ($type + '|' + $model); "
        "}"
    )

    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return None, None

    output = completed.stdout.strip()
    if not output:
        return None, None

    first_line = output.splitlines()[0].strip()
    if "|" not in first_line:
        return first_line or None, None

    storage_type, storage_model = first_line.split("|", 1)
    storage_type = storage_type.strip() or None
    storage_model = storage_model.strip() or None

    if storage_type:
        normalized = storage_type.lower()
        if "ssd" in normalized:
            storage_type = "SSD"
        elif "hdd" in normalized or "hard" in normalized:
            storage_type = "HD"
        elif storage_type == "Unspecified":
            storage_type = None
        elif normalized == "unknown":
            storage_type = None

    return storage_type, storage_model


def _run_powershell(command: str) -> str:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _collect_memory_stats() -> tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[int]]:
    if psutil is None:
        return None, None, None, None, None

    vm = psutil.virtual_memory()
    return (
        _bytes_to_gb(vm.total),
        _bytes_to_gb(vm.used),
        _bytes_to_gb(vm.available),
        round(vm.percent, 1),
        psutil.cpu_count(logical=False),
    )


def _collect_disk_usage(system_drive: str) -> DiskUsage:
    if psutil is not None:
        disk_usage = psutil.disk_usage(_get_disk_root_path(system_drive))
        return DiskUsage(
            total_gb=_bytes_to_gb(disk_usage.total),
            used_gb=_bytes_to_gb(disk_usage.used),
            free_gb=_bytes_to_gb(disk_usage.free),
            percent=round(disk_usage.percent, 1),
        )

    usage = shutil.disk_usage(_get_disk_root_path(system_drive))
    return DiskUsage(
        total_gb=_bytes_to_gb(usage.total),
        used_gb=_bytes_to_gb(usage.used),
        free_gb=_bytes_to_gb(usage.free),
        percent=round((usage.used / usage.total) * 100, 1),
    )


def _collect_temp_dir() -> str:
    return os.getenv("TEMP") or os.getenv("TMP") or str(Path.home() / "AppData" / "Local" / "Temp")


def _parse_optional_int(value: str) -> Optional[int]:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _parse_optional_float(value: str) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return round(parsed, 2) if parsed >= 0 else None


def _collect_motherboard_and_memory_windows() -> tuple[Optional[MotherboardInfo], Optional[MemoryUpgradeAnalysis]]:
    baseboard_command = (
        "$board = Get-CimInstance Win32_BaseBoard | Select-Object -First 1 Manufacturer,Product,SerialNumber; "
        "if ($board) { "
        "$manufacturer = if ($board.Manufacturer) { $board.Manufacturer } else { '' }; "
        "$product = if ($board.Product) { $board.Product } else { '' }; "
        "$serial = if ($board.SerialNumber) { $board.SerialNumber } else { '' }; "
        "Write-Output ($manufacturer + '|' + $product + '|' + $serial); "
        "}"
    )
    memory_command = (
        "$arrays = @(Get-CimInstance Win32_PhysicalMemoryArray); "
        "$modules = @(Get-CimInstance Win32_PhysicalMemory); "
        "$totalSlots = ($arrays | Measure-Object -Property MemoryDevices -Sum).Sum; "
        "if (-not $totalSlots) { $totalSlots = $null } "
        "$usedSlots = @($modules).Count; "
        "$installedBytes = ($modules | Measure-Object -Property Capacity -Sum).Sum; "
        "if (-not $installedBytes) { $installedBytes = 0 } "
        "$maxBytes = 0; "
        "foreach ($array in $arrays) { "
        "  if ($array.PSObject.Properties.Name -contains 'MaxCapacityEx' -and $array.MaxCapacityEx) { "
        "    $maxBytes += [int64]$array.MaxCapacityEx; "
        "  } elseif ($array.MaxCapacity) { "
        "    $maxBytes += ([int64]$array.MaxCapacity * 1KB); "
        "  } "
        "} "
        "if (-not $maxBytes) { $maxBytes = $null } "
        "$installedGb = [math]::Round($installedBytes / 1GB, 2); "
        "if (-not $installedBytes) { $installedGb = $null } "
        "$maxGb = if ($maxBytes) { [math]::Round($maxBytes / 1GB, 2) } else { $null }; "
        "$freeSlots = if ($null -ne $totalSlots) { [math]::Max($totalSlots - $usedSlots, 0) } else { $null }; "
        "$canUpgrade = $null; "
        "if ($null -ne $freeSlots -and $freeSlots -gt 0) { $canUpgrade = $true } "
        "elseif ($null -ne $maxGb -and $null -ne $installedGb -and $installedGb -lt $maxGb) { $canUpgrade = $true } "
        "elseif ($null -ne $freeSlots) { $canUpgrade = $false } "
        "$totalSlotsText = if ($null -ne $totalSlots) { $totalSlots } else { '' }; "
        "$usedSlotsText = if ($null -ne $usedSlots) { $usedSlots } else { '' }; "
        "$freeSlotsText = if ($null -ne $freeSlots) { $freeSlots } else { '' }; "
        "$installedGbText = if ($null -ne $installedGb) { $installedGb } else { '' }; "
        "$maxGbText = if ($null -ne $maxGb) { $maxGb } else { '' }; "
        "$canUpgradeText = if ($null -ne $canUpgrade) { $canUpgrade } else { '' }; "
        "Write-Output ($totalSlotsText + '|' + $usedSlotsText + '|' + $freeSlotsText + '|' + $installedGbText + '|' + $maxGbText + '|' + $canUpgradeText);"
    )

    try:
        baseboard_output = _run_powershell(baseboard_command)
        memory_output = _run_powershell(memory_command)
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return None, None

    motherboard = None
    if baseboard_output:
        parts = baseboard_output.split("|")
        while len(parts) < 3:
            parts.append("")
        manufacturer, model, serial_number = (part.strip() or None for part in parts[:3])
        if manufacturer or model or serial_number:
            motherboard = MotherboardInfo(
                manufacturer=manufacturer,
                model=model,
                serial_number=serial_number,
            )

    memory_upgrade = None
    if memory_output:
        parts = memory_output.split("|")
        while len(parts) < 6:
            parts.append("")
        total_slots = _parse_optional_int(parts[0])
        used_slots = _parse_optional_int(parts[1])
        free_slots = _parse_optional_int(parts[2])
        installed_gb = _parse_optional_float(parts[3])
        max_supported_gb = _parse_optional_float(parts[4])
        can_upgrade_raw = parts[5].strip().lower()
        can_upgrade = None
        if can_upgrade_raw in {"true", "1", "yes"}:
            can_upgrade = True
        elif can_upgrade_raw in {"false", "0", "no"}:
            can_upgrade = False
        memory_upgrade = MemoryUpgradeAnalysis(
            installed_gb=installed_gb,
            total_slots=total_slots,
            used_slots=used_slots,
            free_slots=free_slots,
            max_supported_gb=max_supported_gb,
            can_upgrade=can_upgrade,
        )

    return motherboard, memory_upgrade


def get_system_snapshot() -> SystemSnapshot:
    system_drive = _get_system_drive()
    memory_total_gb, memory_used_gb, memory_available_gb, memory_percent, cpu_physical = _collect_memory_stats()
    disk = _collect_disk_usage(system_drive)
    cpu_logical = os.cpu_count()
    storage_type = None
    storage_model = None
    motherboard = None
    memory_upgrade = None

    if platform.system().lower() == "windows":
        storage_type, storage_model = _detect_storage_type_windows(system_drive)
        motherboard, memory_upgrade = _collect_motherboard_and_memory_windows()

    return SystemSnapshot(
        os_name=platform.system(),
        os_release=platform.release(),
        architecture=platform.machine(),
        cpu_cores_logical=cpu_logical,
        cpu_cores_physical=cpu_physical,
        memory_total_gb=memory_total_gb,
        memory_used_gb=memory_used_gb,
        memory_available_gb=memory_available_gb,
        memory_percent=memory_percent,
        disk=disk,
        system_drive=system_drive,
        storage_type=storage_type,
        storage_model=storage_model,
        motherboard=motherboard,
        memory_upgrade=memory_upgrade,
        temp_dir=_collect_temp_dir(),
    )
