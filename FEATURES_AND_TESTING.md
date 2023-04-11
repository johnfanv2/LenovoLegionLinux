## Features and Testing

## External HDMI
Usually attached to dGPU. So easiest way to make it work is enabling dGPU only in BIOS/UEFI. More advanced would
be switching in hybrid mode to dGPU only as long as HDMI is attached or outputting via dGPU.

## Flip to Start

cat  /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c | hexdump -C

Stored in 4-byte UEFI variables FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c
```bash

sudo chattr -i /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c
# first 4 bytes are attributes
printf '\x07\x00\x00\x00\x01\x00\x00\x00' | sudo tee /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c 
cat  /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c | hexdump -C

cat  /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c | hexdump -C
# 00000000  07 00 00 00 00 00 00 00 
# 07 = EFI_VARIABLE_NON_VOLATILE | EFI_VARIABLE_BOOTSERVICE_ACCESS | EFI_VARIABLE_RUNTIME_ACCESS
#

/efi/vars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c/size
# 0x04
sudo cat /sys/firmware/efi/vars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c/data | hexdump -C
# 0000000 0000 0000    

# first byte: 1 => enabled
# first byte: 0 => diabled

# enables it
sudo chattr -i /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c
# first 4 bytes are attributes
printf '\x07\x00\x00\x00\x01\x00\x00\x00' | sudo tee /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c 
cat  /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c | hexdump -C

# disable it
sudo chattr -i /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c
# first 4 bytes are attributes
printf '\x07\x00\x00\x00\x00\x00\x00\x00' | sudo tee /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c 
cat  /sys/firmware/efi/efivars/FBSWIF-d743491e-f484-4952-a87d-8d5dd189b70c | hexdump -C
```

```
#should be y
cat /boot/config-$(uname -r) | grep CONFIG_EFI=y
# should be rw
mount | grep efivars
```

### Fn-Lock
- using secondary (special) functions of Fn keys
- works as intended, pressing it toggles the light in the Fn-Lock key
    - light off: 
        - F1, F2, ... is triggered when F key is pressed while Fn-key is not pressed
        - Special functions (increase volume, ...) is triggered when F key is pressed while Fn-key is pressed
    - light on: 
        - F1, F2, ... is triggered when F key is pressed while Fn-key is pressed
        - Special functions (increase volume, ...) is triggered when F key is pressed while Fn-key is not pressed
    - controllable by software with ideapad_acpi
```bash
# 1: enabled
# 0: disabled
# read
cat /sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/fn_lock
echo 1 > /sys/bus/platform/drivers/ideapad_acpi/VPC2004:00/fn_lock
# set with software
```
- test: toggle by pressing button and activate
    - expected: read via software returns 1
- test: toggle by pressing button and deactivate
    - expected: read via software returns 0
- test: enable with software
    - expected: LED indicator turns on; one does not have to hold down Fn to use special functions (test with mute/unmute)

```bash
sudo apt-get install acpid
acpi_listen
# When pressing Fn-Lock
# 8FC0DE0C-B4E4- 000000d0 00000000
# 1E3391A1-2C89- 000000e8 00000000
# When pressing Fn+Q (power switch)
# D320289E-8FEA- 000000e3 00000000
# D320289E-8FEA- 000000e7 00000000
```

### Touchpad


### Rapid Charge
```bash
# Enable
echo '\_SB.PCI0.LPC0.EC0.VPC0.SBMC 0x07' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'

# Distable
echo '\_SB.PCI0.LPC0.EC0.VPC0.SBMC 0x08' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'

```

### Keyboard backlight (white)
#### WMI
```text
WMI
GUID: 8C5B9127-ECD4-4657-980F-851019F99CA5
Object ID: BA

Getting state
Method ID: 0x1

Setting state
Method ID: 0x2
```

#### Test of WMI via acpi_call
```bash
# Get current state
echo '\_SB.GZFD.WMBA 0 0x1 0' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'
{0x00, 0x01}

# Set current state
echo '\_SB.GZFD.WMBA 0 0x2 {0, 0x01, 0x03}' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'
0x0
```

### GSync
```text
WMI
GUID: 887B54E3-DDDC-4B2C-8B88-68A26A8835D0
Object ID: AA

Getting state
Method ID: 0x29
Args: None
Returns: integer
- 0: enabled
- 1: not enabled

Setting state
Method ID: 0x2A
Args: Buffer of u8
Returns: integer
- 0: enabled
- 1: not enabled
```

