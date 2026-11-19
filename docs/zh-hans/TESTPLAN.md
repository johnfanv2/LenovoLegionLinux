# 测试计划

## 测试
完成[初次使用测试](initial-testing.md)中的测试，以及以下测试：

### 测试：从 hwmon 接口读取传感器数值
先用繁琐的方式读取一次，以确认一切安装正常：
```bash
# 先用繁琐的方式读取传感器（只需做一次 :))
# 读取当前 CPU 温度：输出为 温度*1000
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/temp1_input
# 读取当前 GPU 温度：输出为 温度*1000
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/temp2_input
# 读取当前 IC 温度：输出为 温度*1000
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/temp3_input
# 读取风扇 1 的转速（RPM）
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/fan1_input
# 读取风扇 2 的转速（RPM）
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/fan2_input
```

不符合预期：
    - 什么都没有显示：内核模块没有正确加载，回到第一个测试
    - 温度为 0
    - 风扇开启时转速为 0
符合预期：
    - 如果 GPU 处于深度休眠，其报告的温度为 0；在 GPU 上运行一些任务再测试
    - 输出 `hwmon` 温度值时，数值是温度乘以 1000
    - 温度有效，特别是不为 0（GPU 除外，见上）
    - 风扇转速有效：风扇关闭时为 0，否则应大于 1000 rpm
    - `sensors` 的输出包含类似如下内容
```text
legion_hwmon-isa-0000
Adapter: ISA adapter
Fan 1:           1737 RPM
Fan 2:           1921 RPM
CPU Temperature:  +42.0°C
GPU Temperature:   +30.0°C
IC Temperature:   +41.0°C
```

### 测试：用 hwmon 从硬件读取当前风扇曲线
```bash
# 显示风扇 1 所有等级的风扇转速
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_pwm
# 显示风扇 2 所有等级的风扇转速
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm2_auto_point*_pwm

# 显示所有等级的 CPU 温度上限
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_temp
# 显示所有等级的 CPU 温度下限
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_temp_hyst

# 显示所有等级的 GPU 温度上限
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm2_auto_point*_temp
# 显示所有等级的 GPU 温度下限
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm2_auto_point*_temp_hyst

# 显示所有等级的 IC 温度上限
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm3_auto_point*_temp
# 显示所有等级的 IC 温度下限
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm3_auto_point*_temp_hyst


# 显示所有等级的风扇加速时间与减速时间
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_accel
# 显示所有等级的风扇减速时间
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_decel
# 显示等级数量
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/auto_points_size
```
