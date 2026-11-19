> **翻译进行中**：本文件是英文原文 [FEATURES_AND_TESTING.md](../FEATURES_AND_TESTING.md) 的简体中文版，当前覆盖到「Legion Zone v3 固件上的风扇曲线（level 索引）」为止；之后章节的翻译将按文档顺序陆续补充，未覆盖部分请阅读英文原文。

## 功能与测试

## Legion Slim 5 16AHP9 (83DH, NRCN)

在 BIOS NRCN20WW、EC ID 0x8227、Debian 内核 6.12.111+deb13-amd64 上测试。

在该 BIOS 上，`WMAB` 仅支持风扇表方法 5 和 6。
全速控制使用 `WMAE` 方法 17 和 18，feature 为 `0x04020000`。
这些方法读取并写入 EC 的 `FFON` 位。

全速需要自定义模式（`powermode=255`）。在平衡模式下，固件会接受该位的变化，
但不会提高风扇转速。驱动在自定义模式之外拒绝启用请求；
在所有模式下都接受禁用请求。

验证该控制的方法：

1. 保存 `powermode` 和 `fan_fullspeed` 的当前值。
2. 把 `powermode` 设为 255，进入自定义模式。
3. 把 `fan_fullspeed` 设为 1。
4. 用 `sensors` 检查两个风扇的转速，持续至少 15 秒。
5. 恢复 `fan_fullspeed` 的保存值。
6. 恢复 `powermode` 的保存值。

将该修复应用到 v0.0.34 后，两个风扇从 3500 RPM 升到约
5000 RPM。全速读回值从 0 变为 1，并在测试结束后回到 0。
该控制不需要直接写 EC。

其他 BIOS 版本与风扇曲线写入未经测试。

在 NRCN25WW（issue #516）上，固件风扇表读出为
`1 2 3 5 6 7 8 9 10 10`，这些是转速等级（level），而不是百分比。旧版本的模块把该表当作百分比处理，
因此 GUI 发送了大于 10 的值。这很可能就是该 issue 中
`Operation not supported` 写入失败的原因。模块现在把
`fancurve_speed_unit` 报告为 `level`，并且只暴露风扇 1 的转速点。在该固件上，
minifancurve 和风扇控制器锁对应的 EC 字节保存的是其它数据，
因此模块不再读写它们。

该机型尚未验证过任何等级写入，因此在未以
`allow_unvalidated_fancurve=1` 加载模块时，风扇曲线写入会以 `EPERM` 失败。
验证写入的方法：

1. 运行 `sudo cat /sys/kernel/debug/legion/fancurve` 并保存风扇表。
2. 以 `allow_unvalidated_fancurve=1` 加载模块。
3. 通过 `legion_hwmon` 设备把某个点写到其已保存等级或以上。pwm 值会
   按 `level * 255 / 10` 取整到最近的等级，因此等级 6 对应 pwm 153：
   `echo 153 | sudo tee /sys/class/hwmon/hwmonN/pwm1_auto_point5_pwm`。
4. 再次读取风扇表，并用 `sensors` 检查风扇转速是否变化。

## 无风扇曲线支持的 GUI

在风扇曲线访问方法为 `ACCESS_METHOD_NO_ACCESS` 的机型上（例如
NCCN 固件的 Yoga Pro 7 14AHP9；以及风扇表尚未启用时的
Legion 5 15IRX10/QNCN），在模块已加载的情况下启动 `legion_gui`。确认窗口能打开、
风扇曲线的读取/应用按钮处于禁用状态，
且提示信息说明不支持自定义风扇曲线。确认
`sensors` 仍能报告风扇转速和温度。不需要进行任何风扇曲线写入。

运行 `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p
'test_gui_startup.py'` 执行启动回归测试。

## Legion Zone v3 固件上的风扇曲线（level 索引）