### Other to reverse enginner yet
```c
#define WMI_METHOD_ID_GSYNCSTATUSGET 0x29 
#define WMI_METHOD_ID_GSYNCSTATUSSET 0x2A

#define WMI_METHOD_ID_IGPUMODESTATUSGET 0x0
#define WMI_METHOD_ID_IGPUMODESTATUSSET 0x0
enum IGPUState{
	IGPUState_default=0,
	IGPUState_iGPUOnly=1,
	IGPUState_auto=2
};

// overdrive
// ODStatusGet, ODStatusSet
// IsSupportOD
#define WMI_METHOD_ID_ODSTATUSGET 0x0
#define WMI_METHOD_ID_ODSTATUSSET 0x0
// 0=off, 1=on
enum ODState{
	ODState_off=0,
	ODState_on=1,
};

// touchpad lock
// TPStatusGet, TPStatusSet
// IsSupportDisableTP
#define WMI_METHOD_ID_TPSTATUSGET 0x0
#define WMI_METHOD_ID_TPSTATUSSET 0x0
// 0=off, 1=on

//
// WinKeyStatusGet, WinKeyStatusSet
// IsSupportDisableWinKey
#define WMI_METHOD_ID_WINKEYSTATUSGET 0x0
#define WMI_METHOD_ID_WINKEYSTATUSSET 0x0

//
// LENOVO_FAN_METHOD
// Fan_Set_FullSpeed
```

### Temperatures via WMI
GetIRTemp: 1 (0x1)
GetCPUTemp: 18 (0x12)
GetGPUTemp: 19 (0x13)
```bash
echo '\_SB.GZFD.WMAA 0 0x1 0' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'
echo '\_SB.GZFD.WMAA 0 0x18 0' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'
echo '\_SB.GZFD.WMAA 0 0x19 0' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'
```
Result: Not properly implemented as seen in ACPI dissassembly.


### Fan RPM via WMI
GetFanCount: 7 (0x1)
GetFan1Speed: 8 (0x8)
GetFan2Speed: 9 (0x9)
GetFanMaxSpeed: 10 (0xA)
```bash
echo '\_SB.GZFD.WMAA 0 0x1 0' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'
echo '\_SB.GZFD.WMAA 0 0x18 0' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'
echo '\_SB.GZFD.WMAA 0 0x19 0' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'
```
Result: Not properly implemented as seen in ACPI dissassembly.

### Fan control via WMI FAN_METHOD
```
92549549-4BDE-4F06-AC04-CE8BF898DBAA
Class Name: LENOVO_FAN_METHOD
Methods Count: 8
Object ID : B2

Fan_Get_FullSpeed: 1
```


```bash
# get full speed status
echo '\_SB.GZFD.WMB2 0 0x1 0' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'

# set to full speed
echo '\_SB.GZFD.WMB2 0 0x2 1' > /proc/acpi/call
cat /proc/acpi/call; printf '\n'
```


### Script for Windows
```powershell
$wmi_classes = Get-WmiObject -Namespace 'ROOT/WMI' -List -Class "*LENOVO*"
foreach ($wmi_class in $wmi_classes){
  Write-Host "########################################"
  Write-Host "########################################"
  Write-Host "########################################"
  Write-Host "Name:" $wmi_class.Name
  Write-Host "Class Name:" $wmi_class.Name 
  Write-Host "Class GUID:" $wmi_class.Qualifiers["guid"].Value
  Write-Host "Description:" $wmi_class.Methods.Count
  Write-Host "Methods:"
  foreach ($method in $wmi_class.Methods){
    Write-Host "Name:" $method.Name
    Write-Host "WmiMethodId:" $method.Qualifiers["WmiMethodId"].Value
    Write-Host "Class Name:" $wmi_class.Name 
    Write-Host "Class GUID:" $wmi_class.Qualifiers["guid"].Value
    Write-Host "Description:" $method.Qualifiers["Description"].Value
    Write-Host "Implemented:" $method.Qualifiers["Implemented"].Value
    Write-Host ""
  }
  Write-Host ""
}
```

#### Log from Windows

