from types import SimpleNamespace

from optimizer_pc import power


class FakePsutil:
    @staticmethod
    def cpu_percent(interval=0.0):
        return 18.5

    @staticmethod
    def virtual_memory():
        return SimpleNamespace(percent=42.0)

    @staticmethod
    def sensors_battery():
        return None


def test_collect_power_snapshot_uses_battery_reading_on_windows(monkeypatch):
    monkeypatch.setattr(power.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        power,
        "_run_powershell_first_success",
        lambda commands: "12.50|80|120",
    )

    snapshot = power.collect_power_snapshot()

    assert snapshot.status == "ok"
    assert snapshot.source == "battery_discharge"
    assert snapshot.watts == 12.5
    assert snapshot.battery_percent == 80.0
    assert snapshot.battery_runtime_minutes == 120
    assert snapshot.confidence == 0.85


def test_collect_power_snapshot_falls_back_to_system_load(monkeypatch):
    monkeypatch.setattr(power.platform, "system", lambda: "Linux")
    monkeypatch.setattr(power, "psutil", FakePsutil)

    snapshot = power.collect_power_snapshot()

    assert snapshot.status == "ok"
    assert snapshot.source == "system_load_model"
    assert snapshot.watts is not None
    assert snapshot.cpu_percent == 18.5
    assert snapshot.memory_percent == 42.0
    assert snapshot.confidence == 0.35
