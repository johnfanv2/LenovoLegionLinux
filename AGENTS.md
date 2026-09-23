# AGENTS.md

Guidance for AI coding agents (and humans) working on LenovoLegionLinux (LLL).

## What this project is

LLL is a Linux driver + userspace toolkit for Lenovo Legion laptops (an open
alternative to Lenovo Vantage / Legion Zone on Windows). It talks to the
embedded controller (EC) and ACPI/WMI firmware to expose fan curves, power
modes, sensors, battery conservation, and more through standard Linux
interfaces (sysfs, debugfs, hwmon).

**This project writes to hardware (EC memory, ACPI methods).** Changes to the
kernel module, `legiond`, or SmartFan can affect real fan/thermal behavior.
Prefer conservative defaults and never enable risky behavior unconditionally.

## Repository layout

| Path | What it is | Language |
|---|---|---|
| `kernel_module/` | `legion-laptop.c` kernel module (sysfs/hwmon/debugfs/platform-profile) | C (kernel) |
| `python/legion_linux/` | Python package: `legion.py` (library), `legion_cli.py`, `legion_gui.py` | Python 3 |
| `extra/service/legiond/` | `legiond` + `legiond-ctl` daemon (auto fan-profile switching) | C (gnu2x) |
| `extra/service/` | systemd/OpenRC units, `legiond.ini`, fan curve `profiles/*.yaml` | shell/ini/yaml |
| `extra/smartfan/` | Standalone shell fan daemon for Legion 7 Gen 10+ (needs only `acpi_call`) | bash |
| `deploy/` | Packaging: RPM specs, Dockerfiles, per-distro dependency scripts | shell/spec |
| `tests/` | Test/lint scripts — **these are exactly what CI runs** | bash |
| `subprojects/` | AUR DKMS packaging | PKGBUILD |
| `doc/` | Assets, `FEATURES_AND_TESTING.md`, `REVERSE_ENGINEER.md`, `TESTPLAN.md` | markdown |

## Build, test, lint — per component

CI (`.github/workflows/build.yml`, ubuntu-24.04) installs dependencies via
`deploy/dependencies/install_dependencies_ubuntu_24_04.sh` (build) and
`install_development_dependencies_ubuntu_24_04.sh` (lint), then runs the
scripts below. **Run the same scripts locally before committing.**

### Kernel module (`kernel_module/`)

```bash
cd kernel_module
make                      # build (needs linux-headers for the running kernel)
sudo make reloadmodule    # unload + reload in-place for testing
sudo make forcereloadmodule   # same, but bypass the DMI model allowlist
sudo make install         # permanent install
sudo make dkms            # install via DKMS (auto-rebuild on kernel updates)
```

- Lint: `./tests/test_kernel_checkpath.sh` — runs the kernel `checkpatch.pl`
  (with `--ignore LINUX_VERSION_CODE --ignore CONSTANT_COMPARISON`) on
  `legion-laptop.c`. It must stay clean.
- Style: Linux kernel coding style. The repo-root `.clang-format` is the
  upstream kernel clang-format (clang-format >= 11); format touched C code
  with it.
- Build artifacts (`*.o`, `*.ko`, `*.mod*`, `Module.symvers`, …) are
  git-ignored — never commit them.

### legiond daemon (`extra/service/legiond/`)

```bash
cd extra/service/legiond
make          # builds legiond and legiond-ctl; gcc -std=gnu2x -Wall -Wextra
make clean    # requires libinih (links -linih)
```

- Zero-warning build is expected (`-Wall -Wextra`).
- Format C changes with the repo-root `.clang-format`.
- Runtime layout: binary in `/usr/bin`, config in
  `/etc/legion_linux/legiond.ini` + fan curve presets, units
  `legiond.service`, `legiond-onresume.service`, `legiond-cpuset.timer`.
  See `extra/service/legiond/README.org` for architecture (Unix socket +
  inotify on power-state/power-profile files — **no acpid dependency**).
- The `legiond`/`legiond-ctl` binaries are git-ignored.

### Python package (`python/legion_linux/`)

```bash
# Lint gate — MUST pass (CI runs exactly this):
./tests/test_python.sh
# = pylint --rcfile python/legion_linux/pylintrc python/legion_linux/legion_linux

# CLI smoke test (works without the kernel module loaded):
./tests/test_python_cli.sh

# Format (config in pyproject.toml, line-length 120 to match pylintrc):
black python/legion_linux
```

- Rules: **pylint must always pass; format all Python changes with `black`
  before committing.**
- Run CLI/GUI from the repo:
  `sudo python/legion_linux/legion_linux/legion_cli.py [--help]` /
  `sudo python/legion_linux/legion_linux/legion_gui.py`
- Runtime deps: PyQt6, PyYAML, argcomplete, darkdetect.
- Entry points (installed): `legion_cli`, `legion_gui`.

### SmartFan (`extra/smartfan/`)

Pure bash + `acpi_call`. `install.sh` installs the daemon, TUI switcher
(`workmode`), and turbo toggles. Test changes with `bash -n` and
shellcheck if available.

## Contribution conventions

- **Commits**: short imperative subject; conventional prefixes are in use
  (`feat(scope):`, `fix(scope):`, `docs:`). Keep unrelated changes in
  separate commits.
- **Docs parity**: user-facing behavior changes must update **both**
  `README.md` and `README_zh-hans.md` (they are kept in sync), plus
  `doc/FEATURES_AND_TESTING.md` if a feature/test procedure changes.
- **Adding a laptop model**: add a DMI allowlist entry in
  `kernel_module/legion-laptop.c` keyed on BIOS version prefix (e.g.
  `GKCN`, `N0CN`) with an appropriate existing `model_*` config as
  `driver_data`. Do not widen `has_fan_unlock` beyond validated
  model/BIOS combinations.
- **Never commit**: build artifacts, `__pycache__`, editor files
  (`.gitignore` covers these — if you find yourself force-adding something,
  stop and reconsider).
- **Hardware-affecting changes**: gate new sysfs/WMI functionality behind
  model/feature flags (see how `has_fan_unlock` is done), default to the
  safest behavior, and document how to verify on real hardware
  (`sudo dmesg`, `sensors`, `cat /sys/kernel/debug/legion/fancurve`).

## Useful verification commands on real hardware

```bash
sudo dmesg | grep -i legion              # module probe status
sensors                                  # legion_hwmon temps/fan RPM
sudo cat /sys/kernel/debug/legion/fancurve   # EC fan curve debug dump
cat /sys/firmware/acpi/platform_profile      # current power mode
```

If the module refuses to load with "not in allowlist", that is the DMI
allowlist working as intended — test with `sudo make forcereloadmodule`
and report the model/BIOS instead of silently widening the allowlist.
