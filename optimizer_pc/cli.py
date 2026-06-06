from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .cleanup import clean_temp_files
from .file_audit import collect_file_audit
from .network_audit import collect_network_audit
from .power import collect_power_snapshot
from .processes import list_top_processes
from .system_info import get_system_snapshot


def _dump(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Expose Otimizer PC data as JSON for the desktop GUI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("snapshot", help="Return the full system snapshot.")

    processes_parser = subparsers.add_parser("processes", help="Return the heaviest processes.")
    processes_parser.add_argument("--limit", type=int, default=8)

    network_parser = subparsers.add_parser("network", help="Return the network audit.")
    network_parser.add_argument("--limit", type=int, default=40)

    file_parser = subparsers.add_parser("files", help="Return the file modification audit.")
    file_parser.add_argument("--limit", type=int, default=40)
    file_parser.add_argument("--recent-days", type=int, default=7)
    file_parser.add_argument("--source", default=None)

    subparsers.add_parser("power", help="Return the power snapshot.")

    cleanup_parser = subparsers.add_parser("cleanup", help="Run the temp-file cleanup.")
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

    if args.command == "files":
        _dump(
            asdict(
                collect_file_audit(
                    limit=args.limit,
                    recent_days=args.recent_days,
                    source=args.source,
                )
            )
        )
        return

    if args.command == "power":
        _dump(asdict(collect_power_snapshot()))
        return

    if args.command == "cleanup":
        result = clean_temp_files(confirm=bool(args.confirm))
        _dump({"result": asdict(result)})
        return

    raise SystemExit(1)


if __name__ == "__main__":
    main()
