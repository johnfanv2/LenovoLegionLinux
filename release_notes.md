
## What's Changed in v0.1.5 - 2026-10-30

> **10 commits** by **4 contributors** — thanks everyone! 🎉


### 🚀 Features

* fix EC3 fan curve read-back on LOQ 15IAX9 (83GS) *(kernel)* by @st0nie in [5090420](https://github.com/johnfanv2/LenovoLegionLinux/commit/509042066ad10e73c6650741850acb5db096a84d) / [#640](https://github.com/johnfanv2/LenovoLegionLinux/pull/640)

### 🐛 Bug Fixes

* use WMI3 for fan full speed on Legion Pro 5 16ARX8 (LPCN) *(kernel)* by @pragus in [41ab42f](https://github.com/johnfanv2/LenovoLegionLinux/commit/41ab42f7ca34d482393607509827ae45fcb99293) / [#644](https://github.com/johnfanv2/LenovoLegionLinux/pull/644)
* skip fan_maxspeed and IC temp on Legion Pro 5 16ARX8 (LPCN) *(kernel)* by @pragus in [1ba1d8d](https://github.com/johnfanv2/LenovoLegionLinux/commit/1ba1d8d2e1d9abd536ab06d2aae6855c0f33ac92) / [#645](https://github.com/johnfanv2/LenovoLegionLinux/pull/645)
* remove stale wheels before installing the python package *(deploy)* in [ff72e4c](https://github.com/johnfanv2/LenovoLegionLinux/commit/ff72e4c2b437ec605d5f2e34c5b34111c57c9cc0) / [#643](https://github.com/johnfanv2/LenovoLegionLinux/pull/643)
* leave GameZone WMI to lenovo-wmi-gamezone on QNCN *(kernel)* by @TanelLaas in [711f91c](https://github.com/johnfanv2/LenovoLegionLinux/commit/711f91c5959192930cc02a7033c0ce0b46ca8606)
* read the QNCN EC sensor bytes at their real offsets *(kernel)* by @TanelLaas in [cd81660](https://github.com/johnfanv2/LenovoLegionLinux/commit/cd816605866578a9183b8191441fd2ad55a95ecc)
* build container module against the image's own headers *(ci)* by @st0nie in [f1f3e2a](https://github.com/johnfanv2/LenovoLegionLinux/commit/f1f3e2a9d4eeed09a770ab18842d9ea57187a7c0)
* install linux-modules-extra only when it exists *(ci)* by @st0nie in [0b7495e](https://github.com/johnfanv2/LenovoLegionLinux/commit/0b7495edc96a64430611b4cb5abf1ee40bfe3762)

### 📖 Documentation

* record the QNCN hardware validation by @TanelLaas in [3d081d9](https://github.com/johnfanv2/LenovoLegionLinux/commit/3d081d9503d524e242eedf67006dbc049aa8e4fc)

### 📦 Other Changes

* Merge pull request #642 from TanelLaas/qncn-ec-registers by @st0nie in [468d63e](https://github.com/johnfanv2/LenovoLegionLinux/commit/468d63e62e6fdb37286a9ff9fd139bb236029d7a) / [#642](https://github.com/johnfanv2/LenovoLegionLinux/pull/642)

## ✨ New Contributors

* @pragus made their first contribution in [#644](https://github.com/johnfanv2/LenovoLegionLinux/pull/644)

## ❤️ Contributors

Thanks to @pragus, @, @st0nie, @TanelLaas for making this release possible!


**Full Changelog**: https://github.com/johnfanv2/LenovoLegionLinux/compare/v0.1.4...v0.1.5

