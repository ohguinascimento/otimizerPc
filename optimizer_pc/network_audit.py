from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import ipaddress
import os
import socket
from typing import Iterable, Optional


try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    psutil = None


@dataclass(frozen=True)
class NetworkConnectionInfo:
    pid: Optional[int]
    process_name: str
    exe_path: Optional[str]
    username: Optional[str]
    protocol: str
    status: str
    local_address: str
    local_port: Optional[int]
    remote_address: Optional[str]
    remote_port: Optional[int]
    risk_level: str
    risk_reasons: tuple[str, ...]


@dataclass(frozen=True)
class NetworkAuditSnapshot:
    status: str
    warning: Optional[str]
    generated_at: str
    total_connections: int
    established_connections: int
    listening_connections: int
    remote_connections: int
    suspicious_connections: int
    connections: list[NetworkConnectionInfo]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _endpoint_to_text(endpoint: object) -> tuple[str, Optional[int]]:
    if not endpoint:
        return "", None

    host = getattr(endpoint, "ip", None)
    port = getattr(endpoint, "port", None)

    if host is None and isinstance(endpoint, tuple):
        host = endpoint[0] if len(endpoint) > 0 else None
        port = endpoint[1] if len(endpoint) > 1 else None

    host_text = str(host or "")
    port_value = int(port) if port is not None else None
    return host_text, port_value


def _protocol_name(conn_type: object) -> str:
    if conn_type == socket.SOCK_STREAM:
        return "tcp"
    if conn_type == socket.SOCK_DGRAM:
        return "udp"
    return "unknown"


def _is_public_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False

    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _process_metadata(pid: Optional[int]) -> tuple[str, Optional[str], Optional[str]]:
    if psutil is None or pid is None:
        return "desconhecido", None, None

    try:
        proc = psutil.Process(pid)
        name = proc.name()
        exe_path = proc.exe()
        username = proc.username()
        return name or "desconhecido", exe_path or None, username or None
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError, OSError):
        return "desconhecido", None, None


def _collect_risk_reasons(
    process_name: str,
    exe_path: Optional[str],
    status: str,
    local_host: str,
    remote_host: Optional[str],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if process_name == "desconhecido":
        reasons.append("processo sem identificacao")

    if exe_path:
        normalized_path = exe_path.replace("/", "\\").lower()
        temp_markers = ("\\temp\\", "\\appdata\\local\\temp\\", "\\appdata\\roaming\\")
        if any(marker in normalized_path for marker in temp_markers):
            reasons.append("executavel em pasta temporaria")

    if status == "LISTEN":
        if local_host not in {"127.0.0.1", "::1", "localhost", ""} and not local_host.startswith("127."):
            reasons.append("porta exposta na rede")

    if remote_host and _is_public_ip(remote_host):
        reasons.append("conexao com endereco publico")

    return tuple(dict.fromkeys(reasons))


def _risk_level_from_reasons(reasons: Iterable[str]) -> str:
    reason_set = set(reasons)
    if "executavel em pasta temporaria" in reason_set and "conexao com endereco publico" in reason_set:
        return "alto"
    if "executavel em pasta temporaria" in reason_set:
        return "alto"
    if "conexao com endereco publico" in reason_set or "porta exposta na rede" in reason_set or "processo sem identificacao" in reason_set:
        return "medio"
    return "baixo"


def collect_network_audit(limit: int = 60) -> NetworkAuditSnapshot:
    if psutil is None:
        return NetworkAuditSnapshot(
            status="unavailable",
            warning="psutil nao esta instalado.",
            generated_at=_now_iso(),
            total_connections=0,
            established_connections=0,
            listening_connections=0,
            remote_connections=0,
            suspicious_connections=0,
            connections=[],
        )

    try:
        raw_connections = list(psutil.net_connections(kind="inet"))
    except (psutil.AccessDenied, psutil.NoSuchProcess, OSError) as exc:
        return NetworkAuditSnapshot(
            status="limited",
            warning=f"Acesso restrito ao inventario de rede: {exc.__class__.__name__}.",
            generated_at=_now_iso(),
            total_connections=0,
            established_connections=0,
            listening_connections=0,
            remote_connections=0,
            suspicious_connections=0,
            connections=[],
        )

    connections: list[NetworkConnectionInfo] = []
    established = 0
    listening = 0
    remote = 0

    for conn in raw_connections:
        pid = getattr(conn, "pid", None)
        process_name, exe_path, username = _process_metadata(pid)
        local_host, local_port = _endpoint_to_text(getattr(conn, "laddr", None))
        remote_host, remote_port = _endpoint_to_text(getattr(conn, "raddr", None))
        status = str(getattr(conn, "status", "") or "NONE").upper()
        protocol = _protocol_name(getattr(conn, "type", None))

        if status == "ESTABLISHED":
            established += 1
        if status == "LISTEN":
            listening += 1
        if remote_host:
            remote += 1

        reasons = _collect_risk_reasons(process_name, exe_path, status, local_host, remote_host)
        risk_level = _risk_level_from_reasons(reasons)

        connections.append(
            NetworkConnectionInfo(
                pid=pid,
                process_name=process_name,
                exe_path=exe_path,
                username=username,
                protocol=protocol,
                status=status,
                local_address=local_host or "0.0.0.0",
                local_port=local_port,
                remote_address=remote_host,
                remote_port=remote_port,
                risk_level=risk_level,
                risk_reasons=reasons,
            )
        )

    suspicious_connections = sum(1 for item in connections if item.risk_level != "baixo")

    def sort_key(item: NetworkConnectionInfo) -> tuple[int, int, int, str]:
        priority = {"alto": 0, "medio": 1, "baixo": 2}.get(item.risk_level, 3)
        status_priority = 0 if item.status == "ESTABLISHED" else 1 if item.status == "LISTEN" else 2
        remote_priority = 0 if item.remote_address else 1
        return priority, status_priority, remote_priority, item.process_name.lower()

    connections.sort(key=sort_key)
    connections = connections[: max(1, limit)]

    return NetworkAuditSnapshot(
        status="ok",
        warning=None,
        generated_at=_now_iso(),
        total_connections=len(raw_connections),
        established_connections=established,
        listening_connections=listening,
        remote_connections=remote,
        suspicious_connections=suspicious_connections,
        connections=connections,
    )
