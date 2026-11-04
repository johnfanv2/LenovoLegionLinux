# 初次使用测试

请注意：

- 请按给定顺序测试；在继续下一个之前请先尝试修复失败的测试。
- 这些测试需在终端中手动进行。
- 你可以复制并粘贴命令。在终端内使用 `Ctrl+Shift+V` 粘贴。

## 快速测试：模块是否正确加载

```bash
# 在 LenovoLegionLinux/kernel_module 目录下（非 DKMS 方式）
sudo make reloadmodule 

# 检查内核日志
sudo dmesg
```

预期结果：

- 你应该看到类似 `legion PNP0C09:00: legion_laptop loaded for this device` 的日志信息。`PNP0C09` 可能会被其他文本替换。

非预期结果：

- 执行 `make reloadmodule` 后出现 `insmod: ERROR: could not insert module legion-laptop.ko: Invalid module format`
- 日志中出现 `legion PNP0C09:00: legion_laptop not loaded for this device`。说明内核模块未能正确加载，请重新执行第一次测试。
- 出现 `insmod: ERROR: could not insert module legion-laptop.ko: Key was rejected by service`：因为你开启了安全启动，无法加载内核模块。请在 BIOS 里禁用安全启动，或用私钥签名内核模块。
- 如果看到如下内容，说明该驱动未针对你的笔记本型号测试过；如果你觉得应该兼容，请向维护者反馈。如果你仍想在你的型号上尝试，可以使用 `sudo make forcereloadmodule` 强制加载模块。

```text
[126675.495983] legion PNP0C09:00: Module not usable for this laptop because it is not in allowlist. Notify maintainer if you want to add your device or force load with param force.
[126675.495984] legion PNP0C09:00: legion_laptop not loaded for this device
[126675.496014] legion: probe of PNP0C09:00 failed with error -12
```

## 快速测试：读取当前硬件风扇曲线

```bash
# 读取当前风扇曲线及其他调试输出
sudo cat /sys/kernel/debug/legion/fancurve
```

预期输出：

- EC chip ID 应为 8227
- “fan curve points” 的 size 不能为 0
- 显示当前风扇曲线的表格内不能全为 0，实际数值可能会不同
- “fan curve current point id” 和 “EC Chip Version” 可能与示例不同

示例：

```text
EC Chip ID: 8227 
EC Chip Version: 2a4 
fan curve current point id: 0 
fan curve points size: 8 
Current fan curve in UEFI
u(speed_of_unit)|speed1[u]|speed2[u]|speed1[pwm]|speed2[pwm]|acceleration|deceleration|cpu_min_temp|cpu_max_temp|gpu_min_temp|gpu_max_temp|ic_min_temp|ic_max_temp
3        0       0       0       0       3       3       0       50      0       50      0       30
3        11      11      28      28      3       3       50      55      50      55      30      40
3        13      13      33      33      3       3       55      60      55      60      40      50
3        20      20      51      51      3       3       60      65      60      65      50      55
3        22      22      56      56      3       3       65      70      65      70      55      127
3        24      24      61      61      3       3       70      75      70      75      127     127
3        28      28      71      71      2       2       75      80      75      80      127     127
3        33      33      84      84      2       2       80      88      80      88      127     127
3        40      40      102     102     2       2       88      90      88      90      127     127
3        44      44      112     112     2       2       90      127     90      127     127     127

```

风扇曲线以表格形式展示，列说明如下：

```text
u(speed_of_unit): 风扇速度的单位（1-百分比, 2-PWM, 3-RPM/100, 4-百分比、四舍五入, 5-固件风扇表等级索引 0-10）
speed1[u]: fan1 在该点的速度（单位由 u 决定）
speed2[u]: fan2 在该点的速度（单位由 u 决定）
speed1[pwm]: fan1 在该点的 pwm（0-255）
speed2[pwm]: fan2 在该点的 pwm（0-255）
acceleration: 加速时间（数值越大越慢）
deceleration: 减速时间（数值越大越慢）
cpu_min_temp: CPU 必须低于该温度才能离开此点
cpu_max_temp: CPU 高于此温度则跳到下一个点
gpu_min_temp: GPU 必须低于该温度才能离开此点
gpu_max_temp: GPU 高于此温度则跳到下一个点
ic_min_temp: IC 必须低于该温度才能离开此点
ic_max_temp: IC 高于此温度则跳到下一个点

所有温度单位为摄氏度。
127 为最大温度
```

**注意**：这只是调试输出。风扇曲线的配置仍然通过标准的 `hwmon` 接口进行。

异常情况：

- `/sys/kernel/debug/legion/fancurve: No such file or directory`：内核模块未正确加载
- `cat: /sys/kernel/debug/legion/fancurve: Permission denied`：你忘记加 sudo

## 快速测试：读取硬件传感器数值

- 显示传感器数值，并检查是否包含 “Fan 1”、 “Fan 2”、 “CPU Temperature”、 “GPU Temperature” 的相关行：

```bash
# 运行命令 sensors
sensors
```

- 显示传感器数值
- 增加 CPU 负载，并检查：
  - 显示的 CPU 温度是否升高
  - 显示的风扇转速是否升高
