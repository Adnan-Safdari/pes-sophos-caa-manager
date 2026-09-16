"""Small session D-Bus API shared by the CLI and indicator."""

from __future__ import annotations

import json
from typing import Any

from sophos_caa.manager import CAAManager

BUS_NAME = "org.sophos.CAA"
OBJECT_PATH = "/org/sophos/CAA"
INTERFACE = "org.sophos.CAA"

INTROSPECTION_XML = f"""
<node>
  <interface name="{INTERFACE}">
    <method name="Start"/>
    <method name="Stop"/>
    <method name="Restart"/>
    <method name="Reauthenticate"/>
    <method name="GetStatus"><arg direction="out" type="s" name="json"/></method>
    <method name="GetNetwork"><arg direction="out" type="s" name="json"/></method>
    <method name="SetAutomaticMode"><arg direction="in" type="b" name="enabled"/></method>
    <signal name="StateChanged"><arg type="s" name="json"/></signal>
  </interface>
</node>
"""


def _gi() -> tuple[Any, Any]:
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    return Gio, GLib


class ManagerDBusService:
    def __init__(self, manager: CAAManager) -> None:
        Gio, GLib = _gi()
        self.gio = Gio
        self.glib = GLib
        self.manager = manager
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = self.connection.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "RequestName",
            GLib.Variant("(su)", (BUS_NAME, 4)),
            GLib.VariantType("(u)"),
            Gio.DBusCallFlags.NONE,
            5_000,
            None,
        )
        if reply.unpack()[0] not in {1, 4}:
            raise RuntimeError("another Sophos CAA Manager instance is already running")
        node = Gio.DBusNodeInfo.new_for_xml(INTROSPECTION_XML)
        self.interface_info = node.interfaces[0]
        self.registration_id = self.connection.register_object(
            OBJECT_PATH,
            self.interface_info,
            self._method_call,
            None,
            None,
        )
        self.owner_id = Gio.bus_own_name_on_connection(
            self.connection,
            BUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            None,
            None,
        )
        manager.add_listener(self.emit_state)

    def _method_call(
        self,
        _connection: Any,
        _sender: str,
        _path: str,
        _interface: str,
        method: str,
        parameters: Any,
        invocation: Any,
    ) -> None:
        try:
            if method == "Start":
                self.manager.manual_start()
                invocation.return_value(None)
            elif method == "Stop":
                self.manager.manual_stop()
                invocation.return_value(None)
            elif method in {"Restart", "Reauthenticate"}:
                self.manager.manual_restart()
                invocation.return_value(None)
            elif method == "GetStatus":
                invocation.return_value(self.glib.Variant("(s)", (self._state_json(),)))
            elif method == "GetNetwork":
                payload = json.dumps(self.manager.state.as_dict()["network"])
                invocation.return_value(self.glib.Variant("(s)", (payload,)))
            elif method == "SetAutomaticMode":
                enabled = bool(parameters.unpack()[0])
                self.manager.set_automatic(enabled)
                invocation.return_value(None)
            else:
                invocation.return_dbus_error(
                    f"{INTERFACE}.UnknownMethod",
                    f"Unknown method {method}",
                )
        except Exception as exc:
            invocation.return_dbus_error(f"{INTERFACE}.Error", str(exc))

    def _state_json(self) -> str:
        return json.dumps(self.manager.state.as_dict())

    def emit_state(self, _state: Any) -> None:
        self.connection.emit_signal(
            None,
            OBJECT_PATH,
            INTERFACE,
            "StateChanged",
            self.glib.Variant("(s)", (self._state_json(),)),
        )


class ManagerDBusClient:
    def __init__(self) -> None:
        Gio, _ = _gi()
        self.gio = Gio
        self.proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            BUS_NAME,
            OBJECT_PATH,
            INTERFACE,
            None,
        )

    def call(self, method: str, parameters: Any = None) -> Any:
        result = self.proxy.call_sync(
            method,
            parameters,
            self.gio.DBusCallFlags.NONE,
            10_000,
            None,
        )
        return result.unpack() if result is not None else ()

    def status(self) -> dict[str, Any]:
        payload = self.call("GetStatus")[0]
        decoded: dict[str, Any] = json.loads(payload)
        return decoded
