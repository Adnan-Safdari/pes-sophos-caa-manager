"""Pure state and policy types used by every frontend."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ProcessState(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    RESTARTING = "restarting"
    FAILED = "failed"
    UNKNOWN = "unknown"


class AuthenticationState(StrEnum):
    STOPPED = "stopped"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    UNKNOWN = "unknown"


class Connectivity(StrEnum):
    UNKNOWN = "unknown"
    NONE = "none"
    PORTAL = "portal"
    LIMITED = "limited"
    FULL = "full"


class ManualOverride(StrEnum):
    NONE = "none"
    STARTED = "started"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class NetworkInfo:
    connection_id: str = ""
    connection_uuid: str = ""
    local_ipv4: str = ""
    gateway: str = ""
    connectivity: Connectivity = Connectivity.UNKNOWN
    portal_reachable: bool = False

    @property
    def fingerprint(self) -> str:
        if not self.connection_uuid and not self.local_ipv4:
            return ""
        return f"{self.connection_uuid}:{self.local_ipv4}"


@dataclass(slots=True)
class ManagerState:
    process: ProcessState = ProcessState.UNKNOWN
    authentication: AuthenticationState = AuthenticationState.UNKNOWN
    network: NetworkInfo = NetworkInfo()
    automatic: bool = True
    override: ManualOverride = ManualOverride.NONE
    last_error: str = ""

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["process"] = self.process.value
        result["authentication"] = self.authentication.value
        result["network"]["connectivity"] = self.network.connectivity.value
        result["override"] = self.override.value
        return result
