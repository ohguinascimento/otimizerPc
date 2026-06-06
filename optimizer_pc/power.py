from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import platform
import subprocess
from typing import Optional


try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    psutil = None


@dataclass(frozen=True)
class PowerSnapshot:
    status: str
    watts: Optional[float]
    source: str
    confidence: Optional[float]
    cpu_percent: Optional[float]
    memory_percent: Optional[float]
    battery_percent: Optional[float]
    battery_runtime_minutes: Optional[int]
    note: Optional[str]
    measured_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_float(value: str) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _parse_int(value: str) -> Optional[int]:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


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


def _collect_battery_snapshot_windows() -> tuple[Optional[float], Optional[int], Optional[float]]:
    commands = [
        (
            "$battery = Get-CimInstance Win32_Battery | Select-Object -First 1 "
            "EstimatedChargeRemaining,EstimatedRunTime,FullChargeCapacity,DesignCapacity,BatteryStatus; "
            "if ($battery) { "
            "  $capacity = 0; "
            "  if ($battery.FullChargeCapacity) { $capacity = [double]$battery.FullChargeCapacity } "
            "  elseif ($battery.DesignCapacity) { $capacity = [double]$battery.DesignCapacity } "
            "  $remaining = [double]$battery.EstimatedChargeRemaining; "
            "  $runtime = [double]$battery.EstimatedRunTime; "
            "  if ($capacity -gt 0 -and $remaining -ge 0 -and $runtime -gt 0) { "
            "    $watts = ((($capacity / 1000.0) * ($remaining / 100.0)) / ($runtime / 60.0)); "
            "    Write-Output (($watts.ToString('0.00')) + '|' + $remaining + '|' + $runtime); "
            "  } "
            "}"
        ),
        (
            "$battery = Get-WmiObject Win32_Battery | Select-Object -First 1 "
            "EstimatedChargeRemaining,EstimatedRunTime,FullChargeCapacity,DesignCapacity,BatteryStatus; "
            "if ($battery) { "
            "  $capacity = 0; "
            "  if ($battery.FullChargeCapacity) { $capacity = [double]$battery.FullChargeCapacity } "
            "  elseif ($battery.DesignCapacity) { $capacity = [double]$battery.DesignCapacity } "
            "  $remaining = [double]$battery.EstimatedChargeRemaining; "
            "  $runtime = [double]$battery.EstimatedRunTime; "
            "  if ($capacity -gt 0 -and $remaining -ge 0 -and $runtime -gt 0) { "
            "    $watts = ((($capacity / 1000.0) * ($remaining / 100.0)) / ($runtime / 60.0)); "
            "    Write-Output (($watts.ToString('0.00')) + '|' + $remaining + '|' + $runtime); "
            "  } "
            "}"
        ),
    ]

    try:
        output = _run_powershell_first_success(commands)
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return None, None, None

    if not output:
        return None, None, None

    parts = output.split("|")
    watts = _parse_float(parts[0].strip()) if parts else None
    battery_percent = _parse_float(parts[1].strip()) if len(parts) > 1 else None
    runtime_minutes = _parse_int(parts[2].strip()) if len(parts) > 2 else None
    return watts, runtime_minutes, battery_percent


def _estimate_from_system_load() -> tuple[Optional[float], Optional[float], Optional[float]]:
    if psutil is None:
        return None, None, None

    cpu_percent = round(float(psutil.cpu_percent(interval=0.15) or 0.0), 1)
    memory = psutil.virtual_memory()
    memory_percent = round(float(memory.percent or 0.0), 1)

    base_watts = 22.0
    if psutil.sensors_battery() is not None:
        base_watts = 11.0

    watts = base_watts + (cpu_percent * 0.72) + (memory_percent * 0.09)
    return round(max(watts, 2.5), 2), cpu_percent, memory_percent


def collect_power_snapshot() -> PowerSnapshot:
    measured_at = _now_iso()
    note = "Leitura exata depende de sensores de hardware. Este valor usa a melhor fonte disponivel."

    if platform.system().lower() == "windows":
        battery_watts, battery_runtime_minutes, battery_percent = _collect_battery_snapshot_windows()
        if battery_watts is not None:
            return PowerSnapshot(
                status="ok",
                watts=round(battery_watts, 2),
                source="battery_discharge",
                confidence=0.85,
                cpu_percent=None,
                memory_percent=None,
                battery_percent=battery_percent,
                battery_runtime_minutes=battery_runtime_minutes,
                note="Leitura derivada da descarga da bateria.",
                measured_at=measured_at,
            )

    estimated_watts, cpu_percent, memory_percent = _estimate_from_system_load()
    if estimated_watts is None:
        return PowerSnapshot(
            status="unavailable",
            watts=None,
            source="unavailable",
            confidence=None,
            cpu_percent=None,
            memory_percent=None,
            battery_percent=None,
            battery_runtime_minutes=None,
            note=note,
            measured_at=measured_at,
        )

    return PowerSnapshot(
        status="ok",
        watts=estimated_watts,
        source="system_load_model",
        confidence=0.35,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        battery_percent=None,
        battery_runtime_minutes=None,
        note=note,
        measured_at=measured_at,
    )
