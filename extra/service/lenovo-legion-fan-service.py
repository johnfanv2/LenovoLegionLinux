import os
from os.path import exists 
import psutil
import fnmatch
import argparse

class fan_profile:
    fan1_rpm = []
    fan2_rpm = []
    cpu_min_temp= [] 
    cpu_max_temp= [] 
    gpu_min_temp= [] 
    gpu_max_temp= [] 
    ic_min_temp= [] 
    ic_max_temp= [] 
    acceleration = []
    deceleration = []

hwmon_dir = ""
profile_mode= ""

def find_hwmondir():
    global hwmon_dir 
    if os.path.exists("/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/") == True:
        for file in os.listdir("/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/"):

            if "hwmon" in file:
                hwmon_dir = "/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/" + file + "/"
                print("found hwmon dir at", hwmon_dir)
            else:
                print("hwmon directory not found, is the module loaded?")
    else:
        print("Can't find the hwmon path, is everything correct")



def parse_def_config(fan_profile):
    #fan1
    for i in range(1,11):
        file="pwm1_auto_point{}_pwm".format(i)
        fan_profile.fan1_rpm.append(valueof(file))

    #fan2
    for i in range(1,11):
        file="pwm2_auto_point{}_pwm".format(i)
        fan_profile.fan2_rpm.append(valueof(file))

    #cpu_min_temp
    for i in range(1,11):
        file="pwm1_auto_point{}_temp_hyst".format(i)
        fan_profile.cpu_min_temp.append(valueof(file))

    #cpu_max_temp
    for i in range(1,11):
        file="pwm1_auto_point{}_temp".format(i)
        fan_profile.cpu_max_temp.append(valueof(file))

    #gpu_min_temp
    for i in range(1,11):
        file="pwm2_auto_point{}_temp_hyst".format(i)
        fan_profile.gpu_min_temp.append(valueof(file))

    #gpu_max_temp
    for i in range(1,11):
        file="pwm2_auto_point{}_temp".format(i)
        fan_profile.gpu_max_temp.append(valueof(file))

    #ic_min_temp
    for i in range(1,11):
        file="pwm3_auto_point{}_temp_hyst".format(i)
        fan_profile.ic_min_temp.append(valueof(file))

    #ic_max_temp
    for i in range(1,11):
        file="pwm3_auto_point{}_temp".format(i)
        fan_profile.ic_max_temp.append(valueof(file))

    #acceleration
    for i in range(1,11):
        file="pwm1_auto_point{}_accel".format(i)
        fan_profile.acceleration.append(valueof(file))

    #deceleration
    for i in range(1,11):
        file="pwm1_auto_point{}_decel".format(i)
        fan_profile.deceleration.append(valueof(file))

    print("default profile parsed")


def store_profile(profile,name):
    path = "/etc/lenovo-fan-control/" + "legion-profile-{}".format(name)                
    if os.path.exists(path) == False:
        print("no file")
        print("creating file...")
        deffancurve = open(path, "x")

        tmplist=[]
        for list in dir(profile):
            if not list.startswith('__'):

                tmplist = getattr(profile,list)
                deffancurve.write("#{}\n".format(list))

                for element in tmplist:
                    deffancurve.write(element)
    else: 
        print("File already exists")


