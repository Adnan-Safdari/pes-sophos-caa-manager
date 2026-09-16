"""User-level bootstrap installer."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

from sophos_caa.caa.process import caa_version, discover_caa
from sophos_caa.config.config import Config
from sophos_caa.core.detector import PortalDetector


def _systemd_quote(value: str) -> str:
    if any(character in value for character in "\n\r\0"):
        raise ValueError("invalid character in executable path")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _write(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        with suppress(FileNotFoundError):
            os.unlink(temporary)


def _unit_contents() -> tuple[str, str, str]:
    caa_unit = f"""[Unit]
Description=Sophos Client Authentication Agent
After=network.target

[Service]
Type=simple
ExecStart={_systemd_quote(sys.executable)} -m sophos_caa.caa.runner --verbose
Restart=on-failure
RestartSec=5
KillSignal=SIGTERM
KillMode=mixed
TimeoutStopSec=10
NoNewPrivileges=yes
PrivateTmp=yes
"""
    manager_unit = f"""[Unit]
Description=Sophos CAA network manager
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart={_systemd_quote(sys.executable)} -m sophos_caa.main
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=default.target
"""
    indicator_unit = f"""[Unit]
Description=Sophos CAA desktop indicator
After=graphical-session.target sophos-caa-manager.service
Wants=sophos-caa-manager.service
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={_systemd_quote(sys.executable)} -m sophos_caa.ui.tray
Restart=on-failure
RestartSec=3
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=default.target
"""
    return caa_unit, manager_unit, indicator_unit


def _indicator_available() -> bool:
    try:
        import gi

        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
        except ValueError:
            gi.require_version("AppIndicator3", "0.1")
        return True
    except (ImportError, ValueError):
        return False


def _desktop_entry() -> str:
    cli = Path(sys.executable).parent / "sophos-caa"
    return f"""[Desktop Entry]
Type=Application
Name=Sophos CAA Manager
GenericName=Network Authentication
Comment=Show and control the unofficial Sophos CAA desktop indicator
Exec={cli} show-indicator
Icon=org.sophos.CAA
Terminal=false
StartupNotify=false
Categories=Network;
Keywords=Sophos;CAA;PES;Network;Authentication;
Actions=Reauthenticate;HideIndicator;

[Desktop Action Reauthenticate]
Name=Re-authenticate CAA
Exec={cli} reauth

