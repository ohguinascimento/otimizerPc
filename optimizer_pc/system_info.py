from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform
import shutil
import subprocess
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


def _run_powershell_first_success(commands: list[str]) -> str:
    last_error: Optional[Exception] = None
    for command in commands:
        try:
            output = _run_powershell(command)
        except (FileNotFoundError, subprocess.CalledProcessError, OSError) as exc:
            last_error = exc
            continue
        if output:
            return output
    if last_error is not None:
        raise last_error
    return ""


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


def _parse_ps_output_int(output: str) -> Optional[int]:
    for line in output.splitlines():
        value = _parse_optional_int(line.strip())
        if value is not None:
            return value
    return None


def _parse_ps_output_float(output: str) -> Optional[float]:
    for line in output.splitlines():
        value = _parse_optional_float(line.strip())
        if value is not None:
            return value
    return None


def _collect_motherboard_and_memory_windows() -> tuple[Optional[MotherboardInfo], Optional[MemoryUpgradeAnalysis]]:
    baseboard_commands = [
        (
            "$board = Get-CimInstance Win32_BaseBoard | Select-Object -First 1 Manufacturer,Product,SerialNumber; "
            "if ($board) { "
            "$manufacturer = if ($board.Manufacturer) { $board.Manufacturer } else { '' }; "
            "$product = if ($board.Product) { $board.Product } else { '' }; "
            "$serial = if ($board.SerialNumber) { $board.SerialNumber } else { '' }; "
            "Write-Output ($manufacturer + '|' + $product + '|' + $serial); "
            "}"
        ),
        (
            "$board = Get-WmiObject Win32_BaseBoard | Select-Object -First 1 Manufacturer,Product,SerialNumber; "
            "if ($board) { "
            "$manufacturer = if ($board.Manufacturer) { $board.Manufacturer } else { '' }; "
            "$product = if ($board.Product) { $board.Product } else { '' }; "
            "$serial = if ($board.SerialNumber) { $board.SerialNumber } else { '' }; "
            "Write-Output ($manufacturer + '|' + $product + '|' + $serial); "
            "}"
        ),
    ]

    try:
        baseboard_output = _run_powershell_first_success(baseboard_commands)
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        baseboard_output = ""

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

    total_slots = None
    used_slots = None
    installed_gb = None
    max_supported_gb = None
    free_slots = None
    can_upgrade = None

    if platform.system().lower() == "windows":
        try:
            total_slots = _parse_ps_output_int(
                _run_powershell_first_success(
                    [
                        (
                            "$arrays = @(Get-CimInstance Win32_PhysicalMemoryArray); "
                            "if ($arrays) { "
                            "  $total = ($arrays | Measure-Object -Property MemoryDevices -Sum).Sum; "
                            "  if ($total -gt 0) { Write-Output $total } "
                            "}"
                        ),
                        (
                            "$arrays = @(Get-WmiObject Win32_PhysicalMemoryArray); "
                            "if ($arrays) { "
                            "  $total = ($arrays | Measure-Object -Property MemoryDevices -Sum).Sum; "
                            "  if ($total -gt 0) { Write-Output $total } "
                            "}"
                        ),
                    ]
                )
            )
        except (FileNotFoundError, subprocess.CalledProcessError, OSError):
            total_slots = None

        try:
            used_slots = _parse_ps_output_int(
                _run_powershell_first_success(
                    [
                        "Write-Output ((@(Get-CimInstance Win32_PhysicalMemory)).Count)",
                        "Write-Output ((@(Get-WmiObject Win32_PhysicalMemory)).Count)",
                    ]
                )
            )
        except (FileNotFoundError, subprocess.CalledProcessError, OSError):
            used_slots = None

        try:
            installed_gb = _parse_ps_output_float(
                _run_powershell_first_success(
                    [
                        (
                            "$modules = @(Get-CimInstance Win32_PhysicalMemory); "
                            "if ($modules) { "
                            "  $installed = ($modules | Measure-Object -Property Capacity -Sum).Sum; "
                            "  if ($installed -gt 0) { Write-Output ([math]::Round($installed / 1GB, 2)) } "
                            "}"
                        ),
                        (
                            "$modules = @(Get-WmiObject Win32_PhysicalMemory); "
                            "if ($modules) { "
                            "  $installed = ($modules | Measure-Object -Property Capacity -Sum).Sum; "
                            "  if ($installed -gt 0) { Write-Output ([math]::Round($installed / 1GB, 2)) } "
                            "}"
                        ),
                    ]
                )
            )
        except (FileNotFoundError, subprocess.CalledProcessError, OSError):
            installed_gb = None

        try:
            max_supported_gb = _parse_ps_output_float(
                _run_powershell_first_success(
                    [
                        (
                            "$arrays = @(Get-CimInstance Win32_PhysicalMemoryArray); "
                            "if ($arrays) { "
                            "  $max = 0; "
                            "  foreach ($array in $arrays) { "
                            "    if ($array.PSObject.Properties.Name -contains 'MaxCapacityEx' -and $array.MaxCapacityEx) { "
                            "      $max += ([int64]$array.MaxCapacityEx * 1KB); "
                            "    } elseif ($array.MaxCapacity) { "
                            "      $max += ([int64]$array.MaxCapacity * 1KB); "
                            "    } "
                            "  } "
                            "  if ($max -gt 0) { Write-Output ([math]::Round($max / 1GB, 2)) } "
                            "}"
                        ),
                        (
                            "$arrays = @(Get-WmiObject Win32_PhysicalMemoryArray); "
                            "if ($arrays) { "
                            "  $max = 0; "
                            "  foreach ($array in $arrays) { "
                            "    if ($array.MaxCapacityEx) { "
                            "      $max += ([int64]$array.MaxCapacityEx * 1KB); "
                            "    } elseif ($array.MaxCapacity) { "
                            "      $max += ([int64]$array.MaxCapacity * 1KB); "
                            "    } "
                            "  } "
                            "  if ($max -gt 0) { Write-Output ([math]::Round($max / 1GB, 2)) } "
                            "}"
                        ),
                    ]
                )
            )
        except (FileNotFoundError, subprocess.CalledProcessError, OSError):
            max_supported_gb = None

        if total_slots is not None and used_slots is not None:
            free_slots = max(total_slots - used_slots, 0)
        if free_slots is not None:
            can_upgrade = free_slots > 0
        elif max_supported_gb is not None and installed_gb is not None:
            can_upgrade = installed_gb < max_supported_gb

    if any(
        value is not None
        for value in (total_slots, used_slots, installed_gb, max_supported_gb, free_slots, can_upgrade)
    ):
        memory_upgrade = MemoryUpgradeAnalysis(
            installed_gb=installed_gb,
            total_slots=total_slots,
            used_slots=used_slots,
            free_slots=free_slots,
            max_supported_gb=max_supported_gb,
            can_upgrade=can_upgrade,
        )
    else:
        memory_upgrade = None

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
        if cpu_physical is None:
            try:
                cpu_physical = _parse_ps_output_int(
                    _run_powershell_first_success(
                        [
                            "(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum",
                            "(Get-WmiObject Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum",
                        ]
                    )
                )
            except (FileNotFoundError, subprocess.CalledProcessError, OSError):
                pass

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
