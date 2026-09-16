from __future__ import annotations

import stat
from pathlib import Path

import pytest

from sophos_caa.config.config import Config


def test_save_and_load_round_trip_with_restrictive_permissions(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "config.toml"
    config = Config(
        automatic=False,
        debounce_seconds=1.5,
        portal_host="portal.example.test",
        portal_port=18090,
        probe_timeout_seconds=0.75,
        caa_command='/opt/Sophos CAA/bin/caa "managed"',
        retry_seconds=(1, 7, 60),
    )

    config.save(path)

    assert Config.load(path) == config
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_save_replaces_an_insecure_existing_file_mode(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[automation]\nenabled = true\n", encoding="utf-8")
    path.chmod(0o644)

    Config().save(path)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    assert Config.load(tmp_path / "missing.toml") == Config()


@pytest.mark.parametrize(
    "changes",
    [
        {"debounce_seconds": 0.49},
        {"debounce_seconds": 30.01},
        {"portal_port": 0},
        {"portal_port": 65536},
        {"probe_timeout_seconds": 0.19},
        {"probe_timeout_seconds": 10.01},
        {"portal_host": ""},
        {"portal_host": "has whitespace"},
        {"retry_seconds": ()},
        {"retry_seconds": (0,)},
        {"retry_seconds": (3601,)},
    ],
)
def test_validation_rejects_out_of_range_values(changes: dict[str, object]) -> None:
    config = Config()
    for name, value in changes.items():
        setattr(config, name, value)

    with pytest.raises(ValueError):
        config.validate()


def test_load_validates_file_values(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[network]\nportal_port = 70000\n", encoding="utf-8")

    with pytest.raises(ValueError, match="portal_port"):
        Config.load(path)
