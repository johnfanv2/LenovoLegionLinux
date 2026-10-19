
## What's Changed in v0.1.4 - 2026-10-19

> **7 commits** by **3 contributors** — thanks everyone! 🎉


### 🚀 Features

* Legion Y530 (8JCN) fan curve and temperatures via the EC *(kernel)* by @metalfury in [db7185f](https://github.com/johnfanv2/LenovoLegionLinux/commit/db7185f710c70130a55c3c61889c734ed098af25)
* add Legion 5 15AKP10 (83F1, RYCN) model config *(kernel)* by @st0nie in [8877d10](https://github.com/johnfanv2/LenovoLegionLinux/commit/8877d105285fd638ff0a0ea2dc8be6426920d8da)

### 🐛 Bug Fixes

* treat NRCN and M1CN fan tables as levels, drop v0 EC bytes *(kernel)* by @st0nie in [5deb227](https://github.com/johnfanv2/LenovoLegionLinux/commit/5deb227fec88516c787600d5dcab931802a43ad7)
* treat M0CN (Slim 7 16IRH8) fan table as levels, gate writes *(kernel)* by @st0nie in [7567a94](https://github.com/johnfanv2/LenovoLegionLinux/commit/7567a949f96464e55a40e55c17ca80dab90b3b4d) / [#639](https://github.com/johnfanv2/LenovoLegionLinux/pull/639)
* update fan curve test for the removed EC4 method *(tests)* by @st0nie in [815bbde](https://github.com/johnfanv2/LenovoLegionLinux/commit/815bbdeca049e71143aaea25d82f9a62dd12539e)
* use the WMI level fan table on Legion 5 16IRX9 (83DG, NMCN) *(kernel)* by @V-Conet in [3b33228](https://github.com/johnfanv2/LenovoLegionLinux/commit/3b33228a4ec41fd82ef21628353e03f4a3929f97) / [#636](https://github.com/johnfanv2/LenovoLegionLinux/pull/636)

### 📖 Documentation

* document the Legion Y530 (8JCN) fan curve by @metalfury in [0699f2a](https://github.com/johnfanv2/LenovoLegionLinux/commit/0699f2a54065f6ae5d9affd0fbb1199bdb7f9b0f) / [#638](https://github.com/johnfanv2/LenovoLegionLinux/pull/638)
## ❤️ Contributors

Thanks to @st0nie, @metalfury, @V-Conet for making this release possible!


**Full Changelog**: https://github.com/johnfanv2/LenovoLegionLinux/compare/v0.1.3...v0.1.4

