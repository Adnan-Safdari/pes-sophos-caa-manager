#!/usr/bin/env python3
"""Install into a private user venv while retaining system PyGObject."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    project = Path(__file__).resolve().parent
    venv = Path.home() / ".local" / "share" / "sophos-caa-manager" / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
        check=True,
    )
    python = venv / "bin" / "python"
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", str(project)], check=True)
    result = subprocess.run([str(venv / "bin" / "sophos-caa-install"), *sys.argv[1:]])
    if result.returncode == 0 and "--uninstall" in sys.argv[1:]:
        shutil.rmtree(venv)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
