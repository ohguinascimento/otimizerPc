from types import SimpleNamespace
import socket

from optimizer_pc import network_audit


class FakeProcess:
    def __init__(self, pid, name, exe_path, username):
        self._pid = pid
        self._name = name
        self._exe_path = exe_path
        self._username = username

    def name(self):
        return self._name

    def exe(self):
        return self._exe_path

    def username(self):
        return self._username


class FakePsutil:
    @staticmethod
    def net_connections(kind="inet"):
        return [
            SimpleNamespace(
                pid=1001,
                type=socket.SOCK_STREAM,
                status="ESTABLISHED",
                laddr=SimpleNamespace(ip="192.168.1.20", port=51515),
                raddr=SimpleNamespace(ip="8.8.8.8", port=443),
            ),
            SimpleNamespace(
                pid=2002,
                type=socket.SOCK_STREAM,
                status="LISTEN",
                laddr=SimpleNamespace(ip="0.0.0.0", port=3389),
                raddr=None,
            ),
        ]

    @staticmethod
    def Process(pid):
        if pid == 1001:
            return FakeProcess(pid, "updater.exe", "C:\\Users\\User\\AppData\\Local\\Temp\\updater.exe", "User")
        if pid == 2002:
            return FakeProcess(pid, "svchost.exe", "C:\\Windows\\System32\\svchost.exe", "SYSTEM")
        raise network_audit.psutil.NoSuchProcess(pid)  # pragma: no cover - defensive

    class NoSuchProcess(Exception):
        pass

    class AccessDenied(Exception):
        pass

    class ZombieProcess(Exception):
        pass


def test_collect_network_audit_marks_suspicious_connections(monkeypatch):
    monkeypatch.setattr(network_audit, "psutil", FakePsutil)
    monkeypatch.setattr(network_audit, "_now_iso", lambda: "2026-05-15T00:00:00+00:00")

    snapshot = network_audit.collect_network_audit(limit=10)

    assert snapshot.status == "ok"
    assert snapshot.warning is None
    assert snapshot.total_connections == 2
    assert snapshot.established_connections == 1
    assert snapshot.listening_connections == 1
    assert snapshot.remote_connections == 1
    assert snapshot.suspicious_connections == 2
    assert len(snapshot.connections) == 2
    assert snapshot.connections[0].risk_level == "alto"
    assert "executavel em pasta temporaria" in snapshot.connections[0].risk_reasons
    assert "conexao com endereco publico" in snapshot.connections[0].risk_reasons


def test_collect_network_audit_without_psutil_is_unavailable(monkeypatch):
    monkeypatch.setattr(network_audit, "psutil", None)

    snapshot = network_audit.collect_network_audit(limit=10)

    assert snapshot.status == "unavailable"
    assert snapshot.warning is not None
    assert snapshot.connections == []
