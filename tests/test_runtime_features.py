from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from sophos_caa import cli
from sophos_caa.caa import runner
from sophos_caa.caa.journal import CAAJournalMonitor
from sophos_caa.core.state import (
    AuthenticationState,
    Connectivity,
    ManagerState,
    NetworkInfo,
)
from sophos_caa.ui import tray


def test_manager_state_serializes_authentication_state() -> None:
    state = ManagerState(
        authentication=AuthenticationState.AUTHENTICATED,
        network=NetworkInfo(connectivity=Connectivity.FULL),
    )

    result = state.as_dict()

    assert result["authentication"] == "authenticated"
    assert result["network"]["connectivity"] == "full"


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("caa started in foreground mode.\n", AuthenticationState.CONNECTING),
        ("Connecting to host 10.0.0.1 ...\n", AuthenticationState.CONNECTING),
        ("Connected with TLS encryption.\n", AuthenticationState.CONNECTED),
        ("Login was accepted.\n", AuthenticationState.AUTHENTICATED),
        (
            "Running instance of caa terminated by signal 15\n",
            AuthenticationState.STOPPED,
        ),
    ],
)
def test_journal_monitor_maps_observed_events(line: str, expected: AuthenticationState) -> None:
    idle_add = MagicMock()
    callback = MagicMock()
    monitor = CAAJournalMonitor(idle_add, callback)
    monitor.process = MagicMock(stdout=[line])

    monitor._read()

    idle_add.assert_called_once_with(callback, expected)


def test_journal_monitor_ignores_unknown_output() -> None:
    idle_add = MagicMock()
    monitor = CAAJournalMonitor(idle_add, MagicMock())
    monitor.process = MagicMock(stdout=["PONG sent!\n", "\n"])

    monitor._read()

    idle_add.assert_not_called()


def test_journal_monitor_starts_mocked_journal_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    process = MagicMock()
    popen = MagicMock(return_value=process)
    thread = MagicMock()
    thread_factory = MagicMock(return_value=thread)
    monkeypatch.setattr("sophos_caa.caa.journal.subprocess.Popen", popen)
    monkeypatch.setattr("sophos_caa.caa.journal.threading.Thread", thread_factory)
    monitor = CAAJournalMonitor(MagicMock(), MagicMock())

    monitor.start()
    monitor.start()

    popen.assert_called_once_with(
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
    thread_factory.assert_called_once_with(
        target=monitor._read,
        name="caa-journal",
        daemon=True,
    )
    thread.start.assert_called_once_with()


def test_journal_monitor_kills_reader_after_terminate_timeout() -> None:
    process = MagicMock()
    process.wait.side_effect = [subprocess.TimeoutExpired("journalctl", 2), 0]
    monitor = CAAJournalMonitor(MagicMock(), MagicMock())
    monitor.process = process

    monitor.stop()

    process.terminate.assert_called_once_with()
    process.kill.assert_called_once_with()
    assert process.wait.call_args_list == [call(timeout=2), call(timeout=2)]
    assert monitor.process is None


def test_runner_supervises_discovered_caa_with_original_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = MagicMock(caa_command="/configured/caa")
    executable = Path("/opt/sophos/caa")
    monkeypatch.setattr(runner.Config, "load", MagicMock(return_value=config))
    discover = MagicMock(return_value=executable)
    monkeypatch.setattr(runner, "discover_caa", discover)
    supervise = MagicMock(return_value=23)
    monkeypatch.setattr(runner, "run_supervised", supervise)
    monkeypatch.setattr(runner.sys, "argv", ["sophos-caa-run", "--verbose", "--flag"])

    assert runner.main() == 23

    discover.assert_called_once_with("/configured/caa")
    supervise.assert_called_once_with(executable, ["--verbose", "--flag"])


def test_runner_pty_supervisor_returns_child_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    try:
        result = runner.run_supervised(
            Path(sys.executable),
            ["-c", "print('flushed status')"],
        )
    except OSError as exc:
        pytest.skip(f"PTY unavailable in test sandbox: {exc}")

    assert result == 0
    assert "flushed status" in capsys.readouterr().out


def test_single_instance_lock_uses_private_runtime_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    lock = tray.SingleInstanceLock()

    try:
        path = tmp_path / "sophos-caa-indicator.lock"
        assert path.exists()
        assert path.stat().st_mode & 0o777 == 0o600
    finally:
        os.close(lock.descriptor)


def test_single_instance_lock_closes_descriptor_when_already_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    real_close = os.close
    close = MagicMock(side_effect=real_close)
    monkeypatch.setattr(tray.os, "close", close)
    monkeypatch.setattr(
        tray.fcntl,
        "flock",
        MagicMock(side_effect=BlockingIOError),
    )

    with pytest.raises(tray.AlreadyRunningError, match="already running"):
        tray.SingleInstanceLock()

    close.assert_called_once()


@pytest.mark.parametrize(
    ("command_name", "method_name"),
    [
        ("show-indicator", "start"),
        ("hide-indicator", "stop"),
        ("restart-indicator", "restart"),
    ],
)
def test_indicator_cli_lifecycle_does_not_open_ui_or_dbus(
    command_name: str,
    method_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = MagicMock()
    controller_class = MagicMock(return_value=controller)
    dbus_client = MagicMock(side_effect=AssertionError("D-Bus client should not be created"))
    monkeypatch.setattr(cli, "IndicatorController", controller_class)
    monkeypatch.setattr(cli, "ManagerDBusClient", dbus_client)

    assert cli.main([command_name]) == 0

    controller_class.assert_called_once_with()
    getattr(controller, method_name).assert_called_once_with()
    dbus_client.assert_not_called()


def test_cli_help_lists_described_commands_without_crowded_choices() -> None:
    help_text = cli._parser().format_help()

    assert "usage: sophos-caa [-h] COMMAND ..." in help_text
    assert "status" in help_text
    assert "Show CAA, authentication, and network status" in help_text
    assert "show-indicator" in help_text
    assert "{status,start,stop" not in help_text


@pytest.mark.parametrize("command", [[], ["help"], ["list"]])
def test_cli_help_commands_do_not_connect_to_dbus(
    command: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dbus_client = MagicMock(side_effect=AssertionError("D-Bus client should not be created"))
    monkeypatch.setattr(cli, "ManagerDBusClient", dbus_client)

    assert cli.main(command) == 0

    assert "commands:" in capsys.readouterr().out
    dbus_client.assert_not_called()


def test_logs_line_limit_is_a_logs_subcommand_option() -> None:
    args = cli._parser().parse_args(["logs", "--lines", "25"])

    assert args.command == "logs"
    assert args.lines == 25