########################################
########################################
########################################
Name: LENOVO_UTILITY_EVENT
Class Name: LENOVO_UTILITY_EVENT
Class GUID: {8fc0de0c-b4e4-43fd-b0f3-8871711c1294}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_SMART_FAN_MODE_EVENT
Class Name: LENOVO_GAMEZONE_SMART_FAN_MODE_EVENT
Class GUID: {D320289E-8FEA-41E0-86F9-611D83151B5F}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_THERMAL_MODE_EVENT
Class Name: LENOVO_GAMEZONE_THERMAL_MODE_EVENT
Class GUID: {D320289E-8FEA-41E0-86F9-911D83151B5F}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_KEYLOCK_STATUS_EVENT
Class Name: LENOVO_GAMEZONE_KEYLOCK_STATUS_EVENT
Class GUID: {10AFC6D9-EA8B-4590-A2E7-1CD3C84BB4B1}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_LIGHTING_EVENT
Class Name: LENOVO_LIGHTING_EVENT
Class GUID: {1e3391a1-2c89-464d-95d9-3028b72e7a33}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_LIGHT_PROFILE_CHANGE_EVENT
Class Name: LENOVO_GAMEZONE_LIGHT_PROFILE_CHANGE_EVENT
Class GUID: {D320289E-8FEA-41E0-86F9-811D83151B5F}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_SMART_FAN_SETTING_EVENT
Class Name: LENOVO_GAMEZONE_SMART_FAN_SETTING_EVENT
Class GUID: {D320289E-8FEA-41E1-86F9-611D83151B5F}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_TEMP_EVENT
Class Name: LENOVO_GAMEZONE_TEMP_EVENT
Class GUID: {BFD42481-AEE3-4501-A107-AFB68425C5F8}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_OC_EVENT
Class Name: LENOVO_GAMEZONE_OC_EVENT
Class GUID: {D062906B-12D4-4510-999D-4831EE80E985}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_FAN_COOLING_EVENT
Class Name: LENOVO_GAMEZONE_FAN_COOLING_EVENT
Class GUID: {BC72A435-E8C1-4275-B3E2-D8B8074ABA59}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_POWER_CHARGE_MODE_EVENT
Class Name: LENOVO_GAMEZONE_POWER_CHARGE_MODE_EVENT
Class GUID: {D320289E-8FEA-41E0-86F9-711D83151B5F}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_GPU_TEMP_EVENT
Class Name: LENOVO_GAMEZONE_GPU_TEMP_EVENT
Class GUID: {BFD42481-AEE3-4502-A107-AFB68425C5F8}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_UTILITY_DATA
Class Name: LENOVO_UTILITY_DATA
Class GUID: {ce6c0974-0407-4f50-88ba-4fc3b6559ad8}
Description: 1
Methods:
Name: GetIfSupportOrVersion
WmiMethodId: 1
Class Name: LENOVO_UTILITY_DATA
Class GUID: {ce6c0974-0407-4f50-88ba-4fc3b6559ad8}
Description: Utility 3.1 function is Support or the function Version
Implemented: True


########################################
########################################
########################################
Name: LENOVO_GAMEZONE_DATA
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: 62
Methods:
Name: GetIRTemp
WmiMethodId: 1
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get IR temp
Implemented: True
input: nothing
output: data
ACPI dissassembly: no handler

Name: GetThermalTableID
WmiMethodId: 2
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get ThermalTable ID
Implemented: True
ACPI dissassembly: no handler

Name: SetThermalTableID
WmiMethodId: 3
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set ThermalTable ID
Implemented: True
ACPI dissassembly: no handler

Name: IsSupportGpuOC
WmiMethodId: 4
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Is SupportGpu OverClock
Implemented: True

Name: GetGpuGpsState
WmiMethodId: 5
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get GpuGpsState
Implemented: True
ACPI dissassembly: no handler

Name: SetGpuGpsState
WmiMethodId: 6
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set GpuGpsState
Implemented: True
ACPI dissassembly: no handler

Name: GetFanCount
WmiMethodId: 7
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Fan Count
Implemented: True
input: nothing
output: data
ACPI dissassembly: no handler

Name: GetFan1Speed
WmiMethodId: 8
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Fan1 Speed
Implemented: True
input: nothing
output: data
ACPI dissassembly: no handler

Name: GetFan2Speed
WmiMethodId: 9
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Fan2 Speed
Implemented: True
input: nothing
output: data
ACPI dissassembly: no handler

Name: GetFanMaxSpeed
WmiMethodId: 10
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Fan Max Speed
Implemented: True
input: nothing
output: data
ACPI dissassembly: no handler

Name: GetVersion
WmiMethodId: 11
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get AslCode Version
Implemented: True
ACPI dissassembly: implemented, returns constant (here: 0xd)

Name: IsSupportFanCooling
WmiMethodId: 12
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Fan cooling capabilty
Implemented: True

Name: SetFanCooling
WmiMethodId: 13
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set Fan cooling on/off
Implemented: True

Name: IsSupportCpuOC
WmiMethodId: 14
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: cpu oc capability
Implemented: True
ACPI dissassembly: implemented, returns constant 0


Name: IsBIOSSupportOC
WmiMethodId: 15
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: bios has overclock capability
Implemented: True
ACPI dissassembly: implemented, returns constant 0


Name: SetBIOSOC
WmiMethodId: 16
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: enble or disable overclock in bios
Implemented: True
ACPI dissassembly: implemented, returns constant 0

Name: GetTriggerTemperatureValue
WmiMethodId: 17
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get temperature change trigger temp value
Implemented: True
ACPI dissassembly: no handler

