# Legion Toolkit (Lenovo LOQ 83SC build)

A power/fan/battery/RGB/overclock control toolkit for the **Lenovo LOQ 83SC**
(BIOS `SECN*`, EC `0x5508`, RTX 5050). It is a thin, model-specific layer on top
of [LenovoLegionLinux](https://github.com/johnfanv2/LenovoLegionLinux).

## Dual codebase (the key design point)

The toolkit contains **two independent codebases** and a model-gate dispatcher
that loads the correct one at runtime:

| Path | Purpose |
|------|---------|
| `custom/legion-gui.py` | 83SC-specific dashboard GUI (this model) |
| `custom/legion-cli.py` | 83SC-specific power CLI (`tdp`, `cpu-tau`, `gpu-ctgp`, …) |
| `upstream/legion-gui.py` | unmodified upstream Legion Linux GUI |
| `upstream/legion-cli.py` | unmodified upstream Legion Linux CLI |
| `lib/lll_adapter.py` | hardware access shim shared by both |
| `legion-tray.py` | system tray launcher |
| `legion-gui.py`, `legion-cli.py` | **generated** dispatchers (do not edit by hand) |

### Model gate

`legion-gui.py` / `legion-cli.py` read DMI (`sys_vendor`, `product_name`,
`bios_version`). On a Lenovo LOQ 83SC they run the `custom/` codebase; on any
other model they `exec()` the upstream codebase embedded as base64. This means a
single deployed file works on every Legion model — no model-specific forks in
the field, no crash on unsupported hardware.

## Build & install

```bash
python3 tools/build_combined.py   # regenerate legion-gui.py / legion-cli.py
sudo tools/install.sh             # deploy to /usr/lib/legion-toolkit/
```

Edit `custom/` or `upstream/`, then rebuild — never hand-edit the generated
`legion-gui.py` / `legion-cli.py`.

## Environment independence

- **No forced Qt platform.** The GUI/tray no longer set `QT_QPA_PLATFORM` or
  `WAYLAND_DISPLAY`; Qt auto-selects Wayland or X11. The desktop entry does not
  force a platform either.
- **No machine-specific paths.** Config lives under `XDG_CONFIG_HOME`
  (`~/.config/legion-toolkit/`). Hardware sysfs paths are probed, not hardcoded
  to one user's layout.
- **Graceful privilege use.** `pkexec` is used only when present; the one-time
  NVIDIA modeset tweak is skipped (not crashed) if `pkexec` is unavailable.

## CLI custom commands

`legion-ctl --help` (or `legion-cli.py --help`) lists generic commands under
*Commands* and the LOQ 83SC specific power controls (e.g. `tdp`, `cpu-tau`,
`gpu-ctgp`) in a separate *LOQ 83SC custom power controls* section. The
`legion-ctl` / `legion-gui` commands are installed to `/usr/local/bin` by
`install.sh`; both are thin launchers onto the model-gated dispatcher, so on
83SC they run the custom build and on any other model they transparently run the
upstream Legion Linux CLI/GUI.

Hardware-writing commands need root — prefix with `pkexec`, e.g.
`pkexec legion-ctl tdp 55`.

## Desktop environment / compositor support

The toolkit is DE-agnostic for all core functions (power, fan, battery,
overclock, CLI). The display features dispatch by detected compositor:

| Feature | KDE Plasma 6 | Hyprland | GNOME | other |
|---------|--------------|----------|-------|-------|
| Dashboard GUI / CLI | ✅ | ✅ | ✅ | ✅ |
| VRR / FreeSync | ✅ kscreen-doctor + kwriteconfig6 | ✅ hyprctl | ✅ gsettings (experimental-features) | ⚠️ unsupported (message lists supported DEs) |
| Refresh-rate set | ✅ kscreen-doctor | ✅ hyprctl | — | ⚠️ unsupported (message lists supported DEs) |
| System tray | ✅ native | ✅ with a tray host (e.g. waybar) | ⚠️ needs `gnome-shell-extension-appindicator`, **or** the built-in floating "Legion" button fallback | ✅ native / fallback button |

Detection uses `XDG_CURRENT_DESKTOP` + `WAYLAND_DISPLAY`; see
`_detect_compositor()` in `custom/legion-gui.py`. The VRR/refresh code is **not**
hard-wired to KDE — it branches per compositor and degrades gracefully elsewhere.

**Tray on GNOME:** GNOME has no native StatusNotifierItem host, so without the
appindicator extension Qt's `QSystemTrayIcon` would be invisible. As an
architectural fallback the tray spawns a small always-on-top "Legion" button that
opens the same menu, so the app stays reachable regardless of desktop.
