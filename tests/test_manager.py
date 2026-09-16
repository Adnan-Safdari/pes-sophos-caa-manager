from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sophos_caa.config.config import Config
from sophos_caa.core.state import (
    AuthenticationState,
    ManualOverride,
    NetworkInfo,
    ProcessState,
)
from sophos_caa.manager import CAAManager


class FakeGLib:
    def __init__(self) -> None:
        self.next_source = 1
        self.timeouts: list[tuple[int, Callable[[], bool], int]] = []
        self.second_timeouts: list[tuple[int, Callable[[], bool], int]] = []
        self.removed: list[int] = []

    def timeout_add(self, delay: int, callback: Callable[[], bool]) -> int:
        source = self.next_source
        self.next_source += 1
        self.timeouts.append((delay, callback, source))
        return source

    def timeout_add_seconds(self, delay: int, callback: Callable[[], bool]) -> int:
        source = self.next_source
        self.next_source += 1
        self.second_timeouts.append((delay, callback, source))
        return source

    def source_remove(self, source: int) -> None:
        self.removed.append(source)


class FakeNetwork:
    def __init__(self, snapshot: NetworkInfo) -> None:
        self.current = snapshot
        self.subscriber: Callable[[], None] | None = None
        self.error: Exception | None = None

    def subscribe(self, callback: Callable[[], None]) -> list[int]:
        self.subscriber = callback
        return [10, 11]

    def snapshot(self, portal_reachable: bool) -> NetworkInfo:
        if self.error is not None:
            raise self.error
        return NetworkInfo(
            connection_id=self.current.connection_id,
            connection_uuid=self.current.connection_uuid,
            local_ipv4=self.current.local_ipv4,
            gateway=self.current.gateway,
            connectivity=self.current.connectivity,
            portal_reachable=portal_reachable,
        )


class FakeService:
    def __init__(self, state: ProcessState = ProcessState.STOPPED) -> None:
        self.current = state
        self.calls: list[str] = []

    def state(self) -> ProcessState:
        return self.current

    def start(self) -> None:
        self.calls.append("start")
        self.current = ProcessState.RUNNING

    def stop(self) -> None:
        self.calls.append("stop")
        self.current = ProcessState.STOPPED

    def restart(self) -> None:
        self.calls.append("restart")
        self.current = ProcessState.RUNNING


class FakeDetector:
    def __init__(self, reachable: bool = True) -> None:
        self.reachable = reachable
        self.calls = 0

    def probe(self) -> bool:
        self.calls += 1
        return self.reachable


def make_manager(
    *,
    network_info: NetworkInfo | None = None,
    process: ProcessState = ProcessState.STOPPED,
) -> tuple[CAAManager, FakeGLib, FakeNetwork, FakeService, FakeDetector]:
    glib = FakeGLib()
    network = FakeNetwork(network_info or NetworkInfo(connection_uuid="pes", local_ipv4="10.0.0.2"))
    service = FakeService(process)
    detector = FakeDetector()
    manager = CAAManager(
        Config(debounce_seconds=2, retry_seconds=(3, 7)),
        network,  # type: ignore[arg-type]
        service,  # type: ignore[arg-type]
        glib,
    )
    manager.detector = detector  # type: ignore[assignment]
    return manager, glib, network, service, detector


def test_start_subscribes_and_schedules_immediate_evaluation() -> None:
    manager, glib, network, _, _ = make_manager()

    manager.start()

    assert network.subscriber == manager.schedule_evaluation
    assert glib.timeouts[0][0] == 1


def test_network_events_are_debounced_and_replace_pending_source() -> None:
    manager, glib, _, _, _ = make_manager()

    manager.schedule_evaluation()
    first_source = manager._debounce_source
    manager.schedule_evaluation()

    assert glib.removed == [first_source]
    assert [delay for delay, _, _ in glib.timeouts] == [2000, 2000]


def test_evaluation_starts_caa_on_reachable_pes_network() -> None:
    manager, _, _, service, detector = make_manager()
    notifications: list[Any] = []
    manager.add_listener(notifications.append)

    assert manager._evaluate() is False

    assert detector.calls == 1
    assert service.calls == ["start"]
    assert manager.state.process is ProcessState.RUNNING
    assert manager.state.last_error == ""
    assert len(notifications) == 1


def test_failure_uses_bounded_retry_backoff_without_duplicate_timer() -> None:
    manager, glib, network, _, _ = make_manager()
    network.error = RuntimeError("D-Bus unavailable")

    manager._evaluate()
    manager._evaluate()

    assert manager.state.last_error == "D-Bus unavailable"
    assert [delay for delay, _, _ in glib.second_timeouts] == [3]
    assert manager._retry_index == 1

    _, retry_callback, _ = glib.second_timeouts[0]
    assert retry_callback() is False
    assert manager._retry_source == 0
    assert glib.timeouts[-1][0] == 1


def test_successful_evaluation_cancels_a_pending_retry() -> None:
    manager, glib, network, _, _ = make_manager()
    network.error = RuntimeError("temporary failure")
    manager._evaluate()
    retry_source = manager._retry_source

    network.error = None
    manager._evaluate()

    assert retry_source in glib.removed
    assert manager._retry_source == 0


def test_manual_stop_is_honored_until_network_fingerprint_changes() -> None:
    manager, _, network, service, _ = make_manager()
    manager._evaluate()

    manager.manual_stop()
    assert manager.state.override is ManualOverride.STOPPED
    assert service.calls == ["start", "stop"]

    manager._evaluate()
    assert service.calls == ["start", "stop"]
    assert manager.state.override is ManualOverride.STOPPED

    network.current = NetworkInfo(
        connection_uuid="pes",
        local_ipv4="10.0.0.3",
    )
    manager._evaluate()
    assert manager.state.override is ManualOverride.NONE
    assert service.calls == ["start", "stop", "start"]


def test_manual_start_and_restart_refresh_state() -> None:
    manager, _, _, service, _ = make_manager()
    manager._retry_index = 2

    manager.manual_start()
    manager.manual_restart()

    assert service.calls == ["start", "restart"]
    assert manager.state.override is ManualOverride.STARTED
    assert manager.state.process is ProcessState.RUNNING
    assert manager._retry_index == 0


def test_stale_stopped_authentication_is_not_reported_for_running_process() -> None:
    manager, _, _, _, _ = make_manager(process=ProcessState.RUNNING)

    assert manager.set_authentication(AuthenticationState.STOPPED) is False

    assert manager.state.authentication is AuthenticationState.UNKNOWN