Name: GetCPUTemp
WmiMethodId: 18
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get CPU temperature
Implemented: True
input: nothing
output: data
ACPI dissassembly: handler, returns constant 0

Name: GetGPUTemp
WmiMethodId: 19
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get GPU temperature
Implemented: True
input: nothing
output: data
ACPI dissassembly: handler, returns constant 0

Name: GetFanCoolingStatus
WmiMethodId: 20
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Fan cooling on/off status
Implemented: True
ACPI dissassyembly: implemented, does something depending on FCST, LFCM

Name: IsSupportDisableWinKey
WmiMethodId: 21
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: EC support disable windows key capability
Implemented: True
input: nothing
output: data
ACPI dissassyembly: returns 1

Name: SetWinKeyStatus
WmiMethodId: 22
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set windows key disable/enable
Implemented: True
input: data
output: nothing
ACPI dissassyembly: implemented using NCMD

Name: GetWinKeyStatus
WmiMethodId: 23
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get windows key disable/enable status
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented using NCMD

Name: IsSupportDisableTP
WmiMethodId: 24
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: EC support disable touchpad capability
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented

Name: SetTPStatus
WmiMethodId: 25
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set touchpad disable/enable
Implemented: True
input: data
output: nothing
ACPI dissassyembly: implemented using NCMD

Name: GetTPStatus
WmiMethodId: 26
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get touchpad disable/enable status
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented using NCMD

Name: GetGPUPow
WmiMethodId: 27
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get GPU normal mode max TDP(W)
Implemented: True
input: nothing
output: data
ACPI dissassyembly: no handler

Name: GetGPUOCPow
WmiMethodId: 28
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get GPU OC mode max TDP(W)
Implemented: True
input: nothing
output: data
ACPI dissassyembly: no handler

Name: GetGPUOCType
WmiMethodId: 29
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get GPU OC type
Implemented: True
input: nothing
output: data
ACPI dissassyembly: returns 0

Name: GetKeyboardfeaturelist
WmiMethodId: 30
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Keyboard feature list
Implemented: True
ACPI dissassyembly: returns constant that is computed

Name: GetMemoryOCInfo
WmiMethodId: 31
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Memory OC Information
Implemented: True
ACPI dissassyembly: returns constant that is computed

Name: IsSupportWaterCooling
WmiMethodId: 32
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Water Cooling feature capability
Implemented: True
ACPI dissassyembly: returns 0

Name: SetWaterCoolingStatus
WmiMethodId: 33
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set Water Cooling status
Implemented: True
ACPI dissassyembly: returns constant 0

Name: GetWaterCoolingStatus
WmiMethodId: 34
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Water Cooling status
Implemented: True
ACPI dissassyembly: returns constant 0

Name: IsSupportLightingFeature
WmiMethodId: 35
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Lighting feature capability
Implemented: True

Name: SetKeyboardLight
WmiMethodId: 36
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set keyboard light off or on to max
Implemented: True
ACPI dissassyembly: implemented

Name: GetKeyboardLight
WmiMethodId: 37
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get keyboard light on/off status
Implemented: True
ACPI dissassyembly: implemented

Name: GetMacrokeyScancode
WmiMethodId: 38
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Macrokey scan code
Implemented: True
ACPI dissassyembly: implemented

Name: GetMacrokeyCount
WmiMethodId: 39
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Macrokey count
Implemented: True
ACPI dissassyembly: implemented

Name: IsSupportGSync
WmiMethodId: 40
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Support G-Sync feature
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented, returns constant 0x02

Name: GetGSyncStatus
WmiMethodId: 41
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get G-Sync Statust
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented,

Name: SetGSyncStatus
WmiMethodId: 42
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set G-Sync Statust
Implemented: True
input: data
output: nothing
ACPI dissassyembly: implemented,

Name: IsSupportSmartFan
WmiMethodId: 43
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Support Smart Fan feature
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented, returns 0x04 constant

Name: SetSmartFanMode
WmiMethodId: 44
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set Smart Fan Mode
Implemented: True
input: data
output: nothing
ACPI dissassyembly: implemented,

Name: GetSmartFanMode
WmiMethodId: 45
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Smart Fan Mode
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented,

Name: GetSmartFanSetting
WmiMethodId: 46
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Smart Fan Setting Mode
Implemented: True
ACPI dissassyembly: implemented

Name: GetPowerChargeMode
WmiMethodId: 47
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Power Charge Mode
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented

Name: GetProductInfo
WmiMethodId: 48
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Gaming Product Info
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented, returns contant 0x64

Name: IsSupportOD
WmiMethodId: 49
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Over Drive feature capability
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented

