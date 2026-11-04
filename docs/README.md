# Documentation

[简体中文](zh-hans/README.md) · [Back to the project README](../README.md)

## Getting started

- [Installation](installation.md): dependencies per distribution, build, permanent install, DKMS, Secure Boot and uninstall.
- [Initial Usage Testing](initial-testing.md): check that the module loads, reads sensors and the fan curve, and writes the fan curve. Do this before a permanent installation.
- [Compatible Models](compatible-models.md): confirmed models and their supported features.

## Using LLL

- [Usage](usage.md): monitoring, fan curves (GUI, CLI, script), power modes, the `legiond` daemon, fan unlock, battery conservation, Fn lock, touchpad and keyboard backlight.
- [FAQ](faq.md): temperatures, fan behavior, power modes, BIOS/EC reset and troubleshooting.
- [Known Issues](known-issues.md): firmware limitations of the fan curve interfaces.

## Reference and development

- [Features and Testing](FEATURES_AND_TESTING.md): per-model and per-feature notes and hardware test procedures.
- [Overview for Developers](developers.md): the components of this project.
- [Reverse Engineering](REVERSE_ENGINEER.md): collecting WMI/ACPI/EC data for new models.
- [Test Plan](TESTPLAN.md): manual test plan.
- [Contributing](../CONTRIBUTING.md) and [AGENTS.md](../AGENTS.md): build, lint and contribution conventions.
- [Credits](credits.md): basis of this work, contributors and tools based on LLL.
