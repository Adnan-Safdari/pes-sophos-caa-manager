# Troubleshooting

## The CLI cannot find the manager

Check the user service and session journal:

```bash
systemctl --user status sophos-caa-manager
journalctl --user -u sophos-caa-manager -n 100
```

The CLI must run in the same logged-in user's D-Bus session.

## CAA does not start

```bash
systemctl --user status sophos-caa
journalctl --user -u sophos-caa -n 100
which caa
```

If the journal says CAA is already running, a manually launched CAA still owns
`~/.caa/caa.pid`. Run the installer with `--handover` when a brief restart is
acceptable.

## The CAA network is not detected

Check the configured portal without displaying its body. For the default PES
configuration:

```bash
curl -I --max-time 3 http://192.168.254.1:8090/
```

Also check NetworkManager:

```bash
nmcli networking connectivity
nmcli connection show --active
```

## Indicator is absent

The manager and CLI do not depend on the indicator. Install the distribution's
GTK 3 AppIndicator introspection package. Non-Ubuntu GNOME may additionally
need the AppIndicator/KStatusNotifierItem shell extension. KDE Plasma supports
status notifier items directly.

Check or restore the indicator service:

```bash
systemctl --user status sophos-caa-indicator
sophos-caa show-indicator
```

“Hide indicator” intentionally stops only this UI service. The manager and CAA
continue running.

## Configuration error

The manager validates values in:

```text
~/.config/sophos-caa-manager/config.toml
```

Move an invalid file aside to return to defaults. Never copy CAA credentials
into this manager configuration.

