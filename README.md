

# Sophos CAA Manager for Linux (PES RR)

Stop repeating captive-portal logins. Keep the official Sophos Client
Authentication Agent running reliably in the background on Linux.

Built for students at **PES University, Ring Road (RR) Campus**.

[Python 3.11+](https://www.python.org/)
[Linux](https://kernel.org/)
[NetworkManager](https://networkmanager.dev/)
[systemd](https://systemd.io/)
[License: MIT](LICENSE)

[Get started](docs/getting-started.md) · [Features](#key-features) ·
[Architecture](docs/architecture.md) · [Troubleshooting](docs/troubleshooting.md)



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

CAA must already be installed, configured, and working when run manually.

```bash
git clone https://github.com/Adnan-Safdari/pes-sophos-caa-manager.git
cd pes-sophos-caa-manager
python3 bootstrap.py
```

If CAA is already running, installation leaves it untouched. Transfer control
to the manager when a brief CAA restart is acceptable:

```bash
python3 bootstrap.py --handover
```

See the complete distro prerequisites, installation, verification, usage,
configuration, upgrade, and removal steps in
`[docs/getting-started.md](docs/getting-started.md)`.

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
and Arch Linux. See `[packaging/README.md](packaging/README.md)`.

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

See `[SECURITY.md](SECURITY.md)` for reporting and operational guidance.

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