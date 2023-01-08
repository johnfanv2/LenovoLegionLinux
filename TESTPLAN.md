# Testplan

## Tests
Perform tests from README.md and the following:


### Test: Read Sensor Values from hwmon interface
First try it the tedious way not make sure it is installed properly:
```bash
# First read sensors the tedious way (only once :))
# Read current CPU temperature: Output is temperature*1000
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/temp1_input
# Read current GPU temperature: Output is temperature*1000
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/temp2_input
# Read current IC temperature: Output is temperature*1000
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/temp3_input
# Read fan speed in RPM of fan 1
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/fan1_input
# Read fan speed in RPM of fan 2
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/fan2_input
```

Unexpected:
    - Nothing is displayed: Kernel module was not loaded properly, go to first test
    - temperature is 0
    - fan speed is 0 if fan is on
Expected:
    - if GPU is in deep sleep, its reported temperature is 0; run something on the GPU to test it
    - when outputting `hwmon` temperature value, the temperature is multiplied by 1000
    - temperatures are valid, in particular not 0 (except GPU see above)
    - fan speeds are valid: if fan is off it is 0, otherwise greater than 1000 rpm
    - Output of `sensors` contains something like
```text
legion_hwmon-isa-0000
Adapter: ISA adapter
Fan 1:           1737 RPM
Fan 2:           1921 RPM
CPU Temperature:  +42.0°C  
GPU Temperature:   +30.0°C  
IC Temperature:   +41.0°C  
```


### Test: Read Current Fancurve from Hardware with hwmon
```bash
# Display fan speeds of fan 1 for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_pwm
# Display fan speeds of fan 2 for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm2_auto_point*_pwm

# Display CPU upper temperature levels for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_temp
# Display CPU lower temperature for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_temp_hyst

# Display GPU upper temperature levels for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm2_auto_point*_temp
# Display GPU lower temperature for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm2_auto_point*_temp_hyst

# Display IC upper temperature levels for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm3_auto_point*_temp
# Display IC lower temperature for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm3_auto_point*_temp_hyst


# Display accelleration times for all levelsdecleration times for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_accel
# Display decleration times for all levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/pwm1_auto_point*_decel
# Display number of levels
sudo cat /sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/hwmon/hwmon*/auto_points_size
```

