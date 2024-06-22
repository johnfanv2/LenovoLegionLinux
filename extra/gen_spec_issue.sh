#!/bin/bash

template="./spec_issue_template.md"

# Create file from template
result="./specs.md"
cp $template $result

# system
sysinfo=$(dmidecode -t system)
sysinfo=$(awk '!/UUID/' <<< $sysinfo)
sysinfo=$(awk '!/Serial Number/' <<< $sysinfo)
echo "$(awk -v sys_info="$sysinfo" '{gsub(/sysinfo/,sys_info,$0); print $0}'  $result)" > $result

# bios
biosinfo=$(dmidecode -t bios)
echo "$(awk -v bios_info="$biosinfo" '{gsub(/biosinfo/,bios_info,$0); print $0}'  $result)" > $result

# fancurve
fancurve=$(cat /sys/kernel/debug/legion/fancurve)
echo "$(awk -v fancurve="$fancurve" '{gsub(/fancurves/,fancurve,$0); print $0}'  $result)" > $result

# Inspect WMI entries
if ! command -v fwts >/dev/null; then
  echo "$(awk '{gsub(/wmi_entries/,"Not generated",$0); print $0}'  $result)" > "$result"
  echo fwts was not found. Skipping reading of wmi entries. Please install fwts or if it is already installed add it to \$PATH in order to use this feature.
else
  # Generate entries
  fwts_file="./wmi.log"
  fwts wmi - > "$fwts_file"

  # Compress wmi entries
  compressed_wmi_entries="./wmi-entries.tar.gz"
  tar -czvf $compressed_wmi_entries $fwts_file

  # Modify md file for files
  echo "$(awk '{gsub(/wmi_entries/,"Insert WMI entries here"); print}'  $result)" > $result
fi

# ACPI tables
if ! command -v iasl >/dev/null; then
  echo "$(awk '{gsub(/acpi_tables/,"Not generated",$0); print $0}'  $result)" > "$result"
  echo iasl was not found. Skipping reading and disassembling of ACPI tables. Please install acpica-tools or if it is already installed add it to \$PATH in order to use this feature.
else
  # Create directory for tables
  acpi_table_loc="acpi_re"
  mkdir -p "$acpi_table_loc"
  cd "$acpi_table_loc"

  # Copy entries to working directory
  cp --no-preserve=mode /sys/firmware/acpi/tables/*SDT* ./
  
  # Disassemble tables
  iasl -e "$acpi_table_loc/SSDT*" -d DSDT
  
  # Compress tables
  cd ..
  compressed_acpi_tables="./acpi-tables.tar.gz"
  tar -czxf "$compressed_acpi_tables" "$acpi_table_loc"
  
  # Modify md file for files
  echo "$(awk '{gsub(/acpi_tables/,"Insert compressed ACPI tables here",$0); print $0}'  $result)" > "$result"
fi

