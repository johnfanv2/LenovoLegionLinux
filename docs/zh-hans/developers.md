# 开发者概览

本软件包含以下几个部分：

- `kernel_module` 文件夹下的内核模块：
  - 通过写入内存访问嵌入式控制器（EC）
  - 创建新的“文件”：如 `/sys/kernel/debug/legion/fancurve`、 `/sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/powermode`、 `/sys/class/hwmon/X/temp1_input`、 `/sys/class/hwmon/X/pwmY_auto_pointZ_pwm` 等，用户可以通过这些文件读取温度传感器、控制风扇曲线、切换电源模式等。

- `python` 文件夹下的 Python 包：
  - `legion.py`：用于从 Python 修改风扇曲线及其他设置的模块；封装了对上述内核模块及 `ideapad_laptop` 等模块提供的“文件”的读写；所有来自 `legion_gui.py` 和 `legion_cli.py` 的设置更改都通过本模块完成。
  - `legion_gui.py`：一个基于 `legion.py` 的图形界面（GUI）程序，用于更改设置。
  - `legion_cli.py`：一个基于 `legion.py` 的命令行（CLI）程序，用于更改设置。

- `extra/service/legiond` 文件夹下的 `legiond` 守护进程：
  - 一个小型 C 守护进程（附带 `legiond-ctl` 辅助工具），监听电源状态/电源配置变化并应用对应的风扇曲线预设，还可通过 `legiond.ini` 配置可选的 CPU/GPU 功耗调整。

- `extra/smartfan` 文件夹下的 SmartFan：
  - 一个独立的 shell 风扇守护进程，面向 Legion 7 Gen 10+ 机型，仅需 `acpi_call`，无需完整内核模块。
