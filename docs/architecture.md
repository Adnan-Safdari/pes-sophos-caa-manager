# Architecture

The application has three user-level processes with narrow responsibilities:

```text
NetworkManager D-Bus
        |
        v
sophos-caa-manager.service <--- session D-Bus ---> CLI
        |                                              |
        | systemctl --user                             v
        v                                  sophos-caa-indicator.service
sophos-caa.service
        |
        v
official caa executable
```

The manager survives indicator closure. Hiding the indicator exits its service
cleanly; the application launcher or `sophos-caa show-indicator` starts it
again without changing CAA state.

## Components

- `core/state.py`: frontend-independent state values and network snapshot
- `core/controller.py`: pure automatic-mode decisions
- `core/detector.py`: bounded PES portal detector
- `network/network_manager.py`: NetworkManager signal subscription and snapshot
- `service/systemd.py`: safe `systemctl --user` adapter
- `manager.py`: debounce, override, retry, and orchestration
- `caa/journal.py`: event-driven authentication parsing from CAA journal output
- `api.py`: session D-Bus methods and state-change signal
- `cli.py` and `ui/tray.py`: replaceable frontends

## State and overrides

Process state and authentication state are separate. Authentication becomes
`authenticated` only after the observed CAA message `Login was accepted.` is
seen in the journal. A manual start or stop remains in force until the active
connection UUID or local IPv4 changes. Disabling automatic mode leaves all
lifecycle choices to the user.

In automatic mode:

```text
PES portal unreachable -> CAA stopped
PES portal reachable + CAA stopped -> CAA started
PES portal reachable + network fingerprint changed -> CAA restarted
PES portal reachable + unchanged network -> no action
```

The systemd CAA unit uses `sophos-caa-run` to discover the configured CAA
binary and supervise foreground `caa --verbose` behind a pseudo-terminal. The
pseudo-terminal is necessary because the static CAA 1.2.0 binary otherwise
buffers output sent directly to the journal. The launcher forwards termination
signals and streams status lines immediately; systemd restarts unexpected
failures. Intentional `systemctl stop` does not trigger `Restart=on-failure`.

## Local API

The manager owns `org.sophos.CAA` on the user's session bus at
`/org/sophos/CAA`. It exposes lifecycle methods, status queries, automatic-mode
control, and a `StateChanged` signal. It opens no network server.

