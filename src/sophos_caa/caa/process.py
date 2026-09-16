"""CAA executable discovery and validation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def discover_caa(configured: str = "") -> Path:
    candidate = configured or shutil.which("caa")
    if not candidate:
        raise FileNotFoundError("Sophos CAA was not found in PATH")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise FileNotFoundError(f"CAA is not executable: {path}")
    return path


def caa_version(command: Path) -> str:
    result = subprocess.run(
        [str(command), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "CAA version check failed"
        raise RuntimeError(message)
    return result.stdout.strip()
