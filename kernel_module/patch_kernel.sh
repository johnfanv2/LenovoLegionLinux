#!/usr/bin/env bash
##########################################
# Based on the script made by @ARYN-27
# From the discussion https://github.com/johnfanv2/LenovoLegionLinux/pull/29
# Checks for doas, sudo, bat, dkms and cat first
# Runs make, make reloadmodule, make install, make uninstall and dkms.
# Also reloads/restarts power-profiles-daemon when done.
# Test mode and Install mode
##########################################
lll_kernel_patching() {
    LC_ALL=C
    LANG=C

    local script_folder
    local package_name
    local package_version
    local kernel_version
    local privup
    local catit
    local -i reload_verbosity
    local lll_mode
    local usage_message
    local dkms_usr_folder

    script_folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    package_name="LenovoLegionLinux"
    package_version="1.0.0"
    kernel_version="$(uname -r)"
    catit="cat"
    # checks if is root to not use sudo or doas
    if [[ "${USER}" != root ]]; then
        # checks if doas is installed and use it as default
        [[ -f /usr/bin/doas ]] && privup="doas" || privup="sudo"
    fi
    # check if bat is installed and use it as default
    [[ -f /usr/bin/bat ]] && catit="/usr/bin/bat --paging never" || catit="/usr/bin/cat"
    # reload_verbosity (number of lines)
    # 1 = just the last message if it's loaded or nor (default)
    # 5 = last five lines including success (@ARYN-27 default)
    # 41 = all latest messages related to unloading and loading the LLL module
    if [[ "${2}" != "" ]] && [[ "${2}" =~ 1|5|41 ]]; then
        reload_verbosity="${2}"
    else
        reload_verbosity=1
    fi
    lll_mode="build|dkms|dkmsrm|load|install|remove"
    dkms_usr_folder="/usr/src/LenovoLegionLinux-1.0.0"
    usage_message="
        Accepted parameters: ${lll_mode[*]}
        Accepted verbosity parameters: 1|5|41 (not for dkms)

        build
             Just builds the module.
        dkms
             Installs via DKMS.
        dkmsrm
             Removes DKMS.
        install
             Permanently install the module for the current kernel.
        load
             Applies the patch for the current session. Per session.
        remove
             Uninstalls the patch for the current kernel.

        And the values for verbosity:
             1:  just the last message if it's loaded or nor (default);
             5:  last five lines including success (@ARYN-27 default);
             41: all latest messages related to unloading and loading the LLL module.
        "

    if [[ $# -gt 0 ]] && [[ $# -lt 3 ]] && [[ "${1}" =~ ${lll_mode[*]} ]]; then

        pushd "${script_folder}" || return
        printf "Running %s mode.\n" "${1}"
        if [[ "${1}" =~ dkmsrm|remove ]]; then
            printf "%s\n\n" "Starting removing process"
        else
            printf "Starting patching process for kernel-%s\n\n" "${kernel_version}"
        fi

        case "${1}" in
        build)
            make
            ;;
        install)
            printf "%s\n" "MAKEINSTALL"
            make
            ${privup} make install
            ;;
        dkms)
            printf "%s\n" " folder for dkms"
            ${privup} make dkms
            ;;
        dkmsrm)
            if [[ -d "${dkms_usr_folder}" ]]; then
                dkms remove -m "${package_name}" -v "${package_version}"
                rmdir --ignore-fail-on-non-empty --verbose "${dkms_usr_folder}"
            fi
            ;;
        remove)
            make
            ${privup} make uninstall
            ;;
        load)
            make
            ${privup} make reloadmodule | tail --lines="${reload_verbosity}" | ${catit}
            ;;
        *)
            printf "%s" "${usage_message}"
            exit 1
            ;;
        esac
        ${privup} systemctl restart power-profiles-daemon --no-pager --show-transaction
        printf "Patching process done. Exit %s\n" "$?"
        popd || return
    else
        [[ "${1}" != "" ]] && printf "%s\n" "Paramenters unknown." || printf "%s\n" "${usage_message}"
    fi

}
lll_kernel_patching "${@}"
