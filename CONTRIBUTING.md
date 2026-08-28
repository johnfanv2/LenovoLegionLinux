# Contributing to LenovoLegionLinux

Thank you for your interest in contributing to LenovoLegionLinux (LLL)!
This project is community-driven — most of the supported laptop models and
features were contributed by users who owned the hardware. Pull requests are
very welcome.

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

> **Note for AI coding assistants:** this repository ships an
> [AGENTS.md](AGENTS.md) with machine-oriented build, test, and style
> instructions. The human-readable summary below mirrors it.

## Table of Contents

- [Ways to Contribute](#ways-to-contribute)
- [Reporting Issues](#reporting-issues)
- [Development Setup](#development-setup)
- [Build, Test, and Lint](#build-test-and-lint)
- [Style and Quality Gates](#style-and-quality-gates)
- [Commit and PR Conventions](#commit-and-pr-conventions)
- [Adding Support for a New Laptop Model](#adding-support-for-a-new-laptop-model)
- [Hardware Safety Rules](#hardware-safety-rules)

## Ways to Contribute

- **Code**: fix bugs, add features, add support for your laptop model.
- **Testing**: run the tests in the README on your hardware and report
  results (success *and* failure reports are valuable — include your exact
  model and BIOS version).
- **Documentation**: keep the READMEs (`README.md` and `README_zh-hans.md`,
  which are maintained in sync) and the files in `doc/` accurate.

An issue alone gives us very little to work with: we do not have access to
your hardware. If at all possible, please try to fix the problem locally,
test it on your own machine, and open a PR that references the issue.
AI coding assistants (e.g. Claude Code, Codex, Cursor) work well for this —
point them at [AGENTS.md](AGENTS.md) and they will find the build/test
instructions on their own.

## Reporting Issues

Before opening a new issue, search
[existing issues](https://github.com/johnfanv2/LenovoLegionLinux/issues)
(including closed ones) for your laptop model and BIOS version.

When reporting a problem, please include:

- Exact laptop model (e.g. *Legion Pro 7 16IRX8H*) and BIOS version
  (`sudo dmidecode -s bios-version`)
- Linux distribution and kernel version (`uname -r`)
- The output of `sudo dmesg | grep -i legion` after loading the module
- The output of `sensors` and, for fan issues,
  `sudo cat /sys/kernel/debug/legion/fancurve`
- The exact commands you ran and what you expected vs. what happened

If the module refuses to load with "not in allowlist", that is the DMI
allowlist working as intended — see
[Adding Support for a New Laptop Model](#adding-support-for-a-new-laptop-model)
instead of asking for the allowlist to be widened blindly.

## Development Setup

```bash
git clone https://github.com/johnfanv2/LenovoLegionLinux.git
cd LenovoLegionLinux
```

Install the dependencies for your distribution — ready-made scripts live in
`deploy/dependencies/` (e.g. `install_dependencies_ubuntu_24_04.sh`), or
follow the manual package lists in the README's *Requirements* section.

Repository layout:

| Path | What it is |
|---|---|
| `kernel_module/` | `legion-laptop.c` kernel module (C) |
| `python/legion_linux/` | Python library + `legion_cli` + `legion_gui` |
| `extra/service/legiond/` | `legiond`/`legiond-ctl` daemon (C, gnu2x) |
| `extra/service/` | systemd/OpenRC units, `legiond.ini`, fan curve presets |
| `extra/smartfan/` | Standalone bash fan daemon (needs only `acpi_call`) |
| `tests/` | Test/lint scripts — exactly what CI runs |
| `deploy/` | Packaging: RPM specs, Dockerfiles, dependency scripts |

## Build, Test, and Lint

Run the same scripts that CI (`.github/workflows/build.yml`) runs.

### Kernel module

```bash
cd kernel_module
make                       # build
sudo make reloadmodule     # unload + reload in-place for testing
./tests/test_kernel_checkpath.sh   # checkpatch lint (must stay clean)
```

### Python package

```bash
./tests/test_python.sh      # pylint (MUST pass)
./tests/test_python_cli.sh  # CLI smoke test (no hardware needed)
black python/legion_linux   # formatter (line-length 120)
```

### legiond daemon

```bash
cd extra/service/legiond
make   # requires libinih; builds with -Wall -Wextra, zero warnings expected
```

### SmartFan

```bash
bash -n extra/smartfan/*.sh   # syntax check; run shellcheck if available
```

## Style and Quality Gates

- **Kernel C code**: Linux kernel coding style. The repo-root `.clang-format`
  is the upstream kernel clang-format — format the code you touch.
  `checkpatch.pl` (via `tests/test_kernel_checkpath.sh`) must stay clean.
- **legiond C code**: same `.clang-format`; zero warnings with
  `-Wall -Wextra`.
- **Python**: `black` (line-length 120, see `pyproject.toml`) and `pylint`
  (config `python/legion_linux/pylintrc`). **pylint must always pass.**
- **Never commit build artifacts** (`*.o`, `*.ko`, `*.mod*`, `legiond`
  binaries, `__pycache__`, …). `.gitignore` covers them — if you find
  yourself force-adding a file, stop and reconsider.

## Commit and PR Conventions

- Short imperative commit subjects; conventional prefixes are in use
  (`feat(scope):`, `fix(scope):`, `docs:`). Keep unrelated changes in
  separate commits.
- **Docs parity**: user-facing behavior changes must update **both**
  `README.md` and `README_zh-hans.md`, plus `doc/FEATURES_AND_TESTING.md`
  if a feature or test procedure changes.
- In the PR description, reference the issue you are fixing
  (e.g. `Fixes #123`) and describe how you verified the change on real
  hardware (commands run, observed output).

## Adding Support for a New Laptop Model

1. Find your BIOS version: `sudo dmidecode -s bios-version`
   (e.g. `GKCN58WW` — the leading letters `GKCN` are the model family key).
2. Add a DMI allowlist entry in `kernel_module/legion-laptop.c`, keyed on
   the BIOS version prefix, reusing an appropriate existing `model_*`
   config as `driver_data`.
3. Build and test on your machine. For a first quick test without touching
   the allowlist you can use `sudo make forcereloadmodule` — but the PR
   must add a proper allowlist entry.
4. Verify: `sudo dmesg | grep -i legion`, `sensors`,
   `sudo cat /sys/kernel/debug/legion/fancurve`, and the fan curve tests
   from the README.
5. Add your model to the *Confirmed Compatible Models* list in **both**
   READMEs.

Do **not** widen `has_fan_unlock` (or similar feature flags) beyond
model/BIOS combinations you have actually validated on hardware.

## Hardware Safety Rules

This project writes to EC memory and invokes ACPI/WMI methods — mistakes
can affect real fan/thermal behavior.

- Gate new sysfs/WMI functionality behind model/feature flags (see how
  `has_fan_unlock` is implemented).
- Default to the safest behavior; never enable risky behavior
  unconditionally.
- Document how to verify the change on real hardware in your PR.

Thank you for contributing!
