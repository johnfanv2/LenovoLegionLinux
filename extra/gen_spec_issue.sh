#!/bin/bash

# Collects system information into specs.md for use in a bug report.
# Needs root, because dmidecode and the debugfs fancurve dump do.

set -e

# dmidecode and the debugfs fancurve dump both need root. Without it they
# only emit a two line stub, which would be pasted into the issue as if it
# were the real system information.
if [ "$(id -u)" -ne 0 ]; then
	echo "This script needs root: dmidecode and /sys/kernel/debug/legion/fancurve do." >&2
	exit 1
fi

# Resolve the template next to this script, so the report can be
# generated from any working directory.
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

template="./spec_issue_template.md"
result="./specs.md"
tmp_result="$result.tmp"

cleanup() {
	if [ -n "$tmp_result" ]; then
		rm -f "$tmp_result"
	fi
}
trap cleanup EXIT

# Replace one placeholder in the report with the given text.
# Rewrites through a temporary file: the report is both the input and the
# output, and redirecting into it directly would truncate it before awk
# had read it.
substitute() {
	local placeholder=$1 replacement=$2
	awk -v placeholder="$placeholder" -v replacement="$replacement" \
		'{ gsub(placeholder, replacement, $0); print $0 }' "$result" >"$tmp_result"
	mv "$tmp_result" "$result"
}

# Create file from template
cp "$template" "$result"

# model name
model_name=$(dmidecode 2>/dev/null | grep -A3 '^System Information' | grep Version | cut -d : -f 2 || true)
# strip the surrounding whitespace left behind by "cut -d : -f 2"
read -r model_name <<<"$model_name"
substitute modelname "${model_name:-Not available}"

# cpu model
cpu_model=$(lscpu -e=MODELNAME 2>/dev/null | head -2 | tail -1 || true)
substitute cpumodel "${cpu_model:-Not available}"

# gpu model
gpu_model=$(glxinfo 2>/dev/null | grep "OpenGL renderer string" | cut -d : -f 2 || true)
# strip the surrounding whitespace left behind by "cut -d : -f 2"
read -r gpu_model <<<"$gpu_model"
substitute gpumodel "${gpu_model:-Not available}"

# Keyboard backlight
kb_backlight="Unknown"
substitute kbbacklight "$kb_backlight"

# system
sysinfo=$(dmidecode -t system 2>/dev/null | awk '!/UUID/' | awk '!/Serial Number/' || true)
substitute sysinfo "${sysinfo:-Not available}"

# bios
biosinfo=$(dmidecode -t bios 2>/dev/null || true)
substitute biosinfo "${biosinfo:-Not available}"

# fancurve
fancurve=$(cat /sys/kernel/debug/legion/fancurve 2>/dev/null || true)
substitute fancurves "${fancurve:-Not available}"

# Inspect WMI entries
if ! command -v fwts >/dev/null; then
	substitute wmi_entries "Not generated"
	echo "fwts was not found. Skipping reading of wmi entries. Please install fwts or if it is already installed add it to \$PATH in order to use this feature."
else
	# Generate entries
	fwts_file="./wmi.log"
	fwts wmi - >"$fwts_file"

	# Compress wmi entries
	compressed_wmi_entries="./wmi-entries.tar.gz"
	tar -czvf "$compressed_wmi_entries" "$fwts_file" >/dev/null

	# Modify md file for files
	substitute wmi_entries "Insert WMI entries here"
fi

# ACPI tables
if ! command -v iasl >/dev/null; then
	substitute acpi_tables "Not generated"
	echo "iasl was not found. Skipping reading and disassembling of ACPI tables. Please install acpica-tools or if it is already installed add it to \$PATH in order to use this feature."
elif ! (
	# Create directory for tables
	acpi_table_loc="./acpi_re"
	rm -rf "$acpi_table_loc"
	mkdir -p "$acpi_table_loc"

	# Copy entries to working directory and disassemble them. In a
	# subshell, so the cd cannot leak into the rest of the script.
	cd "$acpi_table_loc"

	# Unquoted, a machine without SSDT tables would hand cp a literal
	# "*SDT*" and fail; with nullglob an empty match is detected here.
	shopt -s nullglob
	sdt_tables=(/sys/firmware/acpi/tables/*SDT*)
	if [ "${#sdt_tables[@]}" -eq 0 ]; then
		echo "No ACPI SSDT tables were found."
		exit 1
	fi
	cp --no-preserve=mode "${sdt_tables[@]}" ./

	iasl -n -e SSDT* -d DSDT &>/dev/null
); then
	substitute acpi_tables "Not generated"
	echo "Skipping reading and disassembling of ACPI tables."
else
	# Compress tables
	compressed_acpi_tables="./acpi-tables.tar.gz"
	tar -czvf "$compressed_acpi_tables" acpi_re >/dev/null

	# Modify md file for files
	substitute acpi_tables "Insert compressed ACPI tables here"
fi
