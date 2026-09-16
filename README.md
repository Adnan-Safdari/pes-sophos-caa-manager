<p align="center">
  <img src="assets/icons/hicolor/scalable/apps/org.sophos.CAA.svg" width="120" alt="Sophos CAA Manager application icon">
</p>

<h1 align="center">Sophos CAA Manager for Linux (PES RR)</h1>

<p align="center">
  Stop repeating captive-portal logins.<br>
  Keep the official Sophos Client Authentication Agent running reliably in the background on Linux.
</p>

<p align="center">
  <a href="https://www.python.org/"><img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&amp;logoColor=white"></a>
  <a href="https://kernel.org/"><img alt="Platform: Linux" src="https://img.shields.io/badge/Platform-Linux-FCC624?logo=linux&amp;logoColor=black"></a>
  <a href="https://networkmanager.dev/"><img alt="NetworkManager" src="https://img.shields.io/badge/Network-NetworkManager-6A42C2"></a>
  <a href="https://systemd.io/"><img alt="systemd user service" src="https://img.shields.io/badge/Service-systemd-5C2D91?logo=systemd&amp;logoColor=white"></a>
  <a href="https://www.gtk.org/"><img alt="GTK 3" src="https://img.shields.io/badge/Desktop-GTK%203-4A86CF?logo=gtk&amp;logoColor=white"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
</p>

<p align="center">
  Built for students at <strong>PES University, Ring Road (RR) Campus</strong>.
</p>

<p align="center">
  <a href="docs/getting-started.md">Get started</a> ·
  <a href="#demo">Demo</a> ·
  <a href="#key-features">Features</a> ·
  <a href="docs/architecture.md">Architecture</a> ·
  <a href="docs/troubleshooting.md">Troubleshooting</a>
</p>

> [!IMPORTANT]
> **PES IT policy disclaimer:** This project does not bypass or alter any PES
> network control. It adds a local management layer on top of the official
> Sophos Client Authentication Agent recommended for network authentication.
> It does not automate credential entry, evade session limits, or modify CAA.
> This project is unofficial and fully compliant with the PES University IT Policy.

---

## The problem

Students at PES University RR Campus may have to enter their captive-portal
username and password several times each day—after reconnecting, moving between
access points, receiving a new IP, or switching devices. Old browser sessions
can remain active, and a new login may then be rejected when the firewall's
configured simultaneous-login limit is reached.

This behavior follows the two authentication models documented by Sophos:

