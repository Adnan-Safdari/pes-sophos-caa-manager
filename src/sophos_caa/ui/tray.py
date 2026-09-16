"""GTK/AppIndicator frontend; the manager continues when this exits."""

from __future__ import annotations

import fcntl
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from sophos_caa.api import ManagerDBusClient


class AlreadyRunningError(RuntimeError):
    """Raised when another indicator owns the user-session lock."""


class SingleInstanceLock:
    def __init__(self) -> None:
        runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
        descriptor = os.open(
            runtime / "sophos-caa-indicator.lock",
            os.O_CREAT | os.O_RDWR | os.O_CLOEXEC,
            0o600,
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(descriptor)
            raise AlreadyRunningError("Sophos CAA indicator is already running") from exc
        self.descriptor = descriptor


def _libraries() -> tuple[Any, Any, Any]:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk

    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator
    except ValueError:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3 as AppIndicator
    return AppIndicator, GLib, Gtk


class Tray:
    def __init__(self) -> None:
        self.instance_lock = SingleInstanceLock()
        self.AppIndicator, self.GLib, self.Gtk = _libraries()
        self.client = ManagerDBusClient()
        self.windows: list[Any] = []
        self.indicator = self.AppIndicator.Indicator.new(
            "sophos-caa-manager",
            "org.sophos.CAA-symbolic",
            self.AppIndicator.IndicatorCategory.SYSTEM_SERVICES,
        )
        self.indicator.set_status(self.AppIndicator.IndicatorStatus.ACTIVE)
        self.menu = self.Gtk.Menu()
        self.status_item = self._label("CAA status: Unknown")
        self.authentication_item = self._label("Authentication: Unknown")
        self.network_item = self._label("Network: Unknown")
        self.ip_item = self._label("IP: Unknown")
        self.portal_item = self._label("PES portal: Unknown")
        self._separator()
        self._action("Re-authenticate", "Reauthenticate")
        self._action("Start CAA", "Start")
        self._action("Stop CAA", "Stop")
        self._separator()
        self.auto_item = self.Gtk.CheckMenuItem(label="Automatic mode")
        self.auto_item.connect("toggled", self._toggle_auto)
        self.menu.append(self.auto_item)
        self._separator()
        self._action("View logs", "_logs")
        self._action("About", "_about")
        self._action("Hide indicator", "_quit")
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        self.client.proxy.connect("g-signal", self._signal)
        self._updating = False
        self.refresh()

    def _label(self, text: str) -> Any:
        item = self.Gtk.MenuItem(label=text)
        item.set_sensitive(False)
        self.menu.append(item)
        return item

    def _separator(self) -> None:
        self.menu.append(self.Gtk.SeparatorMenuItem())

    def _action(self, label: str, method: str) -> None:
        item = self.Gtk.MenuItem(label=label)
        item.connect("activate", self._activate, method)
        self.menu.append(item)

    def _activate(self, _item: Any, method: str) -> None:
        if method == "_quit":
            self.Gtk.main_quit()
            return
        if method == "_logs":
            self._show_logs()
            return
        if method == "_about":
            self._show_about()
            return
        try:
            self.client.call(method)
        except Exception as exc:
            print(f"sophos-caa-indicator: {exc}", file=sys.stderr)

    def _show_logs(self) -> None:
        result = subprocess.run(
            [
                "journalctl",
                "--user",
                "-u",
                "sophos-caa-manager.service",
                "-u",
                "sophos-caa.service",
                "-n",
                "200",
                "--no-pager",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        window = self.Gtk.Window(title="Sophos CAA Logs")
        window.set_default_size(760, 480)
        view = self.Gtk.TextView()
        view.set_editable(False)
        view.set_monospace(True)
        view.get_buffer().set_text(result.stdout or result.stderr or "No logs available.")
        scroll = self.Gtk.ScrolledWindow()
        scroll.add(view)
        window.add(scroll)
        window.connect("destroy", lambda item: self.windows.remove(item))
        self.windows.append(window)
        window.show_all()

    def _show_about(self) -> None:
        dialog = self.Gtk.AboutDialog()
        dialog.set_program_name("Sophos CAA Manager")
        dialog.set_version("0.1.0")
        dialog.set_logo_icon_name("org.sophos.CAA")
        dialog.set_comments(
            "Unofficial network-aware manager for the official Sophos CAA client.\n"
            "Not affiliated with or endorsed by Sophos."
        )
        dialog.set_license_type(self.Gtk.License.MIT_X11)
        dialog.run()
        dialog.destroy()

    def _toggle_auto(self, item: Any) -> None:
        if self._updating:
            return
        try:
            self.client.call("SetAutomaticMode", self.GLib.Variant("(b)", (item.get_active(),)))
        except Exception as exc:
            print(f"sophos-caa-indicator: {exc}", file=sys.stderr)

    def _signal(
        self,
        _proxy: Any,
        _sender: str,
        signal_name: str,
        _parameters: Any,
    ) -> None:
        if signal_name == "StateChanged":
            self.refresh()

    def refresh(self) -> None:
        state = self.client.status()
        network = state["network"]
        process = state["process"]
        self.status_item.set_label(f"CAA status: {process.title()}")
        authentication = state["authentication"]
        self.authentication_item.set_label(f"Authentication: {authentication.title()}")
        self.network_item.set_label(f"Network: {network['connection_id'] or 'Disconnected'}")
        self.ip_item.set_label(f"IP: {network['local_ipv4'] or '-'}")
        portal = "Reachable" if network["portal_reachable"] else "Not reachable"
        self.portal_item.set_label(f"PES portal: {portal}")
        self._updating = True
        self.auto_item.set_active(bool(state["automatic"]))
        self._updating = False
        icon = {
            "running": "org.sophos.CAA-symbolic",
            "starting": "org.sophos.CAA-connecting-symbolic",
            "restarting": "org.sophos.CAA-connecting-symbolic",
            "failed": "org.sophos.CAA-error-symbolic",
            "stopped": "org.sophos.CAA-inactive-symbolic",
        }.get(process, "org.sophos.CAA-inactive-symbolic")
        if authentication in {"connecting", "connected"}:
            icon = "org.sophos.CAA-connecting-symbolic"
        self.indicator.set_icon_full(icon, f"Sophos CAA: {process}")


def main() -> int:
    try:
        tray = Tray()
        _, _, Gtk = _libraries()
        Gtk.main()
        del tray
        return 0
    except AlreadyRunningError:
        return 0
    except Exception as exc:
        print(f"sophos-caa-indicator: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
