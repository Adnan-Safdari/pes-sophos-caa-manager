# Getting started

This guide covers prerequisites, source installation, first handover, everyday
use, upgrades, and removal.

## 1. Confirm that CAA works

Sophos CAA Manager does not install or configure the proprietary CAA client.
Before installing the manager, verify:

```bash
command -v caa
caa --version
```

CAA should already authenticate successfully when started manually. Never put
Sophos credentials in this project or its issue tracker.

If CAA is not installed yet, follow
[Installing Sophos CAA on Linux](installing-sophos-caa.md) first.

## 2. Install system dependencies

Required on every supported system:

- Python 3.11 or newer with `venv`
- systemd user sessions
- NetworkManager
- PyGObject with Gio
- GTK 3 and AppIndicator support for the optional desktop indicator

### Ubuntu and Debian

```bash
sudo apt update
sudo apt install python3 python3-venv python3-gi gir1.2-gtk-3.0 network-manager
sudo apt install gir1.2-ayatanaappindicator3-0.1
```

If the final package is unavailable, install `gir1.2-appindicator3-0.1`
instead.

### Fedora

```bash
sudo dnf install python3 python3-gobject gtk3 NetworkManager systemd \
  libayatana-appindicator-gtk3
```

AppIndicator package names can differ between Fedora releases.

### Arch Linux and derivatives

```bash
sudo pacman -S python python-gobject gtk3 networkmanager systemd \
  libayatana-appindicator
```

Installing dependencies may require administrator access. The manager itself
and all normal CAA operations run as the logged-in user without sudo.

## 3. Install the manager

Clone this repository and run the bootstrap installer:

```bash
git clone https://github.com/Adnan-Safdari/pes-sophos-caa-manager.git
cd pes-sophos-caa-manager
python3 bootstrap.py
```

Alternatively, download and extract a release archive, then run
`python3 bootstrap.py` from the extracted directory.

The bootstrap:

1. creates a private environment in
   `~/.local/share/sophos-caa-manager/venv`
2. discovers and validates the installed `caa` executable
3. writes a mode-`0600` manager configuration
4. installs three systemd user units
5. installs the desktop launcher and original project icons
6. enables the manager and indicator for future logins

If a manual CAA process is already running, the installer preserves it and
does not transfer control automatically.

## 4. Transfer the running CAA session

When a brief authentication restart is acceptable:

```bash
python3 bootstrap.py --handover
```

The handover stops the manually started CAA process, starts the manager, and
lets the current network decision start CAA under `systemd --user`.

Do not run `caa` manually after the handover. Use the indicator or CLI.

## 5. Add the CLI to PATH

The commands are installed in the private environment:

```text
~/.local/share/sophos-caa-manager/venv/bin
```

For the current shell:

```bash
export PATH="$HOME/.local/share/sophos-caa-manager/venv/bin:$PATH"
```

To keep this setting, add that line to your shell profile.

## 6. Verify the installation

```bash
systemctl --user status sophos-caa-manager
systemctl --user status sophos-caa
systemctl --user status sophos-caa-indicator
sophos-caa status
```

On a detected CAA network, status should report:

- the active network and local IPv4
- the configured portal as reachable
- the CAA process as running
- authentication as connecting, connected, authenticated, or unknown

Authentication is reported only after an exact message verified from CAA
output. `Unknown` is safer than incorrectly claiming authentication.

## 7. Use the indicator

The indicator starts automatically at login. Its menu can start, stop, or
re-authenticate CAA, toggle automatic mode, display logs, and show current
network state.

Choosing **Hide indicator** closes only the panel UI. The manager and CAA keep
running. Restore it by opening **Sophos CAA Manager** from the application grid
or run:

```bash
sophos-caa show-indicator
```

Other indicator controls:

```bash
sophos-caa hide-indicator
sophos-caa restart-indicator
```

## 8. Use the CLI

List commands and their descriptions:

```bash
sophos-caa help
# Equivalent:
sophos-caa --help
```

Status and network information:

```bash
sophos-caa status
sophos-caa network
```

Manual lifecycle controls:

```bash
sophos-caa start
sophos-caa stop
sophos-caa restart
sophos-caa reauth
```

Automatic mode:

```bash
sophos-caa enable-auto
sophos-caa disable-auto
```

Logs:

```bash
sophos-caa logs
sophos-caa logs --lines 250
journalctl --user -u sophos-caa-manager
journalctl --user -u sophos-caa
```

## 9. Configure network detection

The configuration is:

```text
~/.config/sophos-caa-manager/config.toml
```

Default values:

```toml
[manager]
schema_version = 1

[automation]
enabled = true
debounce_seconds = 4

[network]
portal_host = "192.168.254.1"
portal_port = 8090
probe_timeout_seconds = 2

[ui]
show_ip_address = false

[retry]
seconds = [5, 10, 30, 60, 120]
```

The desktop indicator hides the local IP address by default. Set
`show_ip_address = true` to display it again.

Restart the relevant component after editing:

```bash
# Network or automation settings:
systemctl --user restart sophos-caa-manager

# UI settings:
sophos-caa restart-indicator
```

CAA credentials remain exclusively in the official CAA configuration under
`~/.caa`. Do not copy them into the manager configuration.

## 10. Upgrade

Pull or unpack the newer source, then rerun:

```bash
python3 bootstrap.py
```

The installer replaces its files atomically and preserves configuration. An
active CAA process is not interrupted during a normal upgrade.

## 11. Uninstall

```bash
python3 bootstrap.py --uninstall
```

Uninstall explicitly stops the indicator, manager, and managed CAA service. It
removes user units, the launcher, icons, and private environment while
preserving:

- the official CAA executable
- `~/.caa`
- `~/.config/sophos-caa-manager/config.toml`

## Next steps

- [Troubleshooting](troubleshooting.md)
- [Architecture](architecture.md)
- [Network detection](network-detection.md)
- [Development](development.md)