- A [browser captive portal](https://docs.sophos.com/nsg/sophos-firewall/21.0/Help/en-us/webhelp/onlinehelp/AdministratorHelp/CurrentActivities/LiveUsers/)
prompts the user for credentials.
- CAA signs the user in automatically by sending authentication messages to
Sophos Firewall.
- Sophos Firewall can enforce a configurable
[simultaneous-login limit](https://docs.sophos.com/nsg/sophos-firewall/21.5/api/CONFIGURE/Authentication/FirewallAuthenticationMethods/operations/configureglobal.html).

CAA solves the repeated browser-login problem, but the basic Linux instruction
to run `caa` starts it in foreground mode. Users following that workflow must
keep a terminal open. Although CAA also exposes a daemon option, it does not
provide network-aware desktop controls. With the tested Linux CAA 1.2.0, a
Wi-Fi, route, or local-IP change can leave the old process unable to
authenticate the new network path reliably, requiring the user to stop and
start it again.

## The solution

Sophos CAA Manager keeps the official Linux client running as a background
user service and restarts it when the network identity changes. Students get
the benefits of CAA without keeping a terminal open or manually restarting the
process throughout the day.

It solves this without replacing or modifying CAA:

```text
NetworkManager events
        |
        v
Sophos CAA Manager
        |
        v
systemd --user  --->  official caa executable
        ^
        |
CLI and desktop indicator
```

The manager identifies configured CAA networks, runs the official client as a
user service, and restarts it when the active connection or local IPv4 address
changes.

## Demo

https://github.com/user-attachments/assets/758bad38-89b6-45f7-a545-0e5a08aee838

[Download the MP4](docs/media/sophos-caa-manager-demo.mp4)

## Key features

- Runs CAA without an open terminal
- Uses `systemd --user`; no root daemon or privileged helper
- Reacts to NetworkManager D-Bus signals instead of continuously polling
- Debounces noisy Wi-Fi, DHCP, route, and connectivity transitions
- Restarts CAA when the connection UUID or local IPv4 changes
- Keeps process state separate from verified authentication state
- Provides a GNOME/KDE-compatible AppIndicator menu
- Lets users hide and restore the indicator without stopping CAA
- Includes a first-class CLI, automatic mode, and manual overrides
- Captures CAA and manager logs in the user journal
- Stores no Sophos password, token, or copied credentials

## Quick start

### 1. Confirm that Sophos CAA works

This manager does not redistribute or replace the proprietary CAA client. CAA
must already be installed, configured, and able to authenticate when run
manually:

```bash
command -v caa
caa --version
```

If it is not installed, follow
[Installing Sophos CAA on Linux](docs/installing-sophos-caa.md) first.

### 2. Install system dependencies

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install git python3 python3-venv python3-gi gir1.2-gtk-3.0 \
  gir1.2-ayatanaappindicator3-0.1 network-manager
```

Fedora:

```bash
sudo dnf install git python3 python3-gobject gtk3 NetworkManager systemd \
  libayatana-appindicator-gtk3
```

Arch Linux:

```bash
sudo pacman -S git python python-gobject gtk3 networkmanager systemd \
  libayatana-appindicator
```

### 3. Install the manager

```bash
git clone https://github.com/Adnan-Safdari/pes-sophos-caa-manager.git
cd pes-sophos-caa-manager
python3 bootstrap.py
```

The installer creates a private environment under
`~/.local/share/sophos-caa-manager/`, installs user-level systemd services, and
adds the desktop indicator. It does not require root.

### 4. Transfer an existing CAA session

If CAA is already running, the first installation leaves it untouched. When a
brief authentication restart is acceptable, transfer control to the manager:

```bash
python3 bootstrap.py --handover
```

Do not continue running `caa` manually after this handover.

### 5. Add the CLI to `PATH`

For the current Bash session:

```bash
export PATH="$HOME/.local/share/sophos-caa-manager/venv/bin:$PATH"
```

Make it permanent:

```bash
grep -qxF 'export PATH="$HOME/.local/share/sophos-caa-manager/venv/bin:$PATH"' \
  ~/.bashrc || \
  echo 'export PATH="$HOME/.local/share/sophos-caa-manager/venv/bin:$PATH"' \
  >> ~/.bashrc
source ~/.bashrc
```

For another shell, add the same directory using that shell's startup file.

### 6. Verify the installation

```bash
sophos-caa status
systemctl --user status sophos-caa-manager
systemctl --user status sophos-caa
```

The indicator starts automatically when its GTK/AppIndicator dependencies are
available. If it was hidden, restore it with:

```bash
sophos-caa show-indicator
```

For upgrades, configuration, troubleshooting, and removal, see the complete
[Getting started guide](docs/getting-started.md).

## Desktop controls

The indicator provides:

- current process, authentication, network, IP, and portal status
- Re-authenticate
- Start CAA
- Stop CAA
- Automatic mode
- View logs
- About
- Hide indicator

Hiding the indicator closes only the panel UI. The manager and CAA continue
running. Open **Sophos CAA Manager** from the application grid to restore it.

## CLI

```text
sophos-caa status
sophos-caa start
sophos-caa stop
sophos-caa restart
sophos-caa reauth
sophos-caa enable-auto
sophos-caa disable-auto
sophos-caa network
sophos-caa logs
sophos-caa show-indicator
sophos-caa hide-indicator
sophos-caa restart-indicator
sophos-caa help
```

## Supported environments

The portable core targets Linux systems with:

- Python 3.11 or newer
- systemd user sessions
- NetworkManager
- Sophos CAA

The indicator uses GTK 3 with Ayatana AppIndicator or AppIndicator. Ubuntu
GNOME and KDE Plasma are the primary desktop targets. Other GNOME
installations may require an AppIndicator/KStatusNotifierItem extension.
Waybar and other frontends can use the same CLI and session D-Bus API.

Distribution packaging templates are provided for Debian/Ubuntu, Fedora/RPM,
and Arch Linux. See [Distribution packaging](packaging/README.md).

## Documentation

- [Getting started](docs/getting-started.md)
- [Installing Sophos CAA](docs/installing-sophos-caa.md)
- [Architecture](docs/architecture.md)
- [Network detection](docs/network-detection.md)
- [Verified CAA behavior](docs/caa-behavior.md)
- [Development](docs/development.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Security model

The manager runs as the logged-in user and controls only a user service. It
does not read or display `~/.caa/caa.conf`, transmit credentials, implement the
Sophos protocol, expose a network socket, or use `shell=True`.

See the [Security policy](SECURITY.md) for reporting and operational guidance.

## Project status

Version `0.1.0` is an early release tested with CAA 1.2.0 on Ubuntu 24.04,
GNOME/Wayland, systemd 255, and NetworkManager 1.46. Additional distro and
desktop testing is welcome.

## Trademark notice

This is an independent, unofficial open-source project. It is not affiliated
with, endorsed by, or supported by Sophos. Sophos is a trademark of its
respective owner. The project contains original artwork and does not
redistribute Sophos branding or the proprietary CAA binary.

## License

Licensed under the [MIT License](LICENSE).