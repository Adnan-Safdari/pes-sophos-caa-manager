# Contributing

Contributions are welcome, especially testing across distributions, desktop
environments, NetworkManager versions, and legitimate CAA releases.

## Before opening a change

- Do not include CAA binaries, credentials, configuration values, packet
  captures, or proprietary protocol details.
- Keep the Python core independent of a specific desktop environment.
- Prefer NetworkManager D-Bus events over polling.
- Add parser rules only for exact CAA output that has been safely observed and
  documented.
- Keep all services user-level unless a reviewed requirement proves otherwise.

## Development setup

Follow [`docs/development.md`](docs/development.md), then run:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src bootstrap.py
```

Changes to desktop files, icons, systemd units, or packaging should also run
the validators listed in the development guide.

## Reporting bugs

Include:

- distribution and version
- desktop environment and session type
- Python, NetworkManager, systemd, and CAA versions
- the command or action that failed
- sanitized manager and CAA journal output

Never post `~/.caa/caa.conf`. Remove usernames, passwords, tokens, internal
hostnames, and identifying network information from logs.

## Scope

This project controls an existing official CAA process. Contributions must not
reverse engineer or replace the Sophos authentication protocol, bypass
authentication, or extract credentials.

