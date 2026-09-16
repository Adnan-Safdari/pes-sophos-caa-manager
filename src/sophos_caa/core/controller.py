"""Network-aware CAA lifecycle policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .state import ManualOverride, NetworkInfo, ProcessState


class Action(StrEnum):
    NONE = "none"
    START = "start"
    STOP = "stop"
    RESTART = "restart"


@dataclass(slots=True)
class AutomationPolicy:
    """Decide one idempotent action from the latest observed state."""

    previous_fingerprint: str | None = None

    def evaluate(
        self,
        network: NetworkInfo,
        process: ProcessState,
        *,
        automatic: bool,
        override: ManualOverride,
    ) -> Action:
        fingerprint_changed = (
            self.previous_fingerprint is not None
            and network.fingerprint != self.previous_fingerprint
        )
        self.previous_fingerprint = network.fingerprint
        if fingerprint_changed:
            override = ManualOverride.NONE

        if not automatic or override is not ManualOverride.NONE:
            return Action.NONE

        if not network.portal_reachable:
            inactive = {ProcessState.STOPPED, ProcessState.UNKNOWN}
            return Action.STOP if process not in inactive else Action.NONE

        if process in {ProcessState.STOPPED, ProcessState.FAILED, ProcessState.UNKNOWN}:
            return Action.START

        if fingerprint_changed and process is ProcessState.RUNNING:
            return Action.RESTART

        return Action.NONE
