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

`WMAA(0x2A)` **无条件返回 ACPI 整数 0**，因此返回成功不代表 MUX 已经
切换。目前尚未定位最后的物理 eDP GPIO/路由；另一套
`SetIGPUModeStatus` 是独立的 iGPU 策略接口，不能与本功能混为一谈。

## Linux 接口与安全限制

- `graphics_mode`：读取 `hybrid` 或 `discrete`，写入对应字符串请求
  下一次启动的模式。
- 原有 `gsync` 保留项目历史的 **Hybrid 布尔语义**：`1` = 混合，
  `0` = 独显；两者的写操作共用相同安全保护。
- 必须同时设置模块参数 `allow_rlcn20_mux_write=1` 和
  `ec_readonly=0` 才允许写入；**默认禁止**，其他 BIOS/机型不启用。
- 写入使用 GameZone MOF 指定的四字节 `UINT32`，验证 WMI 整数 0 回执。
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
`hybrid` 或 `discrete` 请求下一次启动的模式。**必须重启**，固件可能
再重启一次。请按 GPU PCI 身份与 eDP 连接状态核对，而非依赖易变化的
`card0/card1` 编号。不要直接尝试 SMI/EC 端口写入。

**验证状态：**83LT/RLCN20WW 已确认只读查询在 `discrete` 模式下可用；
受保护的**写入及重启后模式往返测试尚未完成**，测试前应准备 BIOS 回退。
原有机型支持讨论见 issue #445。
