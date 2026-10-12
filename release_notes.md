
## What's Changed in v0.1.2 - 2026-10-12

> **11 commits** by **2 contributors** — thanks everyone! 🎉


### 🚀 Features

* add Legion R9000P AFR10 (83F6, RECN) support from RECN20WW DSDT *(kernel)* by @st0nie in [f9239c0](https://github.com/johnfanv2/LenovoLegionLinux/commit/f9239c03d49287ccbc1bd6e3e81cce0f55c1da9c)
* complete Legion 5 15IRX10 (83LY, QNCN) model config from QNCN38WW DSDT *(kernel)* by @st0nie in [dfb9d06](https://github.com/johnfanv2/LenovoLegionLinux/commit/dfb9d0605f9bf1bb5021bc0b7b7840a6bd587614)

### 🐛 Bug Fixes

* refuse percent bytes above level 10 on LPCN firmware *(python)* by @pengstem in [efe2921](https://github.com/johnfanv2/LenovoLegionLinux/commit/efe29215253f2630d42fcc00a6219cfe635b38b0)
* treat the LPCN fan table as levels and gate writes *(kernel)* by @pengstem in [a216ab6](https://github.com/johnfanv2/LenovoLegionLinux/commit/a216ab66a444d61ac5e1ad6a1d570a7a1a9eba64)
* drop xvfb-run from GUI smoke tests when Qt is offscreen *(ci)* by @st0nie in [ab20a12](https://github.com/johnfanv2/LenovoLegionLinux/commit/ab20a12dba0055160b69ff23d033ee5ec0d2a6b3)
* run container GUI smoke tests with Qt offscreen platform *(ci)* by @st0nie in [24de26a](https://github.com/johnfanv2/LenovoLegionLinux/commit/24de26a406f3f4044e7f8ed5bc997cbdbeb4e737)

### 📖 Documentation

* LPCN fan table levels, validation and only-upward limit by @pengstem in [d18588b](https://github.com/johnfanv2/LenovoLegionLinux/commit/d18588bd39de6782d2f4e2242bf281a4c1d06e0a)

### 🔧 CI & Build

* run bake from deploy/ so compose contexts resolve *(docker)* by @st0nie in [13bf9f2](https://github.com/johnfanv2/LenovoLegionLinux/commit/13bf9f21c84bfae4e069cc2dda4f10280386845f)
* cache container layers on GHA and start docker job immediately *(docker)* by @st0nie in [b4fa69c](https://github.com/johnfanv2/LenovoLegionLinux/commit/b4fa69c82743a9f46b9443f89affa3635de31024)

### 📦 Other Changes

* Merge pull request #634 from pengstem/fix/lpcn-fan-table-levels by @st0nie in [399aeaa](https://github.com/johnfanv2/LenovoLegionLinux/commit/399aeaa04f34f2e9a29a32c8951f08e32128bd6c) / [#634](https://github.com/johnfanv2/LenovoLegionLinux/pull/634)
* Merge pull request #635 from johnfanv2/ci-docker-cache-offscreen by @st0nie in [3f4e3cd](https://github.com/johnfanv2/LenovoLegionLinux/commit/3f4e3cd4ee2f0f422edbe5e1d8cc674fe926aa8b) / [#635](https://github.com/johnfanv2/LenovoLegionLinux/pull/635)

## ✨ New Contributors

* @pengstem made their first contribution

## ❤️ Contributors

Thanks to @st0nie, @pengstem for making this release possible!


**Full Changelog**: https://github.com/johnfanv2/LenovoLegionLinux/compare/v0.1.1...v0.1.2

