#!/usr/bin/env bash
# From the discussion https://github.com/johnfanv2/LenovoLegionLinux/pull/29
##########################################
# Checks for doas, sudo, bat and cat first
# Runs make, make reloadmodule and make install.
# Also reloads/restarts power-profiles-daemon when done.
# Test mode and Install mode
##########################################
lll_kernel_patching()
                      {
    LC_ALL=C
    LANG=C

    local script_folder
    local kernel_version
    local privup
    local catit
    local -i reload_verbosity
    local lll_mode
    local usage_message

    script_folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    kernel_version="$(uname -r)"
    catit="cat"
    # checks if is root to not use sudo or doas
    if [[ ! "${USER}" = 1000 ]]; then
        # checks if doas is installed and use it as default
        [[ -f /usr/bin/doas ]] && privup="doas" || privup="sudo"
    fi
    # check if bat is installed and use it as default
    [[ -f /usr/bin/bat ]] && catit="/usr/bin/bat --paging never" || catit="/usr/bin/cat"
    # reload_verbosity (number of lines)
    # 1 = just the last message if it's loaded or nor (default)
    # 5 = last five lines including success (@ARYN-27 default)
    # 41 = all latest messages related to unloading and loading the LLL module
    [[ "${2}" =~ 1|5|41 ]] && reload_verbosity="${2}" || reload_verbosity=1
    lll_mode="build|load|install"

    if [[ $# -gt 0 ]] && [[ $# -lt 3 ]]; then

        if [[ "${1}" =~ ${lll_mode[*]} ]]; then

            pushd "${script_folder}" || return
            printf "Running %s mode.\n" "${1}"
            printf "Starting patching process for kernel-%s\n\n" "${kernel_version}"
            make
            [[ "${1}" = "build" ]] && exit 0
            if [[ "${1}" = "install" ]]; then
                echo MAKEINSTALL
                ${privup} make install
            fi
            ${privup} make reloadmodule | tail --lines="${reload_verbosity}" | ${catit}
            ${privup} systemctl restart power-profiles-daemon --no-pager --show-transaction
            printf "Patching process done. Exit %s\n" "$?"
            popd || return

        fi

    else

        usage_message="
        Accepted parameters: ${lll_mode[*]} + 1|5|41
        build = Just builds the module
        install (permanent) = Permanently install the module for the current kernel
        load (test mode) = Applies the patch for the current session.
        And the values for verbosity:
        1 = just the last message if it's loaded or nor (default)
        5 = last five lines including success (@ARYN-27 default)
        41 = all latest messages related to unloading and loading the LLL module"
        printf "%s" "${usage_message}"

    fi

}
lll_kernel_patching "${@}"
