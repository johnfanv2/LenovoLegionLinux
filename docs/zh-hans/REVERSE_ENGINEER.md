## 检查 WMI 条目
```bash
# 安装所需工具
sudo apt install fwts

# 创建文件夹存放所有新文件
mkdir fwts_re
cd fwts_re
sudo fwts wmi - > fwts_wmi.log
```
然后上传这些文件。

## 反汇编 ACPI 表

```bash
# 安装所需工具
sudo apt install acpica-tools
```

```bash
# 创建文件夹存放所有新文件
mkdir acpi_re
cd acpi_re

# 列出 ACPI 表并复制
ls /sys/firmware/acpi/tables/
sudo cp --no-preserve=mode /sys/firmware/acpi/tables/*SDT* .

# 反汇编 ACPI 表并输出 DSDT.dsl
iasl -e SSDT* -d DSDT
```

然后上传这些文件。

## 在 Windows 中收集 WMI 信息
在 Windows 中以管理员身份打开 PowerShell 并运行以下脚本。它会列出所有可用的 Lenovo WMI 方法。把输出复制到一个文件并上传。
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

## 查找嵌入式控制器（EC）的内存映射地址

找到嵌入式控制器对应的部分。它会包含类似这样的内容。
```
Device (EC0)
    Name (_HID, EisaId ("PNP0C09") /* Embedded Controller Device */)  // _HID: Hardware ID
    Name (_UID, One)  // _UID: Unique ID
```

然后找到嵌入式控制器使用的区域。DSDT 中还有很多其它区域，但只有位于嵌入式控制器作用域（大括号）之内的区域才是我们关心的。

你会找到类似这样的内容：
```text
OperationRegion (ERAM, EmbeddedControl, Zero, 0xFF)

OperationRegion (ECMS, SystemIO, 0x72, 0x02)

OperationRegion (ERAX, SystemMemory, 0xFE00D400, 0xFF)
- 映射到内存地址 0xFE00D400
- 定义了最多字段的区域

OperationRegion (ECB2, SystemMemory, 0xFF00D520, 0xFF)
- 映射到内存地址 0xFF00D520
- 定义了最多字段的区域
```

这说明嵌入式控制器的寄存器/内存被映射到了（CPU 的）内存地址空间。注意，上面 ACPI 表中描述的这些区域只是 ACPI 直接使用的寄存器/内存。

通常，嵌入式控制器的更多寄存器/内存同样被映射到了（CPU 的）内存中。它们通常位于 ACPI 表所提及的这些区域之前或之后。

## 观察内存地址随功能发生的变化
现在我们可以读取这些内存映射区域了。然后改变一些东西，例如：
- 通过增加 CPU 负载来提高风扇转速
- 通过增加 CPU 负载来升高温度
- 通过按 Fn + Q 切换电源模式，这同时应该会改变硬件中的风扇曲线

```bash
cat /sys/kernel/debug/legion/ecmemory | hexdump -C
```

- 在你用 Fn+Q 切换电源模式的前后各执行一次。尝试找出哪些值发生了变化、哪些值可能代表风扇曲线。
