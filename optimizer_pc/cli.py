from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .cleanup import clean_temp_files
from .network_audit import collect_network_audit
from .processes import list_top_processes
from .system_info import get_system_snapshot


def _dump(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Expõe dados do Otimizer PC em JSON para a GUI desktop.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("snapshot", help="Retorna o snapshot completo do sistema.")

    processes_parser = subparsers.add_parser("processes", help="Retorna os processos mais pesados.")
    processes_parser.add_argument("--limit", type=int, default=8)

    network_parser = subparsers.add_parser("network", help="Retorna a auditoria de rede.")
    network_parser.add_argument("--limit", type=int, default=40)

    cleanup_parser = subparsers.add_parser("cleanup", help="Executa a limpeza dos temporários.")
    cleanup_parser.add_argument("--confirm", action="store_true")

    args = parser.parse_args()

    if args.command == "snapshot":
        _dump(asdict(get_system_snapshot()))
        return

    if args.command == "processes":
        _dump({"processes": [asdict(item) for item in list_top_processes(limit=args.limit)]})
        return

    if args.command == "network":
        _dump(asdict(collect_network_audit(limit=args.limit)))
        return

    if args.command == "cleanup":
        result = clean_temp_files(confirm=bool(args.confirm))
        _dump({"result": asdict(result)})
        return

    raise SystemExit(1)


if __name__ == "__main__":
    main()
