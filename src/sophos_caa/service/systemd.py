"""Safe adapter for the systemd user manager."""

from __future__ import annotations

import subprocess

from sophos_caa.core.state import ProcessState


class SystemdController:
    unit = "sophos-caa.service"

    def _run(self, *arguments: str, timeout: float = 15) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["systemctl", "--user", *arguments, self.unit],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def start(self) -> None:
        self._require_success(self._run("start"))

    def stop(self) -> None:
        self._require_success(self._run("stop"))

    def restart(self) -> None:
        self._require_success(self._run("restart"))

    def state(self) -> ProcessState:
        result = self._run("show", "--property=ActiveState", "--value", timeout=5)
        value = result.stdout.strip()
        if value == "active":
            return ProcessState.RUNNING
        if value in {"activating", "reloading"}:
            return ProcessState.STARTING
        if value in {"inactive", "deactivating"}:
            return ProcessState.STOPPED
        if value == "failed":
            return ProcessState.FAILED
        return ProcessState.UNKNOWN

    @staticmethod
    def _require_success(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode:
            message = result.stderr.strip() or result.stdout.strip() or "systemctl command failed"
            raise RuntimeError(message)

    @classmethod
    def logs(cls, lines: int = 100) -> int:
        process = subprocess.run(
            ["journalctl", "--user", "-u", cls.unit, "-n", str(lines), "--no-pager"],
            check=False,
        )
        return process.returncode


class IndicatorController(SystemdController):
    unit = "sophos-caa-indicator.service"
