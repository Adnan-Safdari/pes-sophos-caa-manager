"""Command-line interface for the running manager."""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Any

from sophos_caa.api import ManagerDBusClient
from sophos_caa.service.systemd import IndicatorController


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sophos-caa",
        description="Manage Sophos CAA authentication on Linux.",
        epilog="Run 'sophos-caa COMMAND --help' for command-specific options.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=28),
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", title="commands")
    descriptions = {
        "status": "Show CAA, authentication, and network status",
        "start": "Start CAA with a manual override",
        "stop": "Stop CAA with a manual override",
        "restart": "Restart the CAA process",
        "reauth": "Restart CAA to authenticate again",
        "enable-auto": "Enable network-aware automation",
        "disable-auto": "Disable network-aware automation",
        "network": "Show the current network decision",
        "show-indicator": "Start the desktop indicator",
        "hide-indicator": "Stop the desktop indicator",
        "restart-indicator": "Restart the desktop indicator",
        "help": "Show this command list",
        "list": "List available commands",
    }
    for name, description in descriptions.items():
        commands.add_parser(name, help=description, description=description)
    logs = commands.add_parser("logs", help="Show recent CAA and manager logs")
    logs.add_argument(
        "-n",
        "--lines",
        type=int,
        default=100,
        metavar="COUNT",
        help="number of journal lines to show (default: 100)",
    )
    return parser


def _status_text(state: dict[str, Any]) -> str:
    network = state["network"]
    return "\n".join(
        [
            "Sophos CAA",
            "",
            f"CAA process:   {state['process'].title()}",
            f"Authentication: {state['authentication'].title()}",
            f"Network:       {network['connection_id'] or 'Disconnected'}",
            f"Local IPv4:    {network['local_ipv4'] or '-'}",
            f"Gateway:       {network['gateway'] or '-'}",
            f"PES portal:    {'Reachable' if network['portal_reachable'] else 'Not reachable'}",
            f"Connectivity:  {network['connectivity'].title()}",
            f"Mode:          {'Automatic' if state['automatic'] else 'Manual'}",
            f"Override:      {state['override'].title()}",
            f"Error:         {state['last_error'] or '-'}",
        ]
    )


def _logs(lines: int) -> int:
    if not 1 <= lines <= 10_000:
        raise ValueError("--lines must be between 1 and 10000")
    return subprocess.run(
        [
            "journalctl",
            "--user",
            "-u",
            "sophos-caa-manager.service",
            "-u",
            "sophos-caa.service",
            "-n",
            str(lines),
            "--no-pager",
        ],
        check=False,
    ).returncode


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command in {None, "help", "list"}:
        parser.print_help()
        return 0
    if args.command == "logs":
        return _logs(args.lines)

    try:
        if args.command in {"show-indicator", "hide-indicator", "restart-indicator"}:
            indicator = IndicatorController()
            if args.command == "show-indicator":
                indicator.start()
            elif args.command == "hide-indicator":
                indicator.stop()
            else:
                indicator.restart()
            return 0

        client = ManagerDBusClient()
        if args.command == "status":
            print(_status_text(client.status()))
        elif args.command == "network":
            state = client.status()
            print(_status_text({**state, "process": "not shown"}))
        elif args.command == "start":
            client.call("Start")
        elif args.command == "stop":
            client.call("Stop")
        elif args.command == "restart":
            client.call("Restart")
        elif args.command == "reauth":
            client.call("Reauthenticate")
        elif args.command in {"enable-auto", "disable-auto"}:
            import gi

            gi.require_version("GLib", "2.0")
            from gi.repository import GLib

            client.call(
                "SetAutomaticMode",
                GLib.Variant("(b)", (args.command == "enable-auto",)),
            )
        return 0
    except Exception as exc:
        print(f"sophos-caa: {exc}", file=sys.stderr)
        print("Is sophos-caa-manager.service running?", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
