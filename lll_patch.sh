#!/usr/bin/env bash
# From the discussion https://github.com/johnfanv2/LenovoLegionLinux/pull/29
#####################
# Checks for doas, sudo, bat and cat first
# Runs make, make reloadmodule and make install, also reloads/restarts power-profiles-daemon
# Test mode and Install mode
#####################
lll_kernel_patching()
                      {
    LC_ALL=C
    LANG=C

    local script_folder
    local kernel_version
    local krn_dir
    local privup
    local catit
    local -i reload_verbosity
    local lll_mode

    script_folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    kernel_version="$(uname -r)"
    krn_dir="kernel_module"
    catit="cat"
    # checks if is root to not use sudo or doas
    if [[ ! "${USER}" = 1000 ]]; then
        # checks if doas is installed and use it as default
        [[ -f /usr/bin/doas ]] && privup="doas" || privup="sudo"
    fi
    # check if bat is installed and use it as default
    [[ -f /usr/bin/bat ]] && catit="/usr/bin/bat --paging never" || catit="/usr/bin/cat"
    # reload_verbosity
    # 1 = just the last message if it's loaded or nor
    # 5 = last five lines including success
    # 41 = all latest messages related to unloading and loading the LLL module
    reload_verbosity=41
    lll_mode="load|install"

    if [[ $# -eq 1 ]]; then

        if [[ "${1}" =~ ${lll_mode[*]} ]]; then

            pushd "${script_folder}/${krn_dir}" || return
            printf "Running %s mode. (load = test mode, install = permanent mode)\n" "${1}"
            printf "Starting patching process for kernel-%s\n\n" "${kernel_version}"
            make
            if [[ "${1}" == "install" ]]; then
                ${privup} make install
            fi
            ${privup} make reloadmodule | tail --lines="${reload_verbosity}" | ${catit}
            ${privup} systemctl restart power-profiles-daemon --no-pager --show-transaction

            printf "Patching process done. Exit %s\n" "$?"
            popd || return

        fi

    else

        printf "Accepted parameters: %s\nload = test mode, install = permanent mode" "${lll_mode[*]}"

    fi

}
lll_kernel_patching "${@}"
