"""Run CAA behind a pseudo-terminal so status output is flushed immediately."""

from __future__ import annotations

import os
import pty
import select
import signal
import subprocess
import sys
from pathlib import Path
from types import FrameType

from sophos_caa.caa.process import discover_caa
from sophos_caa.config.config import Config


def run_supervised(command: Path, arguments: list[str]) -> int:
    master, slave = pty.openpty()
    process = subprocess.Popen(
        [str(command), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)

    def forward(signum: int, _frame: FrameType | None) -> None:
        if process.poll() is None:
            process.send_signal(signum)

    previous_term = signal.signal(signal.SIGTERM, forward)
    previous_int = signal.signal(signal.SIGINT, forward)
    try:
        while True:
            readable, _, _ = select.select([master], [], [], 0.25)
            if readable:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    data = b""
                if data:
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
            if process.poll() is not None:
                return process.wait()
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)
        os.close(master)
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def main() -> int:
    config = Config.load()
    command = discover_caa(config.caa_command)
    return run_supervised(command, sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
