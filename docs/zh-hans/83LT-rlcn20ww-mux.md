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

- `graphics_mode`：读取 `integrated`（UMA 核显）、`hybrid`（混合）或
  `discrete`（独显），写入对应字符串请求下一次启动的模式。读取时使用
  BIOS `Setup` 偏移 `0x259`，避免一位宽的 EC `MSMF` 将 UMA 误判为混合。
- 原有 `gsync` 保留项目历史的 **Hybrid 布尔语义**：`1` = 混合，
  `0` = 独显；无法表达第三种 UMA 模式，进入 UMA 后读取会返回
  `-EOPNOTSUPP`，而不是错误地报告独显。
- 必须同时设置模块参数 `allow_rlcn20_mux_write=1` 和
  `ec_readonly=0` 才允许写入；**默认禁止**，其他 BIOS/机型不启用。
- **核显请求还必须额外开启 `allow_rlcn20_uma_write=1`**（默认关闭）。
  该路径通过 Linux EFI 变量接口设置固件待处理请求 `AppMuxSwitchModeChange`
  的模式字节 `0`，不直接写 SMI 端口；保留原变量首字节，变量不存在时
  以零初始化。三态 EFI 接口需要 Linux 6.3 或更新内核；较旧内核仍采用
  原来的二态 WMI 读取，并拒绝 UMA 请求。固件 DXE 在目标模式已经生效、
  或 `Setup+0x25c`（`IsS4Resume`）为 `1` 时会清除请求、跳过切换。
  SMM 使用特权 SMM 变量协议，而 Linux 使用 EFI Runtime Services；
  如果固件变量策略限制运行时写入，即使 SMM 路径可用，Linux 写入仍可能被拒绝。
  **尚未完成 UMA 重启实测。**
  BIOS 明确警告 UMA 可能导致 HDMI / Type-C 无显示，启用前务必确认
  物理内屏和 BIOS 恢复手段。
- Hybrid/Discrete 请求使用 GameZone MOF 指定的四字节 `UINT32`，验证
  WMI 整数 0 回执；UMA 则使用上述单独的 EFI 变量接口。
  即使 `MSMF` 已报告目标模式，也会转发显式请求，因为待生效的 EFI
  请求可能不同于当前模式。
- GameZone WMI 由内核主线 `lenovo-wmi-gamezone` 接管，避免与平台
  性能模式和固件属性驱动争用。

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
`hybrid` 或 `discrete` 请求下一次启动的模式。未经验证的核显请求还须在
加载模块时额外开启 `allow_rlcn20_uma_write=1`，再写入 `integrated`。
**必须重启**，固件可能再重启一次。请按 GPU PCI 身份与 eDP 连接状态核对，
而非依赖易变化的
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