def parse_custom_profile(path,profile):
    file=open(path,'r')
    for line in file:
        if line.startswith("#"):
            if "Fan" in line or "fan" in line:
                print("fan in line")
                if "1" in line:
                    #advance 1 line
                    for i in range(10):
                        line = file.readline()
                        profile.fan1_rpm.append(line)
                
                    continue

                elif "2" in line:
                    for i in range(10):
                        line = file.readline()
                        profile.fan2_rpm.append(line)

                    continue

            elif "Acc" in line or "acc" in line:
                print(line)
                for i in range(10):
                    line = file.readline()
                    profile.acceleration.append(line)

                continue 

            elif "dec" in line or "Dec" in line:
                for i in range(10):
                    line = file.readline()
                    profile.deceleration.append(line)
                
                continue

            elif "gpu" in line or "GPU" in line or "Gpu" in line:
                if "low" in line or "Low" in line or "min" in line or "Min" in line:
                    for i in range(10):
                        line = file.readline()
                        profile.gpu_min_temp.append(line)
                    
                    continue

                elif "Up" in line or "up" in line or "Max" in line or "max" in line:
                    for i in range(10):
                        line = file.readline()
                        profile.gpu_max_temp.append(line)
                    
                    continue

            elif "cpu" in line or "CPU" in line or "Cpu" in line:
                if "low" in line or "Low" in line or "min" in line or "Min" in line:
                    for i in range(10):
                        line = file.readline()
                        profile.cpu_min_temp.append(line)
                    continue

                elif "Up" in line or "up" in line or "Max" in line or "max" in line:
                    for i in range(10):
                        line = file.readline()
                        profile.cpu_max_temp.append(line)
                    continue

            elif "ic" in line or "Ic" in line or "IC" in line:
                if "low" in line or "Low" in line or "min" in line or "Min" in line:
                    for i in range(10):
                        line = file.readline()
                        profile.ic_min_temp.append(line)
                    continue

                elif "Up" in line or "up" in line or "Max" in line or "max" in line: 
                    for i in range(10):
                        line = file.readline()
                        profile.ic_max_temp.append(line)
                    continue
    print("profile parsed")



def is_default_stored():
    global profile_mode

    f = open("/sys/firmware/acpi/platform_profile","r")
    profile_mode = f.readline()[:-1]
    path="/etc/lenovo-fan-control/" + "legion-profile-default-" + profile_mode
    if os.path.exists(path) == False:
        print("saving profile {}".format(profile_mode))
        return 0
    else:
        print("profile {} already stored".format(profile_mode))
        return 1

def valueof(file):
    f = open(hwmon_dir + file, "r")
    value = f.read(2048)
    return value

def openabs(file):
    f = open(hwmon_dir + file, "w")
    return f


def apply_profile_default(fan_profile):
    apply_profile(default)

def apply_profile(fan_profile):
    #traverse fan.rpm 
    #write first value to pwm1_auto_point{i}_pwm
    #advance
    i=1

    for element in fan_profile.fan1_rpm:
        file = openabs("pwm1_auto_point{}_pwm".format(i))
        file.write(element)
        i=i+1
        file.close()

    i=1

    for element in fan_profile.fan2_rpm:
        file = openabs("pwm2_auto_point{}_pwm".format(i))
        file.write(element)
        i=i+1
        file.close()

    i=1

    for element in fan_profile.cpu_min_temp:
        file = openabs("pwm1_auto_point{}_temp_hyst".format(i))
        file.write(element)
        i=i+1
        file.close()

    i=1

    for element in fan_profile.cpu_max_temp:
        file = openabs("pwm1_auto_point{}_temp".format(i))
        file.write(element)
        i=i+1
        file.close()

    i=1

    for element in fan_profile.gpu_min_temp:
        file = openabs("pwm2_auto_point{}_temp_hyst".format(i))
        file.write(element)
        i=i+1
        file.close()

    i=1

    for element in fan_profile.gpu_max_temp:
        file = openabs("pwm2_auto_point{}_temp".format(i))
        file.write(element)
        i=i+1
        file.close()

    i=1

    for element in fan_profile.ic_min_temp:
        file = openabs("pwm3_auto_point{}_temp_hyst".format(i))
        file.write(element)
        i=i+1
        file.close()

    i=1

    for element in fan_profile.ic_max_temp:
        file = openabs("pwm3_auto_point{}_temp".format(i))
        file.write(element)
        i=i+1
        file.close()

    i=1

    for element in fan_profile.acceleration:
        file = openabs("pwm1_auto_point{}_accel".format(i))
        file.write(element)
        i=i+1
        file.close()

    i=1

    for element in fan_profile.deceleration:
        file = openabs("pwm1_auto_point{}_decel".format(i))
        file.write(element)
        i=i+1
        file.close()


    print("fan profile applied")



find_hwmondir()
default = fan_profile()

if is_default_stored() == 0:
    parse_def_config(default)
    name = "default-" + profile_mode
    store_profile(default,name)

####


custom=fan_profile()

argParser = argparse.ArgumentParser()
argParser.add_argument("-i", "--input", help="profile to load")


args = argParser.parse_args()

input_abs=os.path.abspath(args.input)

print("parsing " + input_abs)

parse_custom_profile(input_abs, custom)


apply_profile(custom)
