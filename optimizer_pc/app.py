from __future__ import annotations

from .cleanup import clean_temp_files
from .power import collect_power_snapshot
from .processes import list_top_processes
from .system_info import get_system_snapshot


def _display_drive(system_drive: str) -> str:
    return system_drive + "\\" if system_drive.endswith(":") else system_drive


def _format_optional_number(value: object, suffix: str = "") -> str:
    if value is None:
        return "n/d"
    return f"{value}{suffix}"


def _truncate_middle(value: str, limit: int = 60) -> str:
    if len(value) <= limit:
        return value
    if limit <= 3:
        return "..."
    head = max(1, (limit - 3) // 2)
    tail = max(1, limit - 3 - head)
    return f"{value[:head]}...{value[-tail:]}"


def format_snapshot() -> str:
    snapshot = get_system_snapshot()
    lines = [
        f"SO: {snapshot.os_name} {snapshot.os_release}",
        f"Arquitetura: {snapshot.architecture}",
        f"CPU: {snapshot.cpu_cores_physical or 'n/d'} fisicos, {snapshot.cpu_cores_logical or 'n/d'} logicos",
        f"Disco do sistema: {_display_drive(snapshot.system_drive)}",
        f"Temp: {_truncate_middle(snapshot.temp_dir)}",
    ]
    motherboard = getattr(snapshot, "motherboard", None)
    if motherboard is not None:
        board_details = motherboard.model or "Desconhecida"
        if motherboard.manufacturer:
            board_details = f"{motherboard.manufacturer} {board_details}".strip()
        lines.append(f"Placa-mae: {board_details}")
    if snapshot.memory_total_gb is not None:
        memory_line = (
            f"Memoria RAM: {snapshot.memory_used_gb} / {snapshot.memory_total_gb} GB"
            f" ({snapshot.memory_percent}%)"
        )
        if snapshot.memory_available_gb is not None:
            memory_line += f" | Disponivel: {snapshot.memory_available_gb} GB"
        lines.append(memory_line)
    if snapshot.disk is not None:
        lines.append(
            f"Disco: {snapshot.disk.used_gb} / {snapshot.disk.total_gb} GB"
            f" ({snapshot.disk.percent}%) | Livre: {snapshot.disk.free_gb} GB"
        )
    memory_upgrade = getattr(snapshot, "memory_upgrade", None)
    if memory_upgrade is not None:
        lines.append(
            "Slots de memoria: "
            f"{_format_optional_number(memory_upgrade.used_slots)} usados, "
            f"{_format_optional_number(memory_upgrade.free_slots)} livres, "
            f"{_format_optional_number(memory_upgrade.total_slots)} total"
        )
        if memory_upgrade.installed_gb is not None:
            lines.append(f"RAM instalada: {memory_upgrade.installed_gb} GB")
        if memory_upgrade.max_supported_gb is not None:
            lines.append(f"Limite estimado da placa-mae: {memory_upgrade.max_supported_gb} GB")
        if memory_upgrade.can_upgrade is True:
            upgrade_text = "Sim"
        elif memory_upgrade.can_upgrade is False:
            upgrade_text = "Nao"
        else:
            upgrade_text = "Indisponivel"
        lines.append(f"Pode fazer upgrade de RAM: {upgrade_text}")
    storage_details = snapshot.storage_type or "Desconhecido"
    if snapshot.storage_model:
        storage_details += f" ({snapshot.storage_model})"
    lines.append(f"Tipo de armazenamento: {storage_details}")
    return "\n".join(lines)


def format_processes(limit: int = 10) -> str:
    processes = list_top_processes(limit=limit)
    if not processes:
        return "psutil nao esta instalado. Instale para ver a lista de processos."

    lines = ["PID   CPU%   MEM(MB)  NOME"]
    for process in processes:
        lines.append(
            f"{process.pid:<5} {process.cpu_percent:>5.1f} {process.memory_mb:>8.1f}  {process.name}"
        )
    return "\n".join(lines)


def run_cleanup(confirm: bool = True) -> str:
    result = clean_temp_files(confirm=confirm)
    return (
        "Limpeza concluida.\n"
        f"Arquivos removidos: {result.deleted_files}\n"
        f"Pastas removidas: {result.deleted_folders}\n"
        f"Espaco liberado: {result.freed_mb} MB\n"
        f"Itens ignorados: {result.skipped}"
    )


def format_power() -> str:
    snapshot = collect_power_snapshot()
    lines = [
        "Consumo da fonte:",
        f"Status: {snapshot.status}",
        f"Consumo atual: {snapshot.watts if snapshot.watts is not None else 'n/d'} W",
        f"Fonte da leitura: {snapshot.source}",
    ]
    if snapshot.confidence is not None:
        lines.append(f"Confianca: {snapshot.confidence * 100:.0f}%")
    if snapshot.cpu_percent is not None:
        lines.append(f"CPU media: {snapshot.cpu_percent}%")
    if snapshot.memory_percent is not None:
        lines.append(f"RAM: {snapshot.memory_percent}%")
    if snapshot.battery_percent is not None:
        lines.append(f"Bateria: {snapshot.battery_percent}%")
    if snapshot.battery_runtime_minutes is not None:
        lines.append(f"Autonomia estimada: {snapshot.battery_runtime_minutes} min")
    if snapshot.note:
        lines.append(snapshot.note)
    return "\n".join(lines)


def menu() -> str:
    return (
        "Otimizer PC\n"
        "1. Ver analise detalhada do sistema\n"
        "2. Ver processos pesados\n"
        "3. Limpar arquivos temporarios\n"
        "4. Ver consumo da fonte\n"
        "5. Sair\n"
    )


def handle_choice(choice: str) -> str:
    actions = {
        "1": format_snapshot,
        "2": format_processes,
        "4": format_power,
        "5": lambda: "Encerrando.",
    }
    action = actions.get(choice.strip())
    if action is None:
        return "Opcao invalida."
    return action()


def run_cli() -> None:
    while True:
        print(menu())
        choice = input("Escolha uma opcao: ").strip()
        if choice == "3":
            confirm = input("Confirma limpar os temporarios? (s/N): ").strip().lower()
            result = run_cleanup(confirm=confirm == "s")
        else:
            result = handle_choice(choice)
        print("\n" + result + "\n")
        if choice == "4":
            break
