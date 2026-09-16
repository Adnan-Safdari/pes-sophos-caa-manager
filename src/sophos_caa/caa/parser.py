"""Normalize only output that has been observed from CAA 1.2.0."""

from __future__ import annotations

from enum import StrEnum


class CAAEvent(StrEnum):
    STARTED = "started"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class CAAOutputParser:
    def parse_line(self, line: str) -> CAAEvent:
        text = line.strip()
        if text == "caa started in foreground mode.":
            return CAAEvent.STARTED
        if text.startswith("Connecting to host "):
            return CAAEvent.CONNECTING
        if text.startswith("Connected with "):
            return CAAEvent.CONNECTED
        if text == "Login was accepted.":
            return CAAEvent.AUTHENTICATED
        if text.startswith("Running instance of caa terminated by signal "):
            return CAAEvent.STOPPED
        return CAAEvent.UNKNOWN