- 再次显示传感器数值
- 增加 GPU 负载，并检查 GPU 温度是否变化
  - 显示的 CPU 温度是否升高
  - 显示的风扇转速是否升高

预期输出：

- `sensors` 命令的输出应包含如下内容：

  ```text
  legion_hwmon-isa-0000
  Adapter: ISA adapter
  Fan 1:           1737 RPM
  Fan 2:           1921 RPM
  CPU Temperature:  +42.0°C  
  GPU Temperature:  +30.0°C  
  IC Temperature:   +41.0°C  
  ```
- 如果 GPU 处于深度休眠，其温度会显示为 0；可以运行一些 GPU 程序来测试
- 温度应为有效值：特别是不能为 0（除了 GPU，上述情况除外）
- 风扇转速应为有效值：风扇停止时为 0，否则应大于 1000 rpm
- 温度与风扇转速应根据负载变化而上升

异常输出：

- `Command 'sensors' not found`：请通过安装 `lm-sensors` 软件包获取 `sensors` 命令
- 没有 “Fan 1”、 “Fan 2” 等条目显示。说明内核模块未正确加载，请重新执行第一次测试。

---

## 快速测试：通过 hwmon 更改当前硬件风扇曲线

```bash
# 将风扇曲线第二、第三个点的风扇转速分别设置为 1500 rpm、1600 rpm、1700 rpm、1800 rpm。
# 获取 root 权限
sudo su
# 以 root 身份输入：
# hwmon 目录名随内核版本变化（7.0 之前为 PNP0C09:00，7.0+ 为 legion），通过 hwmon 名称定位：
H=$(grep -l legion_hwmon /sys/class/hwmon/hwmon*/name | xargs dirname)
# 第2点，第1风扇（大约 1500 rpm 的 pwm 值）
echo 38 > $H/pwm1_auto_point2_pwm
# 第2点，第2风扇（大约 1600 rpm 的 pwm 值）
echo 40 > $H/pwm2_auto_point2_pwm
# 第3点，第1风扇（大约 1700 rpm 的 pwm 值）
echo 43 > $H/pwm1_auto_point3_pwm
# 第3点，第2风扇（大约 1800 rpm 的 pwm 值）
echo 45 > $H/pwm2_auto_point3_pwm

# 读取当前风扇曲线并检查更改是否生效
cat /sys/kernel/debug/legion/fancurve
```

预期结果：

- 如果你按下 Ctrl+Q（或某些设备的 FN+Q）更改电源模式，或等待时间过长，控制器可能会加载默认值；此时请重试
- 风扇曲线中的对应条目值应被设置为你输入的数值，其它值不相关（用 XXXX 表示）
- 在 Legion Zone v3 固件上（例如 Legion Pro 5 16IRX8，BIOS KWCN），风扇表保存的是 0-10 的风扇等级（`u` = 5）：写入的 pwm 会四舍五入到最近的等级（写入 0、26、51 … 255），读回时为 `level * 255 / 10`（0、25、51、76、102、127、153、178、204、229、255）；第 9、10 点至少需要 pwm 64 和 115，低于某点最小值的写入会返回 `Operation not supported`。在这些机型上，Python 工具（`legion_cli`、`legion_gui` 以及 `legiond` 预设）会把 RPM 值转换为最接近的固件等级（例如 4400 rpm → 9 级），并把 0 rpm 的点提升到该点的最低等级，因此现有预设仍可使用。转换所用的每级 RPM 阶梯在运行时从驱动提供的 `fan1_level_rpm_table`/`fan2_level_rpm_table` 平台属性读取（由固件的 `LENOVO_FAN_TABLE_DATA` WMI 数据块填充），并非硬编码。这些机型（KWCN、Q7CN、RLCN、QNCN）不会暴露 `fan_maxspeed`（Fan Method 3/4 号方法）：固件未实现这两个方法，该属性无法工作（在 KWCN 上读取只得到无意义的 0）；`fan_control.sh` 在该属性不存在时会跳过它

```
u(speed_of_unit)|speed1[u]|speed2[u]|speed1[pwm]|speed2[pwm]|acceleration|deceleration|cpu_min_temp|cpu_max_temp|gpu_min_temp|gpu_max_temp|ic_min_temp|ic_max_temp
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             15        16        38          40          XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             17        18        43          45          XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX

```

**如果你想重置风扇曲线，只需按 Ctrl+Q 或 Fn+Q 切换电源模式，或重启即可恢复。**

异常情况：

- `file not found`：请在 Github 提交 issue 报告你的问题
- 数值没有变化
- 读到的数值与预期不同

## 快速测试：设置自定义风扇曲线

使用提供的脚本设置自定义风扇曲线。参见[使用脚本创建并设置自定义风扇曲线](usage.md#使用脚本创建并设置自定义风扇曲线)。

## 测试：结束

- 如果你对测试结果满意，可以永久安装内核模块（见[永久安装说明](installation.md#永久安装说明)）。
- 无论测试成功还是失败，请创建一个 GitHub Issue 进行反馈。
  - 请务必注明你的笔记本电脑型号
  - 如果出现错误，请附上命令的输出结果
- 你也可以为本仓库点个星
