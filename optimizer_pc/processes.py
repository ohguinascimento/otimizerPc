from __future__ import annotations

from dataclasses import dataclass
import time
from typing import List


try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    psutil = None


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float


def list_top_processes(limit: int = 10, interval: float = 0.1) -> List[ProcessInfo]:
    if psutil is None:
        return []

    sampled_processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            info = proc.info
            proc.cpu_percent(interval=None)
            sampled_processes.append((proc, info))
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            continue

    if not sampled_processes:
        return []

    if interval > 0:
        time.sleep(interval)

    processes: List[ProcessInfo] = []
    for proc, info in sampled_processes:
        try:
            mem_info = info.get("memory_info")
            cpu_percent = proc.cpu_percent(interval=None)
            processes.append(
                ProcessInfo(
                    pid=int(info.get("pid") or 0),
                    name=str(info.get("name") or "desconhecido"),
                    cpu_percent=float(cpu_percent or 0.0),
                    memory_mb=round((mem_info.rss / (1024 ** 2)) if mem_info else 0.0, 1),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            continue

    processes.sort(key=lambda item: (item.cpu_percent, item.memory_mb), reverse=True)
    return processes[:limit]


def terminate_process(pid: int) -> bool:
    if psutil is None:
        raise RuntimeError("psutil nao esta instalado.")

    proc = psutil.Process(pid)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except psutil.TimeoutExpired:
        proc.kill()
    return True
