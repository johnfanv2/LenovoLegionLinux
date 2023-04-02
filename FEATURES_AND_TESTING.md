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


	if (cmd == "enable_rapid_charge") {
		callACPI("\\_SB.PCI0.LPC0.EC0.VPC0.SBMC 0x07");
	}
	else if (cmd == "disable_rapid_charge") {
		callACPI("\\_SB.PCI0.LPC0.EC0.VPC0.SBMC 0x08");