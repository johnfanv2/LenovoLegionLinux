# Legion Pro 5 16ADR10（83LT）/ RLCN20WW 显卡模式请求

此功能仍为**实验性适配**，仅在 DMI 型号为 `83LT` 且 BIOS **恰好为
`RLCN20WW`** 时启用。它请求下一次固件启动所采用的 GPU 模式，
**不会在当前 Linux 会话中即时切换 eDP 物理连接**。

## 固件分析依据

通过实机 DSDT 和联想官方 RLCN20WW BIOS 镜像的静态逆向，确认如下调用链：

1. GameZone WMI `WMAA(0x28)` 返回能力值 `2`；`WMAA(0x29)` 读取 EC
   的 `MSMF`，反映当前报告的显卡模式。
2. `SetGSyncStatus(0)` 触发软件 SMI `0xCA`，子命令 `0x25`（混合）；
   `SetGSyncStatus(1)` 触发 `0xCA/0x26`（独显）。
3. `ChgBootSmm`（FFS GUID `4CA0062A-66FE-4BE7-ACE6-FDE992C1C5EC`）
   注册 `0xCA`，并写入两字节的 EFI 变量 `AppMuxSwitchModeChange`
   （GUID `6ACCE65D-DA35-4B39-B64B-5ED927A7DC7E`）。
   `0x25` 使变量第二字节为 `4`，`0x26` 使它为 `1`。
4. 随后的 DXE 启动阶段，`AppSwitchDisplayModeDxe` 消费请求，修改
   `Setup`、`AMD_PBS_SETUP`、`AmdSetupRPL`，同步 AMD 平台配置，
   必要时再次调用 `ResetSystem(EfiResetCold)`。

此外，从 BIOS `SetupUtility` 的 HII/IFR 菜单确认，`Graphics Device` 位于
`Setup` 偏移 `0x259`，有三个取值：`UMA Graphics = 0`（仅核显）、
`Discrete Graphics = 1`、`Dynamic Graphics = 4`（默认混合）。`ChgBootSmm`
还支持 `0xCA/0x24`，将 `AppMuxSwitchModeChange` 的第二字节设为 `0`。
不过，本机的 `SetGSyncStatus` WMI 方法并没有调用该命令的第三个参数，
传入 `2` 不能请求 UMA 模式。

`WMAA(0x2A)` **无条件返回 ACPI 整数 0**，因此返回成功不代表 MUX 已经
切换。实机已通过重启前后的 PCI/DRM 信息确认内屏 eDP 路由确实变化，
但尚未逆向定位底层 MUX GPIO/寄存器；另一套
`SetIGPUModeStatus` 是独立的 iGPU 策略接口，不能与本功能混为一谈。

## Linux 接口与安全限制

- `graphics_mode` 读取 BIOS `Setup` 偏移 `0x259`，返回 `integrated`、
  `hybrid` 或 `discrete`。读取需要 Linux 6.3 或更新版本以及可访问的 EFI
  运行时变量；否则返回错误，不从一位宽的 WMI 状态猜测。只支持请求
  `hybrid` 和 `discrete`，不支持写入 `integrated`。
- 原有 `gsync` 保留历史的 Hybrid 布尔语义（`1` = 混合，`0` = 独显）。
  EFI 读取识别出 UMA 时返回 `-EOPNOTSUPP`；EFI 读取不可用时为兼容旧版
  回退到原有 WMI 读取，此时无法区分 UMA，不能视为可靠的三态状态。
- 写入必须设置 `allow_rlcn20_mux_write=1` 和 `ec_readonly=0`，默认禁止。
  Hybrid/Discrete 请求使用四字节 `UINT32`，验证 WMI 整数 0 回执；即使
  当前模式相同也会转发请求，因为待生效的请求可能不同。
- 不实现 UMA 写入：直接写 EFI 变量尚未经过实机验证。所有 RLCN 固件的
  原有 GameZone 绑定行为保持不变。

只读检查：

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

显式重新加载模块并开启上述写入权限后，可以向 `graphics_mode` 写入
`hybrid` 或 `discrete` 请求下一次启动的模式。**必须重启**，固件可能再
重启一次。请按 GPU PCI 身份与 eDP 连接状态核对，而非依赖易变化的
`card0/card1` 编号。不要直接尝试 SMI/EC 端口写入。

**验证状态（83LT/RLCN20WW，2026-11-08）：** 已在一台实机完成受保护写入、
重启及模式往返测试：

- 显式开启写入保护开关后，请求 `hybrid` 成功。重启后 AMD Radeon 610M
  （`1002:164e`，`05:00.0`）枚举为 VGA，由 `amdgpu` 驱动，内屏连接到 AMD
  的 `card0-eDP-1`；NVIDIA（`10de:2d58`）仍正常枚举。
- 随后一次性安全定时器读取 `Current mode: hybrid`，证实 WMI 状态读取与
  AMD 的实际 eDP 路由一致，然后请求 `discrete` 并重启。
  再次启动后 AMD `05:00.0` 为 PCI Dummy Function（`1022:14de`），
  NVIDIA 接管内屏 eDP。
- 临时自动回退定时器、服务已经清理；每次请求后均恢复驱动的默认只读保护。

这证实 **RLCN20WW 启动阶段 Hybrid ↔ Discrete 双向显示路由切换**；
**UMA 核显请求尚未实机写入或重启验证**，也不代表运行时无重启切换、
不保证其他 BIOS 版本兼容。原有机型讨论见 issue #445。
