#!/usr/bin/env bash

# Checks for doas, sudo, bat and cat first
# Runs make and restarts power-profiles-daemon

kernel_patching() {

    local privup
    local catit

    privup=""
    catit="cat"
    # checks if is root to not use sudo or doas
    if [[ ! "${USER}" ]]; then
    # checks if doas is installed and use it as default
        [[ -f /usr/bin/doas ]] && privup="doas" || privup="sudo"
    fi
    # check if bat is installed and use it as default
    [[ -f /usr/bin/bat ]] && catit="/usr/bin/bat --paging never" || catit="/usr/bin/cat"

    make
    "${privup}" make install
    "${privup}" make reloadmodule | tail --lines=5 | ${catit}
    "${privup}" systemctl restart power-profiles-daemon --no-pager --show-transaction

    printf "%s %s\n" "Patching done." "$?"

}

kernel_patching
