#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Mock HWMON for tet
mkdir -p /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon0

# Smoketest CLI
${DIR}/../python/legion_linux/legion_cli.py