[Desktop Action HideIndicator]
Name=Hide Indicator
Exec={cli} hide-indicator
"""


def _install_icons() -> None:
    source_root = Path(sys.prefix) / "share" / "icons" / "hicolor"
    target_root = Path.home() / ".local" / "share" / "icons" / "hicolor"
    relative_paths = [
        Path("scalable/apps/org.sophos.CAA.svg"),
        Path("symbolic/apps/org.sophos.CAA-symbolic.svg"),
        Path("symbolic/apps/org.sophos.CAA-connecting-symbolic.svg"),
        Path("symbolic/apps/org.sophos.CAA-error-symbolic.svg"),
        Path("symbolic/apps/org.sophos.CAA-inactive-symbolic.svg"),
    ]
    for relative in relative_paths:
        source = source_root / relative
        if not source.is_file():
            raise FileNotFoundError(f"packaged icon is missing: {source}")
        _write(target_root / relative, source.read_text(encoding="utf-8"))


def _run(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, check=check, text=True, capture_output=True)


def _has_running_caa() -> bool:
    return _run("pgrep", "-x", "caa", check=False).returncode == 0


def _warn_caa_config_permissions() -> None:
    path = Path.home() / ".caa" / "caa.conf"
    if not path.exists():
        print(f"Warning: expected CAA configuration was not found at {path}")
        return
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        print(f"Warning: {path} has mode {mode:04o}; consider restricting it to 0600.")


def _diagnostics(config: Config) -> None:
    user_systemd = _run("systemctl", "--user", "is-system-running", check=False)
    if user_systemd.returncode not in {0, 1}:
        raise RuntimeError(user_systemd.stderr.strip() or "systemd user manager is unavailable")
    network_manager = _run("nmcli", "-t", "-f", "RUNNING", "general", check=False)
    if network_manager.stdout.strip() != "running":
        raise RuntimeError("NetworkManager is not running")
    portal = PortalDetector(
        config.portal_host,
        config.portal_port,
        config.probe_timeout_seconds,
    ).probe()
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "unknown")
    print(
        f"Environment: {platform.system()} {platform.machine()}, "
        f"desktop={desktop}, PES portal={'reachable' if portal else 'not reachable'}"
    )


def _uninstall() -> int:
    units = ("sophos-caa-indicator.service", "sophos-caa-manager.service")
    for unit in units:
        _run("systemctl", "--user", "disable", "--now", unit, check=False)
    _run("systemctl", "--user", "stop", "sophos-caa.service", check=False)

    paths = [
        Path.home() / ".config" / "systemd" / "user" / "sophos-caa.service",
        Path.home() / ".config" / "systemd" / "user" / "sophos-caa-manager.service",
        Path.home() / ".config" / "systemd" / "user" / "sophos-caa-indicator.service",
        Path.home() / ".local" / "share" / "applications" / "org.sophos.CAA.desktop",
        Path.home() / ".config" / "autostart" / "org.sophos.CAA.Indicator.desktop",
    ]
    icon_root = Path.home() / ".local" / "share" / "icons" / "hicolor"
    paths.extend(
        [
            icon_root / "scalable/apps/org.sophos.CAA.svg",
            icon_root / "symbolic/apps/org.sophos.CAA-symbolic.svg",
            icon_root / "symbolic/apps/org.sophos.CAA-connecting-symbolic.svg",
            icon_root / "symbolic/apps/org.sophos.CAA-error-symbolic.svg",
            icon_root / "symbolic/apps/org.sophos.CAA-inactive-symbolic.svg",
        ]
    )
    for path in paths:
        path.unlink(missing_ok=True)
    _run("systemctl", "--user", "daemon-reload", check=False)
    print("Sophos CAA Manager removed. User configuration was preserved.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Sophos CAA Manager for this user")
    parser.add_argument(
        "--handover",
        action="store_true",
        help="briefly stop an existing manually-run CAA and start manager control now",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="stop and remove manager services, indicator, launcher, and icons",
    )
    args = parser.parse_args(argv)

    if args.uninstall:
        if not shutil.which("systemctl"):
            parser.error("required command not found: systemctl")
        return _uninstall()
    for command in ("systemctl", "nmcli"):
        if not shutil.which(command):
            parser.error(f"required command not found: {command}")
    caa = discover_caa()
    _warn_caa_config_permissions()
    config = Config.load()
    config.caa_command = str(caa)
    config.save()
    _diagnostics(config)

    user_units = Path.home() / ".config" / "systemd" / "user"
    caa_unit, manager_unit, indicator_unit = _unit_contents()
    _write(user_units / "sophos-caa.service", caa_unit)
    _write(user_units / "sophos-caa-manager.service", manager_unit)
    _write(user_units / "sophos-caa-indicator.service", indicator_unit)

    indicator_available = _indicator_available()
    if indicator_available:
        _install_icons()
        _write(
            Path.home() / ".local" / "share" / "applications" / "org.sophos.CAA.desktop",
            _desktop_entry(),
        )
        (Path.home() / ".config" / "autostart" / "org.sophos.CAA.Indicator.desktop").unlink(
            missing_ok=True
        )
    else:
        print("Indicator dependency unavailable; manager and CLI were installed.")

    _run("systemctl", "--user", "daemon-reload")
    _run("systemctl", "--user", "enable", "sophos-caa-manager.service")
    if indicator_available:
        _run("systemctl", "--user", "enable", "sophos-caa-indicator.service")
    else:
        _run(
            "systemctl",
            "--user",
            "disable",
            "--now",
            "sophos-caa-indicator.service",
            check=False,
        )
    running = _has_running_caa()
    if running and not args.handover:
        print("CAA is already running; it was not interrupted.")
        print("Run `sophos-caa-install --handover` when ready to transfer control.")
    else:
        if running:
            _run(str(caa), "--stop")
        _run("systemctl", "--user", "start", "sophos-caa-manager.service")

    manager_active = (
        _run(
            "systemctl",
            "--user",
            "is-active",
            "sophos-caa-manager.service",
            check=False,
        ).returncode
        == 0
    )
    if manager_active and indicator_available:
        _run("systemctl", "--user", "start", "sophos-caa-indicator.service")

    print(f"Installed with {caa_version(caa)} at {caa}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