在 `model_kwcn`（Legion Pro 5 16IRX8，BIOS KWCN54WW）上，`Fan_Set_Table` 接收的是 0-10 的十个等级
索引，而不是百分比；`LENOVO_FAN_TABLE_DATA.FanTable_Data` 把等级 n 映射到一个
RPM 值（16IRX8 的风扇 1：1700, 1900, 2100, 2300, 2500, 2900, 3400, 3700, 4400, 5400）。
驱动使用 `FAN_SPEED_UNIT_LEVEL`（debugfs `u` = 5）：hwmon 的 pwm 0-255 按公式
`round(pwm * 10 / 255)` 映射为等级；低于各点最小值 1,1,1,1,1,1,1,1,3,5
的写入会返回 `EOPNOTSUPP`；全零（从未写入过）的风扇表会以 1..10 发送。

测试（自定义电源模式，同时运行 `stress-ng` 和 `watch sensors`）：

```bash
H=$(grep -l legion_hwmon /sys/class/hwmon/hwmon*/name | xargs dirname)
echo 255 | sudo tee $H/pwm1_auto_point10_pwm   # 等级 10
sudo cat /sys/kernel/debug/legion/fancurve      # WMI 块：u = 5，speed1 = 10
sensors                                         # 风扇 1 应达到 FanTable_Data[9]
echo 204 | sudo tee $H/pwm1_auto_point10_pwm   # 等级 8 -> FanTable_Data[7]
echo 25  | sudo tee $H/pwm1_auto_point10_pwm   # EOPNOTSUPP：点 10 的最小值是 5
```

在 Legion Pro 5 16IRX8（KWCN54WW）上实测：先用 Windows 以相同的 WMI 调用验证，然后
在 Linux 上通过本驱动的 hwmon 接口验证：进入自定义模式会向空表填入
1,2,3,4,5,6,7,8,8,8；所有点设为等级 9 时转速达到 4400 / 4600 RPM（风扇 1 / 风扇 2），等级 10 时达到
5400 / 5400 RPM，与 FanTable_Data 一致；热机时 15 秒内生效，从空闲的
2100 RPM 约需 30 秒（EC 的调速斜率约为 100 RPM/s）。DSDT 的 Fan_Set_Table 处理器会把这十个字节
复制到 EC RAM F9F0..F9F9（`ecmemoryram` 偏移 0x1F0），并忽略 FSTM/FSID/FSTL 头部，因此
`Fan_Get_Table` 读回的内容与该内存块是同一批字节。
Python 工具（`legion_cli`、`legion_gui`、`legiond` 预设）会把 RPM 映射到最近的
等级并限制在各点最小值之上；它们使用的每级 RPM 阶梯并非
硬编码，而是在运行时从平台设备的 `fan1_level_rpm_table`/`fan2_level_rpm_table` 读取，
驱动会根据当前电源模式，用固件的
`LENOVO_FAN_TABLE_DATA` WMI 数据块填充该表：

```bash
D=/sys/bus/platform/drivers/legion/legion
cat $D/fan1_level_rpm_table   # 例如 1700 1900 2100 2300 2500 2900 3400 3700 4400 5400
```

同一表格行还携带风扇的真实最大转速（`current_fan_max_speed`），
在这些机型上驱动通过 hwmon 的 `fan1_max`/`fan2_max` 报告它，而不是使用按机型硬编码的值。`fan_maxspeed`（Fan Method id 3/4）在
`model_kwcn`、`model_q7cn`、`model_rlcn` 和 `model_qncn` 上被隐藏（`skip_fan_maxspeed`）：它们的 `WMAB` 只实现了
id 5/6，所以该属性不可能工作（在 KWCN 上，读取返回无意义的 0，写入是无操作；
Q7CN/RLCN/QNCN 依据其 DSDT 推断）；`fan_control.sh` 在该属性缺失时会跳过它。
在相同 BIOS 的 Legion Pro 7 16IRX8H 上，进入模式 0xE0 时 EC 会把风扇表重置为 1..10 并
忽略后续写入（issue #429）；请使用模式 255，并在写入后检查
`/sys/kernel/debug/legion/ecmemory` 的 0x1F0..0x1F9 偏移。

---

> 之后的章节（从 “Legion Pro 7 16IAX10H (83F5, Q7CN)” 开始）尚未翻译，请参阅[英文原文](../FEATURES_AND_TESTING.md#legion-pro-7-16iax10h-83f5-q7cn)。
