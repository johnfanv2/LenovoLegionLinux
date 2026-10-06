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
# fall back to the upstream copy there. Retry hard and walk a mirror list:
# raw.githubusercontent.com occasionally answers 429/5xx on CI runners, and
# wget does not retry HTTP error responses by default (it exits with code 8),
# which used to flake the container build.
KSRC="/lib/modules/$(uname -r)/build"
if [ -f "${KSRC}/scripts/checkpatch.pl" ]; then
	cp "${KSRC}/scripts/checkpatch.pl" "checkpatch.pl"
	# checkpatch looks for its data files next to the script; best effort
	cp "${KSRC}/scripts/spelling.txt" "spelling.txt" 2>/dev/null || true
	cp "${KSRC}/scripts/const_structs.checkpatch" \
		"const_structs.checkpatch" 2>/dev/null || true
else
	urls=(
		"https://raw.githubusercontent.com/torvalds/linux/master/scripts/checkpatch.pl"
		"https://cdn.jsdelivr.net/gh/torvalds/linux@master/scripts/checkpatch.pl"
		"https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/scripts/checkpatch.pl"
	)
	for url in "${urls[@]}"; do
		if wget -q --tries=5 --waitretry=5 --timeout=30 \
			--retry-on-http-error=429,500,502,503,504 \
			-O "checkpatch.pl" "${url}" && [ -s "checkpatch.pl" ] &&
			head -n 1 "checkpatch.pl" | grep -q perl; then
			break
		fi
		rm -f "checkpatch.pl"
	done
	if [ ! -s "checkpatch.pl" ]; then
		echo "Failed to download checkpatch.pl from all mirrors" >&2
		exit 1
	fi
	# checkpatch looks for its data files next to the script; best effort
	base="${url%checkpatch.pl}"
	wget -q --tries=3 --timeout=30 -O "spelling.txt" \
		"${base}spelling.txt" || rm -f "spelling.txt"
	wget -q --tries=3 --timeout=30 -O "const_structs.checkpatch" \
		"${base}const_structs.checkpatch" || rm -f "const_structs.checkpatch"
fi

chmod 755 "checkpatch.pl"
