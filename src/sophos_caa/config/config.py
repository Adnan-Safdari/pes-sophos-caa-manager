"""Validated user configuration with restrictive file permissions."""

from __future__ import annotations

import os
import tempfile
import tomllib
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "sophos-caa-manager" / "config.toml"


@dataclass(slots=True)
class Config:
    schema_version: int = 1
    automatic: bool = True
    debounce_seconds: float = 4.0
    portal_host: str = "192.168.254.1"
    portal_port: int = 8090
    probe_timeout_seconds: float = 2.0
    caa_command: str = ""
    retry_seconds: tuple[int, ...] = field(default_factory=lambda: (5, 10, 30, 60, 120))

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> Config:
        if not path.exists():
            return cls()
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
        automation = raw.get("automation", {})
        manager = raw.get("manager", {})
        network = raw.get("network", {})
        caa = raw.get("caa", {})
        retry = raw.get("retry", {})
        config = cls(
            schema_version=int(manager.get("schema_version", 1)),
            automatic=bool(automation.get("enabled", True)),
            debounce_seconds=float(automation.get("debounce_seconds", 4)),
            portal_host=str(network.get("portal_host", "192.168.254.1")),
            portal_port=int(network.get("portal_port", 8090)),
            probe_timeout_seconds=float(network.get("probe_timeout_seconds", 2)),
            caa_command=str(caa.get("command", "")),
            retry_seconds=tuple(int(value) for value in retry.get("seconds", [5, 10, 30, 60, 120])),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"unsupported configuration schema {self.schema_version}")
        if not 0.5 <= self.debounce_seconds <= 30:
            raise ValueError("debounce_seconds must be between 0.5 and 30")
        if not 1 <= self.portal_port <= 65535:
            raise ValueError("portal_port must be between 1 and 65535")
        if not 0.2 <= self.probe_timeout_seconds <= 10:
            raise ValueError("probe_timeout_seconds must be between 0.2 and 10")
        if not self.portal_host or any(char.isspace() for char in self.portal_host):
            raise ValueError("portal_host is invalid")
        if not self.retry_seconds or any(value < 1 or value > 3600 for value in self.retry_seconds):
            raise ValueError("retry seconds must be between 1 and 3600")

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        content = (
            "[manager]\n"
            f"schema_version = {self.schema_version}\n\n"
            "[automation]\n"
            f"enabled = {str(self.automatic).lower()}\n"
            f"debounce_seconds = {self.debounce_seconds:g}\n\n"
            "[network]\n"
            f'portal_host = "{self.portal_host}"\n'
            f"portal_port = {self.portal_port}\n"
            f"probe_timeout_seconds = {self.probe_timeout_seconds:g}\n\n"
            "[retry]\n"
            f"seconds = [{', '.join(str(value) for value in self.retry_seconds)}]\n"
        )
        if self.caa_command:
            escaped = self.caa_command.replace("\\", "\\\\").replace('"', '\\"')
            content += f'\n[caa]\ncommand = "{escaped}"\n'

        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".config.", text=True)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            with suppress(FileNotFoundError):
                os.unlink(temporary)
