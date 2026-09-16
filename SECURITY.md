# Security policy

## Supported versions

The latest released version receives security fixes. This project is currently
pre-1.0, so users should review release notes before upgrading.

## Reporting a vulnerability

Do not open a public issue containing credentials, tokens, private CAA
configuration, or identifying network data. Contact the repository maintainer
privately using the security-reporting mechanism provided by the hosting
platform.

Include a minimal description, affected version, impact, and safe reproduction
steps. Do not attach `~/.caa/caa.conf` or the proprietary CAA binary.

## Security boundaries

The manager:

- runs as the logged-in user
- uses systemd user services
- opens no listening network socket
- does not store or transmit Sophos credentials
- does not read or display CAA configuration values
- uses argument arrays instead of `shell=True`
- writes manager configuration atomically with mode `0600`
- communicates locally over the user's session D-Bus

The official CAA client remains responsible for authentication, credential
storage, encryption, and communication with the Sophos service.

## Operational guidance

CAA's configuration contains credentials. Restrict it to the owning user when
compatible with the installed client:

```bash
chmod 600 ~/.caa/caa.conf
```

Review commands before sharing journal output:

```bash
journalctl --user -u sophos-caa-manager
journalctl --user -u sophos-caa
```

Remove usernames, tokens, private hostnames, and identifying network details.

