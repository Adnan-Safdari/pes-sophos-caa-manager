# Installing Sophos CAA on Linux

PES University RR Campus guide for installing and configuring the official
Sophos Client Authentication Agent (CAA).

> This guide covers the proprietary CAA client supplied through the PES
> University portal. This repository does not redistribute CAA. Download and
> use it only if you are authorized to access the PES network.

## What CAA does

CAA authenticates a Linux system to the PES network without requiring a
day-to-day browser captive-portal login. Once installed and configured,
authentication is started with:

```bash
caa
```

CAA normally remains in the foreground. After confirming that it works, follow
the separate [Sophos CAA Manager guide](getting-started.md) to run it as a
background user service and handle network changes automatically.

## Prerequisites

- An active PES captive-portal account
- Authorization to download the Linux Authentication Client
- A 64-bit x86 Linux system for the `caa_x64.tar.gz` package
- A terminal and permission to install an executable under `/usr/local/bin`

Check the machine architecture:

```bash
uname -m
```

For the x64 package, the expected result is `x86_64`.

## 1. Download the CAA package

1. Open <https://rr.pes.edu:4443/> in a browser.
2. Sign in with your PES Internet Captive Portal credentials.
3. Open the **Download** section.
4. Download the Linux Authentication Client, typically named
   `caa_x64.tar.gz`.

Do not upload the downloaded archive or CAA binary to a public repository.

## 2. Extract the package

In the directory containing the download:

```bash
tar -xvf caa_x64.tar.gz
```

Enter the extracted directory. Its exact name may vary:

```bash
cd caa*
```

The expected contents are:

```text
.caa/
├── caa.conf
├── ca-cert.pem
└── README

bin/
└── caa
```

Before continuing, confirm that both locations exist:

```bash
test -f .caa/caa.conf
test -f bin/caa
```

## 3. Install the CAA configuration files

Copy the supplied configuration directory into the current user's home:

```bash
cp -a .caa "$HOME/"
```

Restrict the credential-bearing configuration file:

```bash
chmod 600 "$HOME/.caa/caa.conf"
```

Do not run this copy command as root. CAA reads configuration from the current
user's home directory, and the files should remain owned by that user.

## 4. Install the CAA executable

Install the executable in a standard system-wide command location:

```bash
sudo install -m 0755 bin/caa /usr/local/bin/caa
```

Verify command discovery:

```bash
command -v caa
caa --version
```

The path does not have to be `/usr/local/bin/caa`; it only needs to be an
executable named `caa` available through `PATH`.

## 5. Configure PES credentials

Open the user configuration:

```bash
nano "$HOME/.caa/caa.conf"
```

Set the fields using this format:

```text
Copernicus host: 192.168.254.1
Username: YOUR_USERNAME
Password: YOUR_PASSWORD
```

Important:

- Keep the Copernicus host set to `192.168.254.1` for the documented PES RR
  Campus setup.
- Replace the username and password placeholders with your own PES
  captive-portal credentials.
- When changing an existing password, remove the previous encrypted-password
  entry before adding the new plaintext `Password` value.
- Do not share, commit, screenshot, or paste `~/.caa/caa.conf` into an issue.

CAA 1.2.0 replaces the initial plaintext password with an encrypted
representation after its first successful start.

After saving, confirm restrictive permissions without displaying the file:

```bash
stat -c '%a %n' "$HOME/.caa/caa.conf"
```

The expected mode is `600`.

## 6. Run and test CAA

Start CAA as the normal user:

```bash
caa
```

A successful verbose session observed with CAA 1.2.0 includes:

```text
Connecting to host 192.168.254.1 ...
Login was accepted.
```

Expected behavior:

- CAA starts without asking for a password.
- Authentication succeeds.
- Internet connectivity becomes available.
- The process remains running in the terminal.

Press `Ctrl+C` to stop the foreground process.

## Daily use without CAA Manager

When Wi-Fi disconnects, the local IP changes, or you switch networks:

1. Press `Ctrl+C` in the terminal running CAA.
2. Reconnect to the PES Wi-Fi network.
3. Run `caa` again.

For normal CAA usage, avoid signing in through the browser captive portal at
the same time. Competing browser and CAA sessions may interfere with
authentication or session limits.

## Recommended: install CAA Manager

After manual CAA authentication works, install this project's manager:

```bash
python3 bootstrap.py
```

Then transfer the current foreground session when a brief restart is
acceptable:

```bash
python3 bootstrap.py --handover
```

CAA Manager then:

- runs CAA without an open terminal
- detects the PES portal at `192.168.254.1:8090`
- restarts CAA when the active connection or local IPv4 changes
- provides CLI and desktop-indicator controls

Continue with [Getting started](getting-started.md).

## Troubleshooting

### No Internet after starting CAA

Reconnect to Wi-Fi, stop the old CAA process, and start it again:

```bash
caa --stop
caa
```

### Authentication fails

- Verify the username and password in `~/.caa/caa.conf`.
- Confirm the Copernicus host is `192.168.254.1`.
- Check that only one CAA process is running:

```bash
pgrep -a -x caa
```

### Permission denied when running CAA

If CAA was installed somewhere other than `/usr/local/bin`, substitute the
actual path:

```bash
sudo chmod 0755 /usr/local/bin/caa
```

### Configuration is missing

Confirm the expected files:

```bash
ls -la "$HOME/.caa"
```

If necessary, return to the extracted package directory and repeat step 3.
Never download credential configuration from an unofficial source.

### CAA says another instance is running

Check the process:

```bash
pgrep -a -x caa
```

Stop the existing instance cleanly:

```bash
caa --stop
```

## Security notes

- Run CAA as the normal logged-in user.
- Use sudo only to install or update the executable.
- Keep `~/.caa/caa.conf` mode `0600`.
- Never publish the CAA package, binary, certificate bundle, or configuration.
- Obtain CAA only from the authorized PES/Sophos download portal.

For manager-specific problems, see [Troubleshooting](troubleshooting.md).

---

Adapted from the “PES University – RR Campus Linux CAA Installation Guide.”
Original guide compiled by Adnan Safdari.

