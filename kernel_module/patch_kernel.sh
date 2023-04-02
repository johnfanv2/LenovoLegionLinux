#!/usr/bin/env bash

# Checks for doas, sudo, bat and cat first
# Runs make and restarts power-profiles-daemon

kernel_patching() {

 	LC_ALL=C
	LANG=C

	local krn_dir
	local privup
	local catit
	local -i reload_verbosity

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
	reload_verbosity=1

	printf "Starting patching process for kernel-%s\n\n" "$(uname -r)"

	pushd "${krn_dir}" || return
	make
	${privup} make install
	${privup} make reloadmodule | tail --lines="${reload_verbosity}" | ${catit}
	${privup} systemctl restart power-profiles-daemon --no-pager --show-transaction
	popd || return
	
	printf "\n%s %s\n" "Patching process done. Exit %s" "$?"

}

kernel_patching
