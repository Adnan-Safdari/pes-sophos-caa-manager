# Network detection

## Verified PES signal

On two observed PES Wi-Fi networks, the default gateways differed while CAA
connected to `192.168.254.1:9922`. Therefore gateway equality is not used.

The captive portal endpoint `http://192.168.254.1:8090/` returned HTTP 200 while
CAA was authenticated and NetworkManager reported full connectivity. The manager
uses any valid HTTP response from this endpoint as evidence that the current
network is PES.

This probe identifies the network; it does not decide whether authentication
is needed and does not inspect portal content.

## Event flow

The manager subscribes to NetworkManager properties and state signals. Each
burst of events replaces one GLib timeout. After the default four-second
debounce, the manager:

1. probes the portal with a two-second bound
2. reads the primary active connection through NetworkManager D-Bus
3. records connection ID, UUID, local IPv4, gateway, and connectivity
4. compares `connection UUID + local IPv4` with the previous fingerprint
5. applies one idempotent CAA action

There is no continuous polling.

## Connectivity

NetworkManager connectivity values are normalized as unknown, none, portal,
limited, or full. They are status information only. Stopping CAA merely because
connectivity became full would create an authentication loop.

## Known limitation

A private network that routes to an unrelated service at exactly
`192.168.254.1:8090` could be a false positive. A later detector can add a
verified, non-sensitive response signature without changing controller policy.

