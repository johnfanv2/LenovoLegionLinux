#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd "${DIR}/../install_dir"

# Prefer the checkpatch.pl that ships with the kernel headers this module is
# built against. It is version matched to the tree being compiled for, it is
# already present wherever the module can actually be built, and - unlike the
# download - it needs no network access, so it cannot fail on a transient
# error or a rate limit.
#
# The container builds run this before the kernel headers are installed, so
# fall back to the upstream copy there, with retries.
KSRC="/lib/modules/$(uname -r)/build"
if [ -f "${KSRC}/scripts/checkpatch.pl" ]; then
	cp "${KSRC}/scripts/checkpatch.pl" "checkpatch.pl"
else
	wget -q --tries=3 --waitretry=2 --timeout=30 \
		"https://raw.githubusercontent.com/torvalds/linux/master/scripts/checkpatch.pl"
fi

chmod 755 "checkpatch.pl"
