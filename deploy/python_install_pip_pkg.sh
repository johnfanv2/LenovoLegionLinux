#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${DIR}/../python/legion_linux

# Build and install python package
python3 -m pip install --upgrade build
python3 -m build
sudo python3 -m pip install -e .

# Desktop file
sudo cp legion_linux/legion_gui.desktop /usr/share/applications/
sudo mkdir -p /usr/share/icons/
sudo cp legion_linux/legion_logo.png /usr/share/icons/legion_logo.png

sudo cp legion_linux/legion_gui.policy /usr/share/polkit-1/actions/

cd ${DIR}/../extra

sudo cp service/fancurve-set /usr/bin/
cp service/.env $HOME/.config/lenovo_linux/
cp -r service/profiles/* $HOME/.config/lenovo_linux
sudo cp service/{legion-linux.service,legion-linux-restart.path,legion-linux-restart.service} /etc/systemd/system/

read -p "You what to install acpi action [Not recommed for normal user still in develoment]: " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]
then
    sudo cp acpi/{ac_adapter_legion-fancurve,novo-button,PrtSc-button,fn-r-refrate} /etc/acpi/events
    sudo cp acpi/{battery-legion-quiet.sh,snipping-tool.sh,fn-r-refresh-rate.sh} /etc/acpi/actions
fi

echo "Done"