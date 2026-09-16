"""Event-driven NetworkManager D-Bus adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sophos_caa.core.state import NetworkInfo
from sophos_caa.network.connectivity import from_nm_value

NM_NAME = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"
NM_IFACE = "org.freedesktop.NetworkManager"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
ACTIVE_IFACE = "org.freedesktop.NetworkManager.Connection.Active"
IP4_IFACE = "org.freedesktop.NetworkManager.IP4Config"


def _gi() -> tuple[Any, Any]:
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    return Gio, GLib


class NetworkManagerClient:
    def __init__(self) -> None:
        Gio, _ = _gi()
        self._gio = Gio
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)

    def _proxy(self, path: str, interface: str) -> Any:
        return self._gio.DBusProxy.new_sync(
            self.bus,
            self._gio.DBusProxyFlags.NONE,
            None,
            NM_NAME,
            path,
            interface,
            None,
        )

    def snapshot(self, portal_reachable: bool) -> NetworkInfo:
        root = self._proxy(NM_PATH, NM_IFACE)
        connectivity_variant = root.get_cached_property("Connectivity")
        connectivity_value = int(connectivity_variant.unpack()) if connectivity_variant else 0
        connectivity = from_nm_value(connectivity_value)
        primary_variant = root.get_cached_property("PrimaryConnection")
        primary_path = str(primary_variant.unpack()) if primary_variant else "/"
        if primary_path == "/":
            return NetworkInfo(connectivity=connectivity, portal_reachable=portal_reachable)

        active = self._proxy(primary_path, ACTIVE_IFACE)
        connection_id = self._property(active, "Id", "")
        connection_uuid = self._property(active, "Uuid", "")
        ip4_path = self._property(active, "Ip4Config", "/")
        address = ""
        gateway = ""
        if ip4_path != "/":
            ip4 = self._proxy(ip4_path, IP4_IFACE)
            gateway = self._property(ip4, "Gateway", "")
            address_data = self._property(ip4, "AddressData", [])
            if address_data:
                address = str(address_data[0].get("address", ""))

        return NetworkInfo(
            connection_id=str(connection_id),
            connection_uuid=str(connection_uuid),
            local_ipv4=address,
            gateway=str(gateway),
            connectivity=connectivity,
            portal_reachable=portal_reachable,
        )

    @staticmethod
    def _property(proxy: Any, name: str, default: Any) -> Any:
        value = proxy.get_cached_property(name)
        return value.unpack() if value is not None else default

    def subscribe(self, callback: Callable[[], None]) -> list[int]:
        flags = self._gio.DBusSignalFlags.NONE

        def changed(*_args: Any) -> None:
            callback()

        subscriptions = [
            self.bus.signal_subscribe(
                NM_NAME,
                PROPERTIES_IFACE,
                "PropertiesChanged",
                None,
                None,
                flags,
                changed,
            ),
            self.bus.signal_subscribe(
                NM_NAME,
                NM_IFACE,
                "StateChanged",
                NM_PATH,
                None,
                flags,
                changed,
            ),
        ]
        return subscriptions
