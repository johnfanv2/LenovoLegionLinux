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

`WMAA(0x2A)` unconditionally returns ACPI Integer `0`; that acknowledgement
is **not** proof that the MUX switched. The physical eDP GPIO/route is not yet
traced. The separate `SetIGPUModeStatus` method must not be confused with this
MUX-mode request.

## Linux interface and safeguards

- `graphics_mode`: read `hybrid` or `discrete`; write either word to request
  that mode for the next boot.
- Legacy `gsync`: keeps the existing project's inverted **hybrid** boolean
  convention (`1` = hybrid, `0` = discrete). Both writes share the same guard.
- Writes require the module parameter `allow_rlcn20_mux_write=1` **and**
  `ec_readonly=0`. They are disabled by default; no other models/BIOS versions
  receive this feature.
- The setter uses the GameZone MOF's four-byte `UINT32` parameter and validates
  the WMI Integer(0) acknowledgement. Each explicit request is forwarded even
  when `MSMF` already shows that mode: the pending EFI request can differ.
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
mode. **A reboot is necessary** and firmware may reboot once more. Verify the
internal eDP connector and PCI GPU identities after boot; DRM card numbering
is not stable. Do not attempt raw SMI/EC writes.

**Validation status:** Read-only status is confirmed on an 83LT/RLCN20WW in
`discrete` mode. The guarded mode *write and reboot round trip* remains
unverified; this feature should remain experimental until tested with BIOS
recovery access. Related hardware support report: issue #445.
