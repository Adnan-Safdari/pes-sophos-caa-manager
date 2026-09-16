"""Manager daemon entry point."""

from __future__ import annotations

import logging
import signal

from sophos_caa.api import ManagerDBusService
from sophos_caa.caa.journal import CAAJournalMonitor
from sophos_caa.config.config import Config
from sophos_caa.manager import CAAManager
from sophos_caa.network.network_manager import NetworkManagerClient
from sophos_caa.service.systemd import SystemdController


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    import gi

    gi.require_version("GLib", "2.0")
    from gi.repository import GLib

    config = Config.load()
    manager = CAAManager(config, NetworkManagerClient(), SystemdController(), GLib)
    api = ManagerDBusService(manager)
    journal = CAAJournalMonitor(GLib.idle_add, manager.set_authentication)
    loop = GLib.MainLoop()

    def stop() -> bool:
        loop.quit()
        return False

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, stop)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, stop)
    manager.start()
    journal.start()
    logging.getLogger(__name__).info("Sophos CAA Manager started")
    loop.run()
    journal.stop()
    del api
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
