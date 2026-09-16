"""Event-driven authentication state monitoring from the user journal."""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable
from typing import Any

from sophos_caa.caa.parser import CAAEvent, CAAOutputParser
from sophos_caa.core.state import AuthenticationState

EVENT_STATES = {
    CAAEvent.STARTED: AuthenticationState.CONNECTING,
    CAAEvent.CONNECTING: AuthenticationState.CONNECTING,
    CAAEvent.CONNECTED: AuthenticationState.CONNECTED,
    CAAEvent.AUTHENTICATED: AuthenticationState.AUTHENTICATED,
    CAAEvent.STOPPED: AuthenticationState.STOPPED,
}


class CAAJournalMonitor:
    def __init__(
        self,
        idle_add: Callable[..., Any],
        callback: Callable[[AuthenticationState], Any],
    ) -> None:
        self.idle_add = idle_add
        self.callback = callback
        self.parser = CAAOutputParser()
        self.process: subprocess.Popen[str] | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.process is not None:
            return
        self.process = subprocess.Popen(
            [
                "journalctl",
                "--user",
                "-u",
                "sophos-caa.service",
                "-n",
                "30",
                "-f",
                "-o",
                "cat",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self.thread = threading.Thread(target=self._read, name="caa-journal", daemon=True)
        self.thread.start()

    def _read(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            state = EVENT_STATES.get(self.parser.parse_line(line))
            if state is not None:
                self.idle_add(self.callback, state)

    def stop(self) -> None:
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)
        self.process = None
