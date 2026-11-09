# RLCN20WW GPU mode requests on Legion Pro 5 16ADR10 (83LT)

This **experimental** integration is restricted to DMI product `83LT` with
BIOS **exactly `RLCN20WW`**. It requests a GPU mode for the next firmware boot;
it does **not** switch the eDP connector while Linux is running.

## Firmware evidence

Static analysis of the machine's ACPI DSDT and Lenovo's official RLCN20WW BIOS
image confirms the following path:

1. GameZone WMI `WMAA(0x28)` returns capability `2`; `WMAA(0x29)` reads
   EC `MSMF` for the currently reported mode.
2. `SetGSyncStatus(0)` sends software SMI `0xCA` with subcommand `0x25`
   (hybrid); `SetGSyncStatus(1)` sends `0xCA/0x26` (discrete).
3. `ChgBootSmm` (FFS GUID `4CA0062A-66FE-4BE7-ACE6-FDE992C1C5EC`)
   registers SMI `0xCA` and writes the two-byte EFI variable
   `AppMuxSwitchModeChange` (GUID `6ACCE65D-DA35-4B39-B64B-5ED927A7DC7E`).
   Subcommands `0x25` and `0x26` set its second byte to `4` and `1`, respectively.
4. On a subsequent firmware boot, `AppSwitchDisplayModeDxe` consumes that
   request, updates `Setup`, `AMD_PBS_SETUP` and `AmdSetupRPL`, synchronizes AMD
   configuration, and may invoke `ResetSystem(EfiResetCold)` again.

The BIOS `SetupUtility` HII/IFR additionally defines **three** `Graphics Device`
settings at `Setup` byte offset `0x259`: `UMA Graphics = 0`,
`Discrete Graphics = 1`, and `Dynamic Graphics = 4` (default). `ChgBootSmm`
also accepts SMI `0xCA/0x24`, which writes pending mode `0` to the second byte
of `AppMuxSwitchModeChange`. No corresponding *UMA-only* GameZone WMI command
is exposed by this DSDT, so it cannot be requested with `SetGSyncStatus(2)`.

`WMAA(0x2A)` unconditionally returns ACPI Integer `0`; that acknowledgement
is **not** proof that the MUX switched. The actual internal eDP routing was
verified across reboots using PCI/DRM, but the underlying MUX GPIO/register
has not been traced. The separate `SetIGPUModeStatus` method must not be
confused with this MUX-mode request.

## Linux interface and safeguards

- `graphics_mode`: reads `integrated`, `hybrid`, or `discrete` from BIOS
  `Setup` byte `0x259`. This requires Linux 6.3 or newer and accessible EFI
  runtime variables. Otherwise the read fails rather than guessing from the
  one-bit WMI state. Only `hybrid` and `discrete` can be requested; integrated
  writes are not supported.
- Legacy `gsync` retains the existing inverted hybrid boolean (`1` = hybrid,
  `0` = discrete). When EFI readback identifies UMA, reading it returns
  `-EOPNOTSUPP`. If EFI readback is unavailable, it falls back to the original
  WMI behavior for compatibility; in that case UMA cannot be distinguished and
  the result must not be interpreted as a reliable three-state readout.
- Writes require `allow_rlcn20_mux_write=1` and `ec_readonly=0` and are disabled
  by default. Hybrid/Discrete requests use the GameZone four-byte `UINT32`
  parameter and check the WMI Integer(0) acknowledgement. Each request is
  forwarded even if the current mode matches, as a pending request may differ.
- No UMA request is implemented: writing EFI variables directly has not been
  tested on hardware. Existing GameZone binding behavior is unchanged for all
  RLCN firmware versions.

Read-only inspection:

```sh
cat /sys/devices/platform/legion/graphics_mode
cat /sys/devices/platform/legion/gsync
cat /sys/devices/platform/legion/issupportgsync
for card in /sys/class/drm/card*-eDP-*; do
    printf '%s: ' "$card"
    cat "$card/status"
done
lspci -nn | grep -Ei 'VGA|3D|Display|Dummy'
```

With a deliberately reloaded module and explicit opt-in, writing
`hybrid`/`discrete` to `graphics_mode` requests the corresponding next-boot
mode. **A reboot is necessary** and firmware may reboot once more. Verify the
internal eDP connector and PCI GPU identities after boot; DRM card numbering
is not stable. Do not attempt raw SMI/EC writes.

**Validation status (83LT/RLCN20WW, 2026-11-08):** The guarded write and
reboot round trip was verified on one machine:

- Writing `hybrid` with both write guards explicitly enabled returned success.
  After reboot, AMD Radeon 610M (`1002:164e`, PCI `05:00.0`) was a VGA
  controller driven by `amdgpu`, and the internal connected eDP was on AMD's
  `card0-eDP-1`. NVIDIA (`10de:2d58`) remained enumerated.
- A one-shot safety timer subsequently read `Current mode: hybrid`, confirming
  that the WMI mode readback agreed with AMD's eDP routing. It requested
  `discrete` and rebooted. The next boot exposed AMD's `05:00.0` as a PCI
  dummy function (`1022:14de`), while NVIDIA drove the connected eDP panel.
- The temporary rollback timer and service have since been removed. The
  module's firmware-write guard was restored after each request.

This confirms the **boot-time** route change in both directions on this BIOS;
it does not validate UMA-only writes, a live, reboot-free display switch, or
compatibility with other firmware revisions. Related hardware support report:
issue #445.
