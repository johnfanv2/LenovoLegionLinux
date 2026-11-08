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

- `graphics_mode`: read `integrated` (BIOS `UMA Graphics`), `hybrid` (BIOS
  `Dynamic Graphics`), or `discrete`. Write a name to request the next-boot mode.
  The read path uses the BIOS `Setup` variable's byte `0x259`, since the EC's
  one-bit `MSMF` cannot distinguish integrated from hybrid.
- Legacy `gsync`: keeps the existing project's inverted **hybrid** boolean
  convention (`1` = hybrid, `0` = discrete). It cannot represent integrated:
  reading `gsync` in UMA mode returns `-EOPNOTSUPP` instead of misleadingly
  reporting the mode as discrete.
- Writes require the module parameter `allow_rlcn20_mux_write=1` **and**
  `ec_readonly=0`. They are disabled by default; no other models/BIOS versions
  receive this feature.
- **UMA-only writes additionally require `allow_rlcn20_uma_write=1`** (default
  off). They use the synchronized Linux EFI-variable interface to stage
  `AppMuxSwitchModeChange` with mode `0`, rather than issuing a raw software
  SMI. The existing variable's first byte is preserved; a missing variable is
  initialized with zero. This three-state EFI interface requires Linux 6.3 or
  newer; older kernels retain the two-state WMI readback and reject UMA
  requests. On the next boot, DXE deletes the pending request; it applies
  the mode change only if the requested mode differs from the current mode
  and `Setup+0x25c` (`IsS4Resume`) is not `1`.
  The SMM handler uses a privileged SMM variable protocol, while Linux uses
  EFI runtime variable services: firmware variable policy may reject a
  runtime write even when the SMM request is accepted.
  This path **has not been tested by a reboot**. The BIOS explicitly warns
  that UMA mode may disable HDMI / Type-C display output. Do not enable the
  extra option without local display access and a recovery plan.
- Hybrid/Discrete requests use the GameZone MOF's four-byte `UINT32` parameter
  and validate the WMI Integer(0) acknowledgement. Each explicit request is
  forwarded even when `MSMF` already shows that mode: the pending EFI request
  can differ. UMA requests instead use the separate EFI-variable path above.
- The GameZone WMI device is left to `lenovo-wmi-gamezone` to avoid contention
  with mainline firmware-attribute/platform-profile support.

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
mode. For an **unverified** UMA-only request, `allow_rlcn20_uma_write=1` must
also be set at module load, then `integrated` may be written to the same
attribute. **A reboot is necessary** and firmware may reboot once more. Verify the
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
