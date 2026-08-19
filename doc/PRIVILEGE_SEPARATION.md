# Privilege separation

`legion_gui` and `legion_cli` are ordinary desktop-user processes. They do not
invoke `sudo`, `pkexec`, or Polkit and they do not directly write kernel, EFI,
boot, or system configuration paths.

Hardware operations use a versioned, length-prefixed JSON protocol over
`/run/legion-linux/control.sock`. `legion_service` runs under systemd as root.
The socket is owned by `root:legion-linux` with mode `0660`; only root and
processes whose effective or supplementary groups include `legion-linux` can
connect. The service independently verifies peer credentials for defense in
depth.
Each message is a single dynamically sized UTF-8 JSON object. The receiver
reads bounded chunks and attempts to parse after each read, continuing until
the object is complete or the peer reaches EOF. Reads use fixed-size chunks,
short reads are handled correctly, and accepted connections have a deadline so
a stalled partial message cannot indefinitely block the serialized service.
Its protocol is deliberately narrow:

* Features are selected only by a compiled allowlist of known model feature
  names. A caller cannot supply a filesystem path or shell command.
* Read-only properties cannot be changed.
* Fan curves are parsed and validated as structured YAML before the service
  writes known sysfs attributes.
* Boot-logo uploads are bounded to 1 MiB and restricted to supported image
  suffixes. The service receives bytes, not a client-controlled privileged
  path.
* Linux peer credentials reject system/service accounts other than root and
  interactive users (UID 1000 or greater).

## User-owned configuration

Presets and GUI settings live in `~/.config/legion_linux`. Import and export
paths selected by the user are opened by the unprivileged client. For imports,
the client parses the file and uploads only structured content to the service.
For exports, the service returns structured content and the client writes the
selected destination. This prevents the root service from becoming an
arbitrary-file read/write primitive.

## Package behavior

The package installs `legion-linux.service`; distributions should enable and
start it during package installation. The old CLI/GUI Polkit actions are no
longer installed. The systemd unit includes filesystem and process hardening,
while retaining the `/sys` and `/boot` access required by advertised hardware
features.
