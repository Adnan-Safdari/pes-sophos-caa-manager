from __future__ import annotations

from sophos_caa.core.controller import Action, AutomationPolicy
from sophos_caa.core.state import ManualOverride, NetworkInfo, ProcessState

HOME = NetworkInfo(
    connection_uuid="home",
    local_ipv4="192.168.1.20",
    portal_reachable=False,
)
PES = NetworkInfo(
    connection_uuid="pes",
    local_ipv4="10.10.0.20",
    portal_reachable=True,
)
PES_NEW_IP = NetworkInfo(
    connection_uuid="pes",
    local_ipv4="10.10.0.21",
    portal_reachable=True,
)


def evaluate(
    policy: AutomationPolicy,
    network: NetworkInfo,
    process: ProcessState,
    override: ManualOverride = ManualOverride.NONE,
) -> Action:
    return policy.evaluate(network, process, automatic=True, override=override)


def test_home_to_pes_starts_stopped_caa() -> None:
    policy = AutomationPolicy()
    assert evaluate(policy, HOME, ProcessState.STOPPED) is Action.NONE
    assert evaluate(policy, PES, ProcessState.STOPPED) is Action.START


def test_pes_ip_change_restarts_running_caa() -> None:
    policy = AutomationPolicy()
    assert evaluate(policy, PES, ProcessState.STOPPED) is Action.START
    assert evaluate(policy, PES_NEW_IP, ProcessState.RUNNING) is Action.RESTART


def test_first_observation_does_not_restart_an_existing_caa() -> None:
    policy = AutomationPolicy()
    assert evaluate(policy, PES, ProcessState.RUNNING) is Action.NONE


def test_pes_to_home_stops_running_caa() -> None:
    policy = AutomationPolicy()
    assert evaluate(policy, PES, ProcessState.STOPPED) is Action.START
    assert evaluate(policy, HOME, ProcessState.RUNNING) is Action.STOP


def test_manual_override_suppresses_automation_on_same_network() -> None:
    policy = AutomationPolicy()
    assert evaluate(policy, PES, ProcessState.STOPPED) is Action.START
    assert evaluate(policy, PES, ProcessState.STOPPED, ManualOverride.STOPPED) is Action.NONE


def test_disabling_automatic_mode_suppresses_actions() -> None:
    action = AutomationPolicy().evaluate(
        PES,
        ProcessState.STOPPED,
        automatic=False,
        override=ManualOverride.NONE,
    )
    assert action is Action.NONE