Name: GetODStatus
WmiMethodId: 50
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Over Drive status
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented

Name: SetODStatus
WmiMethodId: 51
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set Over Drive status
Implemented: True
input: data
output: nothing
ACPI dissassyembly: implemented, expects 0,1

Name: SetLightControlOwner
WmiMethodId: 52
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set Light Control Owner
Implemented: True
ACPI dissassyembly: implemented

Name: SetDDSControlOwner
WmiMethodId: 53
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set DDS Control Owner
Implemented: True
ACPI dissassyembly: returns constant 0

Name: IsRestoreOCValue
WmiMethodId: 54
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get the flag of restore OC value
Implemented: True
ACPI dissassyembly: implemented

Name: GetThermalMode
WmiMethodId: 55
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Real Thremal Mode
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented, using SPMO, returns 1,2, or 3

Name: GetBIOSOCMode
WmiMethodId: 56
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get the OC switch status in BIOS
Implemented: True
ACPI dissassyembly: implemented, using COCC, returns 0, 1,2,3

Name: SetIntelligentSubMode
WmiMethodId: 57
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Set the current mode in Intelligent Mode
Implemented: True
ACPI dissassyembly: implemented,

Name: GetIntelligentSubMode
WmiMethodId: 58
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get the current mode in Intelligent Mode
Implemented: True
ACPI dissassyembly: implemented

Name: GetHardwareInfoSupportVersion
WmiMethodId: 59
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get hardware info support version
Implemented: True
ACPI dissassyembly: implemented, returns constant 1

Name: GetCpuFrequency
WmiMethodId: 60
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Cpu core 0 max frequency
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented, using CMSP and COCC, PVSD

Name: GetLearningProfileCount
WmiMethodId: 61
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Get Total count of Learning Profile
Implemented: True
ACPI dissassyembly: implemented,

Name: IsACFitForOC
WmiMethodId: 62
Class Name: LENOVO_GAMEZONE_DATA
Class GUID: {887B54E3-DDDC-4B2C-8B88-68A26A8835D0}
Description: Check the Adapter type fit for OC
Implemented: True
input: nothing
output: data
ACPI dissassyembly: implemented, using ACTY


########################################
########################################
########################################
Name: LENOVO_INTELLIGENT_OP_LIST
Class Name: LENOVO_INTELLIGENT_OP_LIST
Class GUID: {93A57CD3-BBC6-46AB-951D-31F17CC968A0}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_GPU_OC_DATA
Class Name: LENOVO_GAMEZONE_GPU_OC_DATA
Class GUID: {887B54E2-DDDC-4B2C-8B88-68A26A8835D0}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_CPU_METHOD
Class Name: LENOVO_CPU_METHOD
Class GUID: {14afd777-106f-4c9b-b334-d388dc7809be}
Description: 6
Methods:
Name: CPU_Get_OC_Status
WmiMethodId: 1
Class Name: LENOVO_CPU_METHOD
Class GUID: {14afd777-106f-4c9b-b334-d388dc7809be}
Description: Get CPU OC Status
Implemented: True

Name: CPU_Set_OC_Status
WmiMethodId: 2
Class Name: LENOVO_CPU_METHOD
Class GUID: {14afd777-106f-4c9b-b334-d388dc7809be}
Description: Set CPU OC Status
Implemented: True

Name: CPU_Get_ShortTerm_PowerLimit
WmiMethodId: 3
Class Name: LENOVO_CPU_METHOD
Class GUID: {14afd777-106f-4c9b-b334-d388dc7809be}
Description: Get CPU ShortTerm_PowerLimit
Implemented: True

Name: CPU_Set_ShortTerm_PowerLimit
WmiMethodId: 4
Class Name: LENOVO_CPU_METHOD
Class GUID: {14afd777-106f-4c9b-b334-d388dc7809be}
Description: Set CPU ShortTerm_PowerLimit
Implemented: True

Name: CPU_Get_LongTerm_PowerLimit
WmiMethodId: 5
Class Name: LENOVO_CPU_METHOD
Class GUID: {14afd777-106f-4c9b-b334-d388dc7809be}
Description: Get CPU LongTerm PowerLimit
Implemented: True

Name: CPU_Set_LongTerm_PowerLimit
WmiMethodId: 6
Class Name: LENOVO_CPU_METHOD
Class GUID: {14afd777-106f-4c9b-b334-d388dc7809be}
Description: Set CPU LongTerm_PowerLimit
Implemented: True


