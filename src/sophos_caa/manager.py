"""Long-running event-driven manager."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sophos_caa.config.config import Config
from sophos_caa.core.controller import Action, AutomationPolicy
from sophos_caa.core.detector import PortalDetector
from sophos_caa.core.state import (
    AuthenticationState,
    ManagerState,
    ManualOverride,
    ProcessState,
)
from sophos_caa.network.network_manager import NetworkManagerClient
from sophos_caa.service.systemd import SystemdController

LOGGER = logging.getLogger(__name__)


class CAAManager:
    def __init__(
        self,
        config: Config,
        network: NetworkManagerClient,
        service: SystemdController,
        glib: Any,
    ) -> None:
        self.config = config
        self.network_client = network
        self.service = service
        self.glib = glib
        self.detector = PortalDetector(
            config.portal_host,
            config.portal_port,
            config.probe_timeout_seconds,
        )
        self.policy = AutomationPolicy()
        self.state = ManagerState(automatic=config.automatic)
        self._debounce_source = 0
        self._retry_source = 0
        self._retry_index = 0
        self._last_fingerprint: str | None = None
        self._listeners: list[Callable[[ManagerState], None]] = []

    def start(self) -> None:
        self.network_client.subscribe(self.schedule_evaluation)
        self.schedule_evaluation(immediate=True)

    def add_listener(self, listener: Callable[[ManagerState], None]) -> None:
        self._listeners.append(listener)

    def schedule_evaluation(self, immediate: bool = False) -> None:
        if self._debounce_source:
            self.glib.source_remove(self._debounce_source)
        milliseconds = 1 if immediate else int(self.config.debounce_seconds * 1000)
        self._debounce_source = self.glib.timeout_add(milliseconds, self._evaluate)

    def _evaluate(self) -> bool:
        self._debounce_source = 0
        try:
            reachable = self.detector.probe()
            network = self.network_client.snapshot(reachable)
            fingerprint_changed = (
                self._last_fingerprint is not None and network.fingerprint != self._last_fingerprint
            )
            self._last_fingerprint = network.fingerprint
            if fingerprint_changed:
                self.state.override = ManualOverride.NONE
                self._retry_index = 0
            self.state.network = network
            self.state.process = self.service.state()
            if self.state.process is ProcessState.STOPPED:
                self.state.authentication = AuthenticationState.STOPPED
            action = self.policy.evaluate(
                network,
                self.state.process,
                automatic=self.state.automatic,
                override=self.state.override,
            )
            self._perform(action)
            self.state.last_error = ""
            if self._retry_source:
                self.glib.source_remove(self._retry_source)
                self._retry_source = 0
        except Exception as exc:
            LOGGER.exception("Network evaluation failed")
            self.state.last_error = str(exc)
            self._schedule_retry()
        self._notify()
        return False

    def _perform(self, action: Action) -> None:
        if action is Action.START:
            self.state.process = ProcessState.STARTING
            self.service.start()
        elif action is Action.STOP:
            self.service.stop()
        elif action is Action.RESTART:
            self.state.process = ProcessState.RESTARTING
            self.service.restart()
        if action is not Action.NONE:
            self.state.process = self.service.state()
            LOGGER.info("CAA action completed: %s", action.value)

    def _schedule_retry(self) -> None:
        if self._retry_source:
            return
        last_index = len(self.config.retry_seconds) - 1
        delay = self.config.retry_seconds[min(self._retry_index, last_index)]
        self._retry_index += 1
        self._retry_source = self.glib.timeout_add_seconds(delay, self._retry)
        LOGGER.warning("Retrying manager evaluation in %s seconds", delay)

    def _retry(self) -> bool:
        self._retry_source = 0
        self.schedule_evaluation(immediate=True)
        return False

    def manual_start(self) -> None:
        self.state.override = ManualOverride.STARTED
        self.service.start()
        self._refresh()

    def manual_stop(self) -> None:
        self.state.override = ManualOverride.STOPPED
        self.service.stop()
        self._refresh()

    def manual_restart(self) -> None:
        self.state.override = ManualOverride.STARTED
        self._retry_index = 0
        self.service.restart()
        self._refresh()

    def set_automatic(self, enabled: bool) -> None:
        self.state.automatic = enabled
        self.state.override = ManualOverride.NONE
        self.config.automatic = enabled
        self.config.save()
        self.schedule_evaluation(immediate=True)
        self._notify()

    def set_authentication(self, authentication: AuthenticationState) -> bool:
        if (
            authentication is AuthenticationState.STOPPED
            and self.service.state() is ProcessState.RUNNING
        ):
            authentication = AuthenticationState.UNKNOWN
        self.state.authentication = authentication
        self._notify()
        return False

    def _refresh(self) -> None:
        self.state.process = self.service.state()
        if self.state.process is ProcessState.STOPPED:
            self.state.authentication = AuthenticationState.STOPPED
        self.state.last_error = ""
        self._notify()

    def _notify(self) -> None:
        for listener in self._listeners:
            listener(self.state)
