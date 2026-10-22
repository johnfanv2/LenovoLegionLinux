#!/bin/bash
# Print the kernel version the external module should be built against for the
# given test/CI script.
#
# On a normal system this is the running kernel. Containers share the host's
# kernel but carry their own /lib/modules, so an image that installs its own
# headers (deploy/Dockerfile.ubuntu.24.04) has no headers for the kernel that
# `uname -r` reports; the module then has to be built against the one kernel
# installed in the image. Building for the running kernel stays the default,
# so nothing changes on a real system, where a module built for any other
# kernel could not be loaded.
set -eu

running_version=$(uname -r)
if [ -d "/lib/modules/$running_version/build" ]; then
	echo "$running_version"
	exit 0
fi

installed_versions=()
for build_dir in /lib/modules/*/build; do
	[ -d "$build_dir" ] || continue
	installed_versions+=("$(basename "$(dirname "$build_dir")")")
done

if [ "${#installed_versions[@]}" -eq 1 ]; then
	echo "${installed_versions[0]}"
	exit 0
fi

echo "No kernel headers for the running kernel $running_version, and not" \
	"exactly one kernel with headers installed (found:" \
	"${installed_versions[*]:-none});" \
	"install linux-headers-$running_version." >&2
exit 1