########################################
########################################
########################################
Name: LENOVO_GPU_METHOD
Class Name: LENOVO_GPU_METHOD
Class GUID: {da7547f1-824d-405f-be79-d9903e29ced7}
Description: 6
Methods:
Name: GPU_Get_OC_Status
WmiMethodId: 1
Class Name: LENOVO_GPU_METHOD
Class GUID: {da7547f1-824d-405f-be79-d9903e29ced7}
Description: Get GPU OC Status
Implemented: True

Name: GPU_Set_OC_Status
WmiMethodId: 2
Class Name: LENOVO_GPU_METHOD
Class GUID: {da7547f1-824d-405f-be79-d9903e29ced7}
Description: Set GPU OC Status
Implemented: True

Name: GPU_Get_PPAB_PowerLimit
WmiMethodId: 3
Class Name: LENOVO_GPU_METHOD
Class GUID: {da7547f1-824d-405f-be79-d9903e29ced7}
Description: Get GPU PPAB PowerLimit
Implemented: True

Name: GPU_Set_PPAB_PowerLimit
WmiMethodId: 4
Class Name: LENOVO_GPU_METHOD
Class GUID: {da7547f1-824d-405f-be79-d9903e29ced7}
Description: Set GPU PPAB PowerLimit
Implemented: True

Name: GPU_Get_cTGP_PowerLimit
WmiMethodId: 5
Class Name: LENOVO_GPU_METHOD
Class GUID: {da7547f1-824d-405f-be79-d9903e29ced7}
Description: Get GPU cTGP PowerLimit
Implemented: True

Name: GPU_Set_cTGP_PowerLimit
WmiMethodId: 6
Class Name: LENOVO_GPU_METHOD
Class GUID: {da7547f1-824d-405f-be79-d9903e29ced7}
Description: Set GPU cTGP PowerLimint
Implemented: True


########################################
########################################
########################################
Name: LENOVO_FAN_METHOD
Class Name: LENOVO_FAN_METHOD
Class GUID: {92549549-4bde-4f06-ac04-ce8bf898dbaa}
Description: 8
Methods:
Name: Fan_Get_FullSpeed
WmiMethodId: 1
Class Name: LENOVO_FAN_METHOD
Class GUID: {92549549-4bde-4f06-ac04-ce8bf898dbaa}
Description: Get Fan Full Speed
Implemented: True
input: nothing
output: status
ACPI dissassyembly: implemented

Name: Fan_Set_FullSpeed
WmiMethodId: 2
Class Name: LENOVO_FAN_METHOD
Class GUID: {92549549-4bde-4f06-ac04-ce8bf898dbaa}
Description: Set Fan Full Speed
Implemented: True
input: status
output: nothing
ACPI dissassyembly: implemented


Name: Fan_Get_MaxSpeed
WmiMethodId: 3
Class Name: LENOVO_FAN_METHOD
Class GUID: {92549549-4bde-4f06-ac04-ce8bf898dbaa}
Description: Get Fan Max Speed
Implemented: True
input: fan_id
output: fanMaxspeed, fanmaxspeedsize
ACPI dissassyembly: no handler

Name: Fan_Set_MaxSpeed
WmiMethodId: 4
Class Name: LENOVO_FAN_METHOD
Class GUID: {92549549-4bde-4f06-ac04-ce8bf898dbaa}
Description: Set Fan Max Speed
Implemented: True
Input: FanMaxSpeedTable
ACPI dissassyembly: no handler

Name: Fan_Get_Table
WmiMethodId: 5
Class Name: LENOVO_FAN_METHOD
Class GUID: {92549549-4bde-4f06-ac04-ce8bf898dbaa}
Description: Get Fan Table
Implemented: True
Input: FanId, SensorId
Output: FanTable, FanTableSize
ACPI dissassyembly: no handler

Name: Fan_Set_Table
WmiMethodId: 6
Class Name: LENOVO_FAN_METHOD
Class GUID: {92549549-4bde-4f06-ac04-ce8bf898dbaa}
Description: Set Fan Table
Implemented: True
Input: FanTable
ACPI dissassyembly: no handler

Name: Fan_GetCurrentFanSpeed
WmiMethodId: 7
Class Name: LENOVO_FAN_METHOD
Class GUID: {92549549-4bde-4f06-ac04-ce8bf898dbaa}
Description: Get Current Fan Speed
Implemented: True
Input: FanId (0 (fan 1) or 1(fan 2))
Output: CurrentFanSpeed
ACPI dissassyembly: implementeed using EC0.FANS, EC0.FA2S

Name: Fan_GetCurrentSensorTemperature
WmiMethodId: 8
Class Name: LENOVO_FAN_METHOD
Class GUID: {92549549-4bde-4f06-ac04-ce8bf898dbaa}
Description: Get Current Sensor Temperature
Implemented: True
Input: SensorId (0x03 (cpu) or 0x04(gpu))
Output: CurrentSensorTemperatue
ACPI disassembly: implemented using EC0.CPUT, EC0.GPUT


