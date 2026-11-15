# GPU mode requests on Legion Pro 5 16ADR10 (83LT, RLCN BIOS)

This **experimental** integration is restricted to DMI product `83LT` and the
**ten exact RLCN BIOS versions** listed below. It requests a GPU mode for the
next firmware boot; it does **not** switch the eDP connector while Linux runs.

### Exact BIOS allowlist and firmware analysis

| Firmware | Firmware evidence |
| --- | --- |
| `RLCN20WW` | IFR, SMM/DXE; Hybrid ↔ Discrete reboot round trip passed on one 83LT |
| `RLCN21WW`, `RLCN25WW`, `RLCN26WW`, `RLCN27WW` | Matching IFR and SMM/DXE binaries with 20WW |
| `RLCN29WW` | Matching IFR and SMM/DXE; EFI Setup readback on an 83LT |
| `RLCN31WW`, `RLCN32WW` | Matching IFR and SMM/DXE binaries with 20WW |
| `RLCN33WW`, `RLCN34WW` | Matching IFR; updated SMM/DXE binaries with corresponding GPU-mode branches |

For every listed version, official Lenovo firmware images have the same
`SystemConfig` GUID (`A04A27F4-DF00-4D42-B552-39511302113D`), 700-byte
`Setup` data, `Graphics Device` offset `0x259`, and option values
UMA `0` / Discrete `1` / Dynamic `4`. The relevant DXE mode decision block is
byte-identical across all ten. The 33WW/34WW SMM binaries differ from older
versions, but still map software SMI `0xCA/0x25` to Hybrid and `0xCA/0x26`
to Discrete.

The module parameter retains its original name, `allow_rlcn20_mux_write`, for
backward compatibility. It remains **off by default** for *every* version;
unknown versions and other chassis cannot use this special `graphics_mode`
path even if their BIOS name begins with `RLCN` (the normal legacy WMI handling
outside this special path is unchanged).

For auditability, the extracted PE32 SHA-256 values are:

| Official BIOS group | `ChgBootSmm` SHA-256 | `AppSwitchDisplayModeDxe` SHA-256 |
| --- | --- | --- |
| 20WW/21WW/25WW/26WW/27WW/29WW/31WW/32WW | `40b6934872477b9addc1fb816635ba0559813089aa6cc722a89c58b9be80bac1` | `02e61d626b2f8177166cb5bf9e85a7b31898b3f0f46cf3aab3d06a2476333139` |
| 33WW/34WW | `d65b65a09dcecd354cd36ca9e47e3f9ad44f156f5a844a1937f00021f6993eb6` | `a8e8d74bbe7b3ef3f7d05b918806ba40a6e40dd29bac09bb32afdd85c978ef50` |

Source packages and per-release notes are available from Lenovo's official
download server, e.g. [RLCN20WW](https://download.lenovo.com/consumer/mobiles/rlcn20ww.exe)
and [RLCN34WW](https://download.lenovo.com/consumer/mobiles/rlcn34ww.exe).
These hashes refer to extracted PE32 sections, **not** the installer EXEs.

## Firmware evidence

Static analysis of the machine's ACPI DSDT and Lenovo's official RLCN BIOS
images confirms the following firmware path on the listed versions:

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

This confirms the **boot-time** route change in both directions on RLCN20WW.
For the remaining nine listed BIOS revisions, compatibility is supported by
firmware IFR and SMM/DXE analysis rather than an independent reboot round trip.
UMA-only writes and live, reboot-free display switching are outside this feature. Related hardware support report: issue #445.
