#!/bin/bash
set -e

echo "MODEL"
dmidecode -s system-version
echo "BIOS"
dmidecode -s bios-version
echo ""

hwmondir=`find /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon -mindepth 1 -name "hwmon*"`
echo "Using hwmon directory: ${hwmondir}" 

# Disable (0) or Enable (1) switching to minifancurve when everything seems very cool
echo 1    > ${hwmondir}/minifancurve

# 1. Fan: Set the fan speed (rmp) of the first fan for the first 6 points (first must be 0)
# If you want more, just continue 
echo 0    > ${hwmondir}/pwm1_auto_point1_pwm
echo 1500 > ${hwmondir}/pwm1_auto_point2_pwm
echo 1900 > ${hwmondir}/pwm1_auto_point3_pwm
echo 2100 > ${hwmondir}/pwm1_auto_point4_pwm
echo 2200 > ${hwmondir}/pwm1_auto_point5_pwm
echo 2500 > ${hwmondir}/pwm1_auto_point6_pwm

# 2. Fan: Set the fan speed (rmp) of the first fan for the first 6 points; first must be 0)
# If you want more, just continue 
echo 0    > ${hwmondir}/pwm2_auto_point1_pwm
echo 1600 > ${hwmondir}/pwm2_auto_point2_pwm
echo 2000 > ${hwmondir}/pwm2_auto_point3_pwm
echo 2200 > ${hwmondir}/pwm2_auto_point4_pwm
echo 2300 > ${hwmondir}/pwm2_auto_point5_pwm
echo 2500 > ${hwmondir}/pwm2_auto_point6_pwm


# CPU lower temperature for each level for the first 6 points; first must be 0
echo 0  > ${hwmondir}/pwm1_auto_point1_temp_hyst
echo 46 > ${hwmondir}/pwm1_auto_point2_temp_hyst
echo 52 > ${hwmondir}/pwm1_auto_point3_temp_hyst
echo 56 > ${hwmondir}/pwm1_auto_point4_temp_hyst
echo 58 > ${hwmondir}/pwm1_auto_point5_temp_hyst
echo 67 > ${hwmondir}/pwm1_auto_point6_temp_hyst

# CPU upper temperature for each level for the first 6 points; 
echo 49 > ${hwmondir}/pwm1_auto_point1_temp
echo 55 > ${hwmondir}/pwm1_auto_point2_temp
echo 59 > ${hwmondir}/pwm1_auto_point3_temp
echo 63 > ${hwmondir}/pwm1_auto_point4_temp
echo 72 > ${hwmondir}/pwm1_auto_point5_temp
echo 77 > ${hwmondir}/pwm1_auto_point6_temp

# GPU lower temperature for each level for the first 6 points; first must be 0
echo 0  > ${hwmondir}/pwm2_auto_point1_temp_hyst
echo 56 > ${hwmondir}/pwm2_auto_point2_temp_hyst
echo 57 > ${hwmondir}/pwm2_auto_point3_temp_hyst
echo 58 > ${hwmondir}/pwm2_auto_point4_temp_hyst
echo 59 > ${hwmondir}/pwm2_auto_point5_temp_hyst
echo 60 > ${hwmondir}/pwm2_auto_point6_temp_hyst

# GPU upper temperature for each level for the first 6 points; 
echo 59 > ${hwmondir}/pwm2_auto_point1_temp
echo 60 > ${hwmondir}/pwm2_auto_point2_temp
echo 61 > ${hwmondir}/pwm2_auto_point3_temp
echo 62 > ${hwmondir}/pwm2_auto_point4_temp
echo 63 > ${hwmondir}/pwm2_auto_point5_temp
echo 64 > ${hwmondir}/pwm2_auto_point6_temp

# IC lower temperature for each level for the first 6 points; first must be 0
echo 0  > ${hwmondir}/pwm3_auto_point1_temp_hyst
echo 56 > ${hwmondir}/pwm3_auto_point2_temp_hyst
echo 57 > ${hwmondir}/pwm3_auto_point3_temp_hyst
echo 58 > ${hwmondir}/pwm3_auto_point4_temp_hyst
echo 59 > ${hwmondir}/pwm3_auto_point5_temp_hyst
echo 60 > ${hwmondir}/pwm3_auto_point6_temp_hyst

# IC upper temperature for each level for the first 6 points; 
echo 59 > ${hwmondir}/pwm3_auto_point1_temp
echo 60 > ${hwmondir}/pwm3_auto_point2_temp
echo 61 > ${hwmondir}/pwm3_auto_point3_temp
echo 62 > ${hwmondir}/pwm3_auto_point4_temp
echo 63 > ${hwmondir}/pwm3_auto_point5_temp
echo 64 > ${hwmondir}/pwm3_auto_point6_temp

# Acceleration time (larger = slower acceleartion) for each level for the first 6 points; 
echo 5 > ${hwmondir}/pwm1_auto_point1_accel
echo 5 > ${hwmondir}/pwm1_auto_point2_accel
echo 5 > ${hwmondir}/pwm1_auto_point3_accel
echo 4 > ${hwmondir}/pwm1_auto_point4_accel
echo 2 > ${hwmondir}/pwm1_auto_point5_accel
echo 2 > ${hwmondir}/pwm1_auto_point6_accel

# Decleration time (larger = slower acceleartion) for each level for the first 6 points; 
echo 4 > ${hwmondir}/pwm1_auto_point1_decel
echo 4 > ${hwmondir}/pwm1_auto_point2_decel
echo 4 > ${hwmondir}/pwm1_auto_point3_decel
echo 3 > ${hwmondir}/pwm1_auto_point4_decel
echo 2 > ${hwmondir}/pwm1_auto_point5_decel
echo 2 > ${hwmondir}/pwm1_auto_point6_decel

echo "Writing fancurve succesful!"
cat /sys/kernel/debug/legion/fancurve
echo "Writing fancurve succesful!"
echo "MODEL"
dmidecode -s system-version
echo "BIOS"
dmidecode -s bios-version
