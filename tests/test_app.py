from types import SimpleNamespace

from optimizer_pc import app


def test_format_snapshot_renders_detailed_system_info(monkeypatch):
    snapshot = SimpleNamespace(
        os_name="Windows",
        os_release="11",
        architecture="AMD64",
        cpu_cores_physical=8,
        cpu_cores_logical=16,
        memory_total_gb=32.0,
        memory_used_gb=12.5,
        memory_available_gb=19.5,
        memory_percent=39.1,
        disk=SimpleNamespace(
            used_gb=450.0,
            total_gb=512.0,
            free_gb=62.0,
            percent=87.9,
        ),
        system_drive="C:",
        storage_type="SSD",
        storage_model="Samsung SSD 970 EVO",
        motherboard=SimpleNamespace(
            manufacturer="ASUSTeK COMPUTER INC.",
            model="TUF GAMING B550M-PLUS",
            serial_number="ABC123",
        ),
        memory_upgrade=SimpleNamespace(
            installed_gb=16.0,
            total_slots=4,
            used_slots=2,
            free_slots=2,
            max_supported_gb=64.0,
            can_upgrade=True,
        ),
        temp_dir="C:\\Temp",
    )
    monkeypatch.setattr(app, "get_system_snapshot", lambda: snapshot)

    output = app.format_snapshot()

    assert "SO: Windows 11" in output
    assert "Memoria RAM: 12.5 / 32.0 GB (39.1%) | Disponivel: 19.5 GB" in output
    assert "Disco do sistema: C:\\" in output
    assert "Placa-mae: ASUSTeK COMPUTER INC. TUF GAMING B550M-PLUS" in output
    assert "Slots de memoria: 2 usados, 2 livres, 4 total" in output
    assert "RAM instalada: 16.0 GB" in output
    assert "Limite estimado da placa-mae: 64.0 GB" in output
    assert "Pode fazer upgrade de RAM: Sim" in output
    assert "Tipo de armazenamento: SSD (Samsung SSD 970 EVO)" in output


def test_format_processes_uses_top_process_list(monkeypatch):
    processes = [
        SimpleNamespace(pid=1234, cpu_percent=77.4, memory_mb=222.2, name="chrome.exe"),
        SimpleNamespace(pid=5678, cpu_percent=22.1, memory_mb=111.0, name="code.exe"),
    ]
    monkeypatch.setattr(app, "list_top_processes", lambda limit=10: processes)

    output = app.format_processes()

    assert "PID   CPU%   MEM(MB)  NOME" in output
    assert "1234" in output
    assert "chrome.exe" in output
    assert "5678" in output
    assert "code.exe" in output


def test_run_cleanup_formats_result(monkeypatch):
    monkeypatch.setattr(
        app,
        "clean_temp_files",
        lambda confirm=True: SimpleNamespace(
            deleted_files=3,
            deleted_folders=2,
            freed_mb=15.75,
            skipped=1,
        ),
    )

    output = app.run_cleanup(confirm=True)

    assert "Limpeza concluida." in output
    assert "Arquivos removidos: 3" in output
    assert "Pastas removidas: 2" in output
    assert "Espaco liberado: 15.75 MB" in output
    assert "Itens ignorados: 1" in output


def test_format_power_reports_power_snapshot(monkeypatch):
    monkeypatch.setattr(
        app,
        "collect_power_snapshot",
        lambda: SimpleNamespace(
            status="ok",
            watts=23.4,
            source="system_load_model",
            confidence=0.35,
            cpu_percent=18.2,
            memory_percent=41.0,
            battery_percent=None,
            battery_runtime_minutes=None,
            note="Leitura de teste.",
        ),
    )

    output = app.format_power()

    assert "Consumo da fonte:" in output
    assert "Consumo atual: 23.4 W" in output
    assert "Fonte da leitura: system_load_model" in output
    assert "Confianca: 35%" in output
    assert "CPU media: 18.2%" in output
    assert "RAM: 41.0%" in output
    assert "Leitura de teste." in output


def test_menu_includes_detailed_analysis_option():
    output = app.menu()

    assert "1. Ver analise detalhada do sistema" in output
    assert "4. Ver consumo da fonte" in output
    assert "5. Sair" in output


def test_handle_choice_rejects_invalid_option():
    assert app.handle_choice("99") == "Opcao invalida."