########################################
########################################
########################################
Name: LENOVO_FAN_TABLE_DATA
Class Name: LENOVO_FAN_TABLE_DATA
Class GUID: {87fb2a6d-d802-48e7-9208-4576c5f5c8d8}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_OTHER_METHOD
Class Name: LENOVO_OTHER_METHOD
Class GUID: {dc2a8805-3a8c-41ba-a6f7-092e0089cd3b}
Description: 8
Methods:
Name: GetDeviceType
WmiMethodId: 1
Class Name: LENOVO_OTHER_METHOD
Class GUID: {dc2a8805-3a8c-41ba-a6f7-092e0089cd3b}
Description: Get Device Type
Implemented: True

Name: GetSupportThermalMode
WmiMethodId: 2
Class Name: LENOVO_OTHER_METHOD
Class GUID: {dc2a8805-3a8c-41ba-a6f7-092e0089cd3b}
Description: Get Thermal Mode Status
Implemented: True

Name: GetCustomModeAbility
WmiMethodId: 3
Class Name: LENOVO_OTHER_METHOD
Class GUID: {dc2a8805-3a8c-41ba-a6f7-092e0089cd3b}
Description: Get Custom Mode Abiltiy
Implemented: True

Name: Set_Custom_Mode_Status
WmiMethodId: 4
Class Name: LENOVO_OTHER_METHOD
Class GUID: {dc2a8805-3a8c-41ba-a6f7-092e0089cd3b}
Description: Set Custom Mode Status
Implemented: True

Name: Get_Legion_Device_Support_Feature
WmiMethodId: 5
Class Name: LENOVO_OTHER_METHOD
Class GUID: {dc2a8805-3a8c-41ba-a6f7-092e0089cd3b}
Description: Get Device Support Feature Status
Implemented: True

Name: Get_Device_Current_Support_Feature
WmiMethodId: 6
Class Name: LENOVO_OTHER_METHOD
Class GUID: {dc2a8805-3a8c-41ba-a6f7-092e0089cd3b}
Description: Get Device Current Support Feature Status
Implemented: True

Name: Set_Device_Current_Support_Feature
WmiMethodId: 7
Class Name: LENOVO_OTHER_METHOD
Class GUID: {dc2a8805-3a8c-41ba-a6f7-092e0089cd3b}
Description: Set Device Current Support Feature enable/disalbe
Implemented: True

Name: Get_Support_LegionZone_Version
WmiMethodId: 8
Class Name: LENOVO_OTHER_METHOD
Class GUID: {dc2a8805-3a8c-41ba-a6f7-092e0089cd3b}
Description: Get Support Legionzone Version
Implemented: True


########################################
########################################
########################################
Name: LENOVO_FAN_MAX_SPEED_DATA
Class Name: LENOVO_FAN_MAX_SPEED_DATA
Class GUID: {c3c7aeb8-4c06-4d40-8f29-212a6ccd74aa}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GPU_OVERCLOCKING_DATA
Class Name: LENOVO_GPU_OVERCLOCKING_DATA
Class GUID: {8A8984E2-228F-685F-B496-DDA5F52CBE5B}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_PANEL_METHOD
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: 22
Methods:
Name: Panel_Get_Support_Status
WmiMethodId: 1
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel Support Functions
Implemented: True

Name: Panel_Get_Status
WmiMethodId: 2
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel Functions Status
Implemented: True

Name: Panel_Set_Status
WmiMethodId: 3
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel Functions Status
Implemented: True

Name: Panel_Get_Low_Latency_Mode
WmiMethodId: 4
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel Low Latency Mode
Implemented: True

Name: Panel_Set_Low_Latency_Mode
WmiMethodId: 5
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel Low Latency Mode
Implemented: True

Name: Panel_Get_PIP_Info
WmiMethodId: 6
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel PIP Info
Implemented: True

Name: Panel_Set_PIP_Info
WmiMethodId: 7
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel PIP Info
Implemented: True

Name: Panel_Get_Game_Aid_FPS_Display_Pos
WmiMethodId: 8
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel Game Aid FPS Display
Implemented: True

Name: Panel_Set_Game_Aid_FPS_Display_Pos
WmiMethodId: 9
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel Game Aid FPS Display
Implemented: True

Name: Panel_Get_Game_Aid_FPS
WmiMethodId: 10
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel Game Aid FPS Display
Implemented: True

Name: Panel_Get_Game_Aid_Sight_Mode
WmiMethodId: 11
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel Game Aid Sight Mode
Implemented: True

Name: Panel_Set_Game_Aid_Sight_Mode
WmiMethodId: 12
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel Game Aid Sight Mode
Implemented: True

