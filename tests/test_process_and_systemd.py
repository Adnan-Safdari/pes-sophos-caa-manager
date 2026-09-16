from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sophos_caa.caa.process import caa_version, discover_caa
from sophos_caa.core.state import ProcessState
from sophos_caa.service.systemd import SystemdController


def test_discover_caa_uses_configured_executable(tmp_path: Path) -> None:
    command = tmp_path / "caa"
    command.write_text("#!/bin/sh\n", encoding="utf-8")
    command.chmod(0o700)

    assert discover_caa(str(command)) == command.resolve()


def test_discover_caa_rejects_non_executable(tmp_path: Path) -> None:
    command = tmp_path / "caa"
    command.write_text("", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="not executable"):
        discover_caa(str(command))


def test_caa_version_uses_argument_list(monkeypatch: pytest.MonkeyPatch) -> None:
    run = MagicMock(
        return_value=subprocess.CompletedProcess(
            ["/opt/caa", "--version"],
            0,
            "caa version 1.2.0\n",
            "",
        )
    )
    monkeypatch.setattr("sophos_caa.caa.process.subprocess.run", run)

    assert caa_version(Path("/opt/caa")) == "caa version 1.2.0"
    assert run.call_args.args[0] == ["/opt/caa", "--version"]


@pytest.mark.parametrize(
    ("active_state", "expected"),
    [
        ("active", ProcessState.RUNNING),
        ("activating", ProcessState.STARTING),
        ("inactive", ProcessState.STOPPED),
        ("failed", ProcessState.FAILED),
        ("unexpected", ProcessState.UNKNOWN),
    ],
)
def test_systemd_state_mapping(
    active_state: str,
    expected: ProcessState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = SystemdController()
    monkeypatch.setattr(
        controller,
        "_run",
        MagicMock(
            return_value=subprocess.CompletedProcess(
                ["systemctl"],
                0,
                f"{active_state}\n",
                "",
            )
        ),
    )

    assert controller.state() is expected


def test_systemd_failure_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = SystemdController()
    monkeypatch.setattr(
        controller,
        "_run",
        MagicMock(
            return_value=subprocess.CompletedProcess(
                ["systemctl"],
                1,
                "",
                "unit failed",
            )
        ),
    )

    with pytest.raises(RuntimeError, match="unit failed"):
        controller.start()
