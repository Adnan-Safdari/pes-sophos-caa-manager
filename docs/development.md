# Development

## Environment

PyGObject is normally supplied by the distribution because it links to system
GObject libraries. Create a development environment that can see system
packages:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e '.[dev]'
```

## Checks

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src
desktop-file-validate desktop/org.sophos.CAA.desktop
xmllint --noout assets/icons/hicolor/scalable/apps/*.svg
xmllint --noout assets/icons/hicolor/symbolic/apps/*.svg
```

Tests mock NetworkManager, systemd, CAA, and portal responses. They do not
require a Sophos Firewall.

## Manual testing

Do not run a source manager alongside an installed manager. Before a handover,
confirm `caa` is available and the portal is reachable. Use:

```bash
systemctl --user status sophos-caa-manager
systemctl --user status sophos-caa
sophos-caa status
```

Switching networks should produce one evaluation after the debounce period.
Changing local IPv4 on PES should restart CAA once. Closing the indicator must
not stop either service.

The indicator should exit cleanly when hidden, remain inactive because its
service uses `Restart=on-failure`, and return from the application launcher:

```bash
sophos-caa hide-indicator
sophos-caa show-indicator
```

## CAA output

Only output observed from CAA 1.2.0 is normalized by the parser. Add parser
states only after capturing and documenting the exact message in
`caa-behavior.md`.

