# Overview for Developers

The software consists of the following parts:

- Kernel module in the `kernel_module` folder:
  - Accesses the embedded controller by writing to its memory
  - Creates new "files": `/sys/kernel/debug/legion/fancurve`, `/sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/powermode` ,
    `/sys/class/hwmon/X/temp1_input`, `/sys/class/hwmon/X/pwmY_auto_pointZ_pwm`, ... that allows to
    read the temperatue sensors, control the fan curve, change power mode etc.
- Python packages in the `python` folder:
  - `legion.py`: A Python module to modify the fan curve and other settings from Python; Encapsulate reading and writing to the "files" provided by the above kernel module and other modules like `ideapad_laptop`; All changes from `legion_gui.py` and `legion_cli.py` goes through this Python module.
  - `legion_gui.py`: a GUI program that uses `legion.py` to change setttings.
  - `legion_cli.py`: a CLI program that uses `legion.py` to change setttings.
- `legiond` daemon in the `extra/service/legiond` folder:
  - A small C daemon (with its `legiond-ctl` helper) that watches power state/power profile changes and applies the matching fan curve preset, plus optional CPU/GPU power tweaks configured in `legiond.ini`.
- SmartFan in the `extra/smartfan` folder:
  - A standalone shell-based fan daemon for Legion 7 Gen 10+ laptops that only needs `acpi_call` instead of the full kernel module.
