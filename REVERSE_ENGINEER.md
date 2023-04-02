## Disassembling ACPI tables

```bash
# Install requiered tools
sudo apt install acpica-tools
```

```bash
# Create folder for all the new files
mkdir acpi_re
cd acpi_re

# List ACPI tables and copy them
ls /sys/firmware/acpi/tables/
sudo cp --no-preserve=mode /sys/firmware/acpi/tables/*SDT* .

# Disassemble tables to output DSDT.dsl
iasl -e SSDT* -d DSDT
```

Then upload files.

## Find Mapped Memory Address of Embedded Controller

Find the part for the embedded controller. It will contain something like this.
```
Device (EC0)
    Name (_HID, EisaId ("PNP0C09") /* Embedded Controller Device */)  // _HID: Hardware ID
    Name (_UID, One)  // _UID: Unique ID
```

Then find the regions used by the embedded controller. There are lots of other regions, but only
these are interesting that are within the scope/braces of the embedded controller.


You will find something similar to this:
```text
OperationRegion (ERAM, EmbeddedControl, Zero, 0xFF)

OperationRegion (ECMS, SystemIO, 0x72, 0x02)

OperationRegion (ERAX, SystemMemory, 0xFE00D400, 0xFF)
- mapped into memory at 0xFE00D400
- region with most of the fields defined

OperationRegion (ECB2, SystemMemory, 0xFF00D520, 0xFF)
- mapped into memory at 0xFF00D520
- region with most of the fields defined
```

This will show that registers/memory of the embedded controller is mapped to (CPU) 
memory address space. Note that these regions described in the ACPI tables above
are only the registers/memory used directly in ACPI. 

Often, much more registers/memory of the embedded controller are mapped to (CPU).
Usually, these are before or after the regions mentioned in the ACPI tables.

## Observing what Changes to Associate Memory Addresses With Functions
Now we can read the memory mapped regions. Then we change something, e.g.
- increase fan speed by increasing CPU load
- increase temperature by increasing CPU load
- change power mode by pressing Fn + Q, which should also change fan curves in hardware

```bash
cat /sys/kernel/debug/legion/ecmemory | hexdump -C
```

- before and after you change the power mode with Fn+Q. Try to find which values change and which could represent the fan curve.