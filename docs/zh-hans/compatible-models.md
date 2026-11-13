# 兼容型号

**从 2020 年到最新的 2025 款联想拯救者机型大概率都能兼容 —— 本驱动仍在积极维护中，新机型会持续加入。以下为已确认可用的具体型号。如果你的 BIOS 版本前缀相同，例如 EFCN（如 EFCN54WW），那很可能也能兼容。如果你想确认你的型号是否可用，或发现不可用，请提交 issue。**

- 联想拯救者 5 15IMH05, 15IMH05H（BIOS EFCN54WW）：传感器、风扇曲线、电源配置
- Lenovo Legion Slim 5 16AHP9（83DH，BIOS NRCN20WW），第 9 代：传感器、电源模式、自定义模式下的风扇全速控制。风扇曲线仅以转速档位读取；在验证之前默认禁止写入（[#516](https://github.com/johnfanv2/LenovoLegionLinux/issues/516)）。参见 [NRCN 说明](../FEATURES_AND_TESTING.md#legion-slim-5-16ahp9-83dh-nrcn)。
- Lenovo Legion Slim 7 16APH8（82Y4，BIOS M1CN48WW）：传感器、电源模式；风扇曲线仅以转速档位读取，默认禁止写入（与 Slim 7 16IRH8 同机型的 AMD 版，同为 EC 0x5507；[#599](https://github.com/johnfanv2/LenovoLegionLinux/issues/599)）
- 联想拯救者 5 15ACH6H（BIOS GKCN58WW、GKCN57WW 或 GKCN65WW），第六代：传感器、风扇曲线、电源配置
- 联想拯救者 R9000（R9000K2021H）（BIOS GKCN59WW）：传感器、风扇曲线、电源配置
- 联想拯救者 5 Pro 16ACH6H (82JQ)（BIOS GKCN58WW）x 2：传感器、风扇曲线、电源配置
- Legion 5 Pro 16ACH6H（AMD 5800H + Nvidia RTX 3070）：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ARH05A（BIOS FSCN14WW），第五代：传感器、风扇曲线
- 联想拯救者 5 15ARH05H（BIOS FSCN14WW 或 FSCN26WW），第五代：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ITH6H（BIOS H1CN49WW，Intel）：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ARH7H（BIOS JUCN55WW），第七代：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ACH6（BIOS HHCN31WW）：传感器、风扇曲线、电源配置
- 联想拯救者 S7 16ARHA7（BIOS KFCN32WW）：传感器、风扇曲线（无mini风扇曲线）、电源配置
- 联想拯救者 5 Pro 16ITH6（BIOS H1CN52WW（H1CN51WW的CPU温度有误））：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ACH6A（BIOS G9CN30WW），全AMD版本：传感器、风扇曲线（含mini风扇曲线）、电源配置
- 联想拯救者 5 17ACH6（BIOS HHCN31WW）：传感器、风扇曲线、电源配置
- 联想拯救者 7i 16ITHG6（BIOS H1CN35WW）：传感器、风扇曲线、电源配置
- 联想拯救者 7 Pro 16ARX8H（BIOS LPCN47WW）：传感器、风扇曲线、电源配置
- 联想拯救者 Pro 5 16ARX8 (82WM)（BIOS LPCN59WW/LPCN65WW）：传感器、风扇曲线（仅速度等级，默认禁止写入，见下方 LPCN 说明）、电源配置
- 联想拯救者 7 16IAX7 (82TD)（BIOS K1CN48WW）：传感器、风扇曲线（写入正常；WMI 回读返回空缓冲区）、电源配置
- 联想拯救者 Pro 7 16IRX8H（BIOS KWCN54WW）：传感器、风扇曲线、电源配置、风扇解锁（可将风扇上限从约 4400 RPM 提升至约 7100 RPM）
- 联想拯救者 Pro 5 16IRX8（82WK，BIOS KWCN54WW）：传感器、风扇曲线（0-10 等级索引，自定义电源模式）、电源配置、通过 Other Method WMI 路径的功耗限制与风扇全速；风扇曲线已在 Linux 自定义电源模式下验证（9 级 → 4400/4600 RPM，10 级 → 5400/5400 RPM）
- 联想拯救者 Pro 7 16IAX10H（83F5，BIOS Q7CN78WW），第十代：传感器（含第三个风扇的转速，hwmon `fan3`）、挂起恢复后自动重新应用自定义风扇曲线、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、无键盘/灯光控制；已在 Linux 上验证（进入自定义模式、写入风扇表点并从 EC RAM 读回）；详见 [Q7CN 说明](../FEATURES_AND_TESTING.md#legion-pro-7-16iax10h-83f5-q7cn)
- 联想拯救者 Pro 5 16ADR10（83LT，BIOS RLCN31WW），第十代（AMD）：传感器、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、键盘背光与 Y 型 Logo 灯、风扇全速（仅限自定义模式）；基于 issue #445 的 DSDT 分析启用，真机验证进行中；详见 [RLCN 说明](../FEATURES_AND_TESTING.md#legion-pro-5-16adr10-83lt-rlcn)
- 联想拯救者 7 16IRX9，第九代：传感器、风扇曲线、电源配置；也可通过 [SmartFan](../../extra/smartfan/) 在不加载内核模块的情况下使用
- 联想拯救者 5 16IAX10（83NX，BIOS Q6CN32WW），第十代（Intel）：通过 WMI3 提供的功耗限制属性（`cpu_temperature_limit`、`cpu_l1_tau`、`gpu_power_target_offset`、长/短期功耗限制）；风扇曲线读取正常，但自定义电源模式目前无法激活（已知问题）；已在 Linux 上历经五次重载、一次 main 合并及一次 BIOS 更新验证；详见 [Q6CN 说明](../FEATURES_AND_TESTING.md#legion-5-16iax10-83nx-q6cn)
- 联想拯救者 Pro 5 16IAX10H（83LU，BIOS Q6CN26WW），第十代（Intel）：传感器、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、白色键盘背光、风扇全速（仅限自定义模式）、通过内核自带的 `lenovo-wmi-other` 固件属性设置 CPU 功耗限制（PL1/PL2，自定义模式，已在 Q6CN79WW 上验证）；WMI 固件布局与上方 83F5 Q7CN 相同，基于 issue #337 的 DSDT 分析与已验证读数启用，真机验证进行中；详见 [83LU 说明](../FEATURES_AND_TESTING.md#legion-pro-5-16iax10h-83lu-q6cn)
- 联想拯救者 5 15AHP10（83M0，BIOS RGCN27WW），第十代（AMD）：传感器、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、键盘背光、风扇全速（仅限自定义模式）；经 DSDT 验证为上方 83LT RLCN 的同胞机型（issue #373），真机验证进行中；详见 [RGCN 说明](../FEATURES_AND_TESTING.md#legion-5-15ahp10-83m0-rgcn)
- 联想拯救者 Pro 5 16IAX10（83F3，BIOS Q6CN79WW），第十代（Intel）：传感器、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、键盘背光、风扇全速（仅限自定义模式）；经 DSDT 验证为上方 83LU Q6CN 的拯救者 Pro 5 同胞机型（issue #471），真机验证进行中；详见 [83F3 说明](../FEATURES_AND_TESTING.md#legion-pro-5-16iax10-83f3-q6cn)
- 联想 LOQ 15IRX10（83JE，BIOS R3CN），第十代（Intel）：传感器、电源配置、风扇曲线（自定义模式 `powermode=255` 下通过 EC3 LOQ 接口独立设置 RPM 和温度/回差）、键盘背光、风扇全速（仅限自定义模式）。R3CN44WW 的 EC3 曲线写入已在 [#535](https://github.com/johnfanv2/LenovoLegionLinux/issues/535) 中经过负载验证；不支持的加/减速、minifancurve 和风扇控制器锁定选项已隐藏。该机型不受 WMI 风扇等级限制；详见 [R3CN 说明](../FEATURES_AND_TESTING.md#loq-15irx10-83je-r3cn)。
- 联想拯救者 Y7000P IRX10（83NN，BIOS S9CN19WW），第十代（Intel）：传感器、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、键盘背光与 Y 型 Logo 灯、风扇全速（仅限自定义模式）；经 DSDT 验证为上方 83F5 Q7CN 的纯 WMI 同胞机型（issue #506），真机验证进行中；详见 [S9CN 说明](../FEATURES_AND_TESTING.md#legion-y7000p-irx10-83nn-s9cn)
- 联想拯救者 Pro 7 16AFR10H（83RU，BIOS SMCN19WW），第十代（AMD）：传感器（含第三个风扇的转速，hwmon `fan3`）、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、风扇全速（仅限自定义模式）、即时开机；无键盘/灯光控制（每键 RGB 由 USB Spectrum 控制器驱动）；经 DSDT 验证为上方 83F5 Q7CN 的 AMD 同胞机型（issue #624），真机验证进行中；详见 [SMCN 说明](../FEATURES_AND_TESTING.md#legion-pro-7-16afr10h-83ru-smcn)
- 联想拯救者 7 15ASH11 / Legion 7a 15 英寸第十一代（83V9，BIOS UACN23WW），第十一代（AMD Ryzen AI Max+，仅集成 Radeon 显卡）：传感器（风扇转速与 CPU 温度；本机没有独立显卡，不提供 GPU 温度）、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、键盘背光、风扇全速（仅限自定义模式）、快速充电与电池养护；不提供功耗限制属性、即时开机和翻盖开机；配置基于 issue #657 中的 UACN23WW DSDT 与强制加载日志（已确认 WMI 电源模式、CPU 温度和风扇转速读取正常），最终配置的真机验证进行中；详见 [UACN 说明](../FEATURES_AND_TESTING.md#legion-7-15ash11-83v9-uacn)
- 联想拯救者 R9000P AFR10（83F6，BIOS RECN20WW），第十代（AMD）：传感器（含第三个风扇的转速，hwmon `fan3`）、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、键盘背光与 Y 型 Logo 灯、风扇全速、即时开机；经 DSDT 验证为同一 RECN BIOS 线上 Legion Pro 5 16AFR10（83F2，RECN）的同胞机型（issue #405），真机验证进行中；详见 [RECN 说明](../FEATURES_AND_TESTING.md#legion-r9000p-afr10-83f6-recn)
- 联想拯救者 Legion 5 15AKP10（83F1，BIOS RYCN27WW/RYCN28WW），第十代（AMD）：传感器、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，仅在接通电源的自定义模式下由 EC 应用）、键盘背光与 Y 型 Logo 灯、风扇全速（仅自定义模式）、即时开机、开盖开机；配置依据 RYCN28WW 的 DSDT（issue #416），真机验证进行中；详见 [RYCN 说明](../FEATURES_AND_TESTING.md#legion-5-15akp10-83f1-rycn)
- 联想拯救者 Legion 5 15IRX10（83LY，BIOS QNCN38WW），第十代（Intel）：传感器、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，两个风扇共用一张表，仅在接通电源的自定义模式下由 EC 应用）、键盘背光与 Y 型 Logo 灯、风扇全速（仅限自定义模式）、快速充电与电池养护、即时开机；GameZone WMI 设备留给 `lenovo_wmi_gamezone`，因此原生电源配置和 `lenovo-wmi-other` 功耗限制可与之共存。风扇曲线、风扇全速、电池与即时开机的写入已在 83LY 上验证（issue #491）；详见 [QNCN 说明](../FEATURES_AND_TESTING.md#legion-5-15irx10-83ly-qncn)
- 联想拯救者 7 16IRX9（83FD，BIOS NSCN37WW），第九代（Intel）：传感器、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，两个风扇共用一张表；按实时热模式写入，极限模式下拒绝写入）、风扇全速（仅限自定义模式）；已经 DSDT 验证（issue #617），风扇曲线写入已在 NSCN41WW 真机验证（issue #625）；详见 [83FD 说明](../FEATURES_AND_TESTING.md#legion-7-16irx9-83fd-nscn)
- 联想拯救者 5 16IRX9（83DG，BIOS NMCN32WW），第九代（Intel）：传感器、电源配置、通过 WMI 设置风扇曲线（1-10 等级索引，两个风扇共用一张表）、风扇全速（仅限自定义模式）
- 联想 LOQ 15APH8（82XT，BIOS LYCN50WW），第八代（AMD）：传感器、电源配置、通过 WMI 设置风扇曲线（等级索引，仅速度点）、风扇全速（仅限自定义模式）；与拯救者 R7000P APH8（82Y9，M3CN）同为 EC 0x8227 平台，支持来自 issue #602，真机验证进行中；详见 [LYCN 说明](../FEATURES_AND_TESTING.md#loq-15aph8-82xt-lycn)
- 联想 LOQ 15IAX9（83GS，BIOS NECN50WW），2024 款（Intel）：传感器、电源配置、风扇曲线（自定义模式 `powermode=255` 下通过 EC3 LOQ 接口独立设置 RPM 和温度/回差）、功耗限制（WMI3：PL1、PL2、cTGP、PPAB）、快速充电、风扇全速；EC 不支持风扇控制器锁定与 minifancurve 并已隐藏
- 联想拯救者 Y530-15ICH（81FV，BIOS 8JCN56WW），2018 款（Intel）：风扇转速、CPU/GPU 温度、风扇曲线（IdeaPad 式 EC 表，8 个点）、`fan_unlock` 即 Fn+Q 的“极速散热”开关（双风扇约 4000 RPM），可实时读回状态；该固件没有电源模式，`fan_fullspeed` 已隐藏。详见 [8JCN 说明](../FEATURES_AND_TESTING.md#legion-y530-15ich-81fv-8jcn)
- 联想 Yoga Pro 7 14AHP9（83E3，BIOS NCCN30WW），2024 款（AMD）：通过 EC 读取 CPU/GPU 温度；无风扇转速、风扇曲线、电源模式和灯光控制——该 ideapad 平台固件（EC 0x5571）不发布任何风扇/电源接口，platform profile 与电池保护模式仍由 ideapad-laptop 提供；经 DSDT 验证（issue #630）；详见 [NCCN 说明](../FEATURES_AND_TESTING.md#yoga-pro-7-14ahp9-83e3-nccn)

还支持更多机型 —— 包括 LOQ 系列以及 2024/2025 款拯救者（如 Legion 7 16IAX10）；完整列表见 [`kernel_module/legion-laptop.c`](../../kernel_module/legion-laptop.c) 中的 DMI 白名单。

*注：未确认的功能大概率也能使用，只是暂无测试。*

目前，以下型号暂不支持风扇控制，但其他功能大概率可用：

- BIOS为HACN*的Legion机型，如S7-15ACH6：[相关Issue](https://github.com/johnfanv2/LenovoLegionLinux/issues/13)
- Legion Y540
