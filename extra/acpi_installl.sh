#!/bin/bash
#chnage power mode and restart service on ac plug/unplug
sudo cp acpi/events/ac_adapter_legion-fancurve /etc/acpi/events
sudo cp acpi/actions/battery-legion-quiet.sh /etc/acpi/actions

read -p "Acpi event to change power mode and restart systemd service on power plug/unplug" -n 1 -r

read -p "You what to install the other acpi action [Not recommed for normal user still in develoment]: " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]
then
    sudo cp acpi/events/{novo-button,PrtSc-button,fn-r-refrate} /etc/acpi/events
    sudo cp acpi/actions/{snipping-tool.sh,fn-r-refresh-rate.sh} /etc/acpi/actions
fi