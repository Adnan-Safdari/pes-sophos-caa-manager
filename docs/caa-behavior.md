# Verified Sophos CAA 1.2.0 behavior

Initial inspection date: 2026-09-16

This document records the observations used by the process wrapper and output
parser. No CAA credentials or configuration values were read or logged.

## Reference test environment

- Distribution: Ubuntu 24.04.4 LTS (Noble), x86-64
- Kernel: Linux 7.0.0-30-generic
- Desktop: Ubuntu GNOME on Wayland
- Init: systemd 255 is PID 1
- User manager: `systemd --user` is running
- NetworkManager: 1.46.0, active
- NetworkManager D-Bus service: available on the system bus
- NetworkManager connectivity checking uses Ubuntu's connectivity-check URL

The target architecture may use these facilities, but the Python core must not
depend on Ubuntu- or GNOME-specific paths or behavior.

## CAA installation

- Command discovery:
  - `which caa`: `/usr/local/bin/caa`
  - `type -a caa`: only `/usr/local/bin/caa`
- Version: `caa version 1.2.0`
- Binary: stripped, statically linked, x86-64 ELF executable
The executable path must be discovered at installation/runtime and must not be
hard-coded to `/usr/local/bin/caa`.

## Documented command-line interface

Both `caa --help` and `caa -h` exited with status 0, wrote the following
interface to stdout, and wrote nothing to stderr:

```text
Usage: caa [OPTIONS]

 -d, --daemon    start in daemon mode
 -s, --stop      stop running daemon
 -v, --verbose   output debug information
 -l, --log=FILE  log into FILE
 -h, --help      display this help
 -V, --version   print program version
```

Both `caa -V` and `caa --version` exited with status 0, wrote
`caa version 1.2.0` to stdout, and wrote nothing to stderr.

There is no documented status command. The stop option is specifically
described as stopping a daemon. A later controlled lifecycle test verified
foreground shutdown and daemon startup behavior below.

## Configuration

The bundled README and command help both specify:

```text
$HOME/.caa/caa.conf
```

The documented fields are Copernicus host, username, and password. CAA replaces
the initial plaintext password with an encrypted representation after first
start. The configuration contents were not inspected.

Observed host permissions:

```text
~/.caa/          0755
~/.caa/caa.conf  0664
~/.caa/caa.pid   0664
```

All are owned by the normal login user. CAA is currently able to run as that
user. The configuration mode is too permissive for a credential-bearing file:
the manager/installer should warn and recommend `0600` without reading or
rewriting the file.

The current CAA process also maintains `$HOME/.caa/caa.pid`.

## Observed process behavior

CAA was already running, so a bounded second invocation was used to avoid
interrupting authentication:

```text
$ caa
caa already running with Process Id <pid>.
```

The second invocation exited with status 1, wrote that message to stdout, wrote
nothing to stderr, and did not leave another process running.

At the final snapshot, CAA was:

- running in the foreground as the normal login user
- attached to a terminal on stdin, stdout, and stderr
- launched as `caa` with no options
- represented by its PID in `$HOME/.caa/caa.pid`
- holding an established TCP connection to `192.168.254.1:9922`

No CAA entries were present in the user or system journal because this process
was launched from a terminal. Existing terminal scrollback was not read or
consumed. Consequently, authentication success, failure, disconnect, and
reconnect output strings are not yet verified.

## NetworkManager and routing observations

NetworkManager reported `connected` with `FULL` connectivity in both observed
snapshots. Its D-Bus values were:

```text
State = 70          # NM_STATE_CONNECTED_GLOBAL
Connectivity = 4   # NM_CONNECTIVITY_FULL
```

Two anonymized PES network snapshots were observed:

- Network A used one client subnet and default gateway, with CAA connected to
  `192.168.254.1:9922`.
- Network B used a different client subnet and default gateway, with CAA still
  connected to `192.168.254.1:9922`.

For the second snapshot, the kernel route was:

```text
192.168.254.1 via <active-default-gateway> dev <wireless-interface>
```

The interface name is deliberately not treated as configuration.

### Important correction to the proposed detector

On the inspected PES networks, `192.168.254.1` is the remote
CAA/Copernicus server endpoint, not the active connection's default gateway.
The default gateway changed between two Wi-Fi networks while the CAA peer
remained `192.168.254.1:9922`.

Therefore this initial rule is invalid in the verified reference environment:

```text
default gateway == 192.168.254.1
```

Using it would classify both observed networks as non-CAA networks and stop a
working CAA session. Network detection needs additional verified evidence
before implementation.

Direct HTTP and HTTPS HEAD requests to `192.168.254.1` ports 80 and 443 timed
out. The PES captive portal instead listens on port 8090. While CAA was
authenticated and NetworkManager reported `FULL` connectivity:

```text
TCP 192.168.254.1:8090   reachable
HTTP HEAD /              200 OK, text/html
HTTPS HEAD /             404 File not found
```

An HTTP response from `192.168.254.1:8090` is therefore useful evidence that
the active network is PES, but not evidence that CAA authentication is
currently required. CAA's own TCP connection uses port 9922; this observation
does not imply that the manager should implement or inspect the proprietary
protocol.

## Verified and unverified behavior

Verified:

- CAA 1.2.0 has foreground and daemon modes.
- It has a daemon stop command and verbose/file-log options.
- It has no documented status command.
- It uses `$HOME/.caa` and a PID file.
- It runs as the normal user in the current setup.
- A duplicate foreground start exits 1 without replacing the running process.
- The live process communicates with `192.168.254.1:9922`.
- Process-running state alone does not provide an authentication status.
- `caa --stop` sends SIGTERM to the PID and exits 0; the foreground process
  handles SIGTERM, exits 0, and removes its PID file.
- `caa --daemon --verbose` exits 0 without terminal output, leaves a child CAA
  process running, and writes its PID file.
- Foreground `--verbose` output for a successful login is:

```text
caa started in foreground mode.
Connecting to host 192.168.254.1 ...
Connected with ECDHE-RSA-AES256-GCM-SHA384 encryption.
Client type sent: Linux
OK Notification received.
Login was accepted.
PONG sent!
7 IPv4 addresses sent!
3 IPv6 addresses sent!
8 MAC addresses sent!
OK Notification received.
OK Notification received.
OK Notification received.
Running instance of caa terminated by signal 15
```

`Login was accepted.` is the observed authentication-success message.

Still unverified:

- exact authentication failure messages
- connection-loss and reconnection messages
- exit codes for startup/configuration/network/authentication failures
- automatic reconnection after route, address, or Wi-Fi changes
- whether CAA binds explicitly to an interface or merely follows kernel routes
- whether a graphical session or session-specific environment is required
- whether any environment variables beyond `HOME` affect operation

Failure and reconnect observations require a real failure or network transition
while verbose output is being captured. The successful lifecycle test preserved
the existing configuration and never printed it.