Name: Panel_Get_Game_Aid_Timer_Info
WmiMethodId: 13
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel Game Aid Timer Info
Implemented: True

Name: Panel_Set_Game_Aid_Timer_Info
WmiMethodId: 14
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel Game Aid Timer Info
Implemented: True

Name: Panel_Get_Game_Aid_Countdown_Info
WmiMethodId: 15
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel Game Aid Countdown Timer Info
Implemented: True

Name: Panel_Set_Game_Aid_Countdown_Info
WmiMethodId: 16
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel Game Aid Countdown Timer Info
Implemented: True

Name: Panel_Get_Display_Mode
WmiMethodId: 17
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel Display Mode
Implemented: True

Name: Panel_Set_Display_Mode
WmiMethodId: 18
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel Display Mode
Implemented: True

Name: Panel_Get_Gamut_Switch
WmiMethodId: 19
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel Gamut Switch
Implemented: True

Name: Panel_Set_Gamut_Switch
WmiMethodId: 20
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel Gamut Switch
Implemented: True

Name: Panel_Get_MPRT
WmiMethodId: 21
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Get Panel MPRT info
Implemented: True

Name: Panel_Set_MPRT
WmiMethodId: 22
Class Name: LENOVO_PANEL_METHOD
Class GUID: {e5edffbf-e822-4bbe-8650-c07b8bae4c54}
Description: Set Panel MPRT info
Implemented: True


########################################
########################################
########################################
Name: LENOVO_CPU_OVERCLOCKING_DATA
Class Name: LENOVO_CPU_OVERCLOCKING_DATA
Class GUID: {4C90256D-44EA-D6A8-7650-63DF4FEB2CFF}
Description: 0
Methods:

########################################
########################################
########################################
Name: Lenovo_SystemElement
Class Name: Lenovo_SystemElement
Class GUID:
Description: 0
Methods:

########################################
########################################
########################################
Name: Lenovo_BatteryInformation
Class Name: Lenovo_BatteryInformation
Class GUID: C3A03776-51AC-49AA-AD0F-F2F7D62C3F3C
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_MEMORY_OC_DATA
Class Name: LENOVO_MEMORY_OC_DATA
Class GUID: {37d0014b-370c-47ef-bf03-588e8acb2fcd}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_LIGHTING_DATA
Class Name: LENOVO_LIGHTING_DATA
Class GUID: {4dd5bd84-15a9-47e2-ad65-cc61a5c62fd0}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_GAMEZONE_CPU_OC_DATA
Class Name: LENOVO_GAMEZONE_CPU_OC_DATA
Class GUID: {B7F3CA0A-ACDC-42D2-9217-77C6C628FBD2}
Description: 0
Methods:

########################################
########################################
########################################
Name: LENOVO_LIGHTING_METHOD
Class Name: LENOVO_LIGHTING_METHOD
Class GUID: {8c5b9127-ecd4-4657-980f-851019f99ca5}
Description: 2
Methods:
Name: Get_Lighting_Current_Status
WmiMethodId: 1
Class Name: LENOVO_LIGHTING_METHOD
Class GUID: {8c5b9127-ecd4-4657-980f-851019f99ca5}
Description: Get Current Lighting Status
Implemented: True
input: lighting_id
output: current_Brigness_Level, Current_State_Type

Name: Set_Lighting_Current_Status
WmiMethodId: 2
Class Name: LENOVO_LIGHTING_METHOD
Class GUID: {8c5b9127-ecd4-4657-980f-851019f99ca5}
Description: Set Current Lighting Status
Implemented: True
Input: Current_Brithngess_Level, Current_State_Type, Lighting_ID


########################################
########################################
########################################
Name: LENOVO_MEMORY_METHOD
Class Name: LENOVO_MEMORY_METHOD
Class GUID: {03607fce-0d83-4612-8a6e-4a4ef0415ea9}
Description: 3
Methods:
Name: MEM_Get_OC_Status
WmiMethodId: 1
Class Name: LENOVO_MEMORY_METHOD
Class GUID: {03607fce-0d83-4612-8a6e-4a4ef0415ea9}
Description: Get Memory OC Status
Implemented: True

Name: MEM_Set_OC_Status
WmiMethodId: 2
Class Name: LENOVO_MEMORY_METHOD
Class GUID: {03607fce-0d83-4612-8a6e-4a4ef0415ea9}
Description: Set Memory OC Status
Implemented: True

Name: MEM_Set_OC_Data
WmiMethodId: 3
Class Name: LENOVO_MEMORY_METHOD
Class GUID: {03607fce-0d83-4612-8a6e-4a4ef0415ea9}
Description: Set Memory OC Data
Implemented: True