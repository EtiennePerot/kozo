#!/usr/bin/env bash

set -e

rootDir="$(dirname "$(dirname "$(dirname "$BASH_SOURCE")")")"
mkdir -p "$HOME/.tmuxinator"
echo "project_root: $rootDir" > "$HOME/.tmuxinator/kozo-onionnet.yml"
# Detect pager
pager=''
if [ -n "$PAGER" ]; then
	if hash "$PAGER"; then
		pager="$PAGER"
	fi
fi
if [ -z "$pager" ]; then
	for p in most less more ipager reed; do
		if hash "$p"; then
			pager="$p"
			break
		fi
	done
fi
if [ -z "$pager" ]; then
	pager=cat
fi
if [ ! -f testnets/onionnet/config.yml ]; then
	echo "Config file does not exist: 'testnets/onionnet/config.yml'"
	exit 1
fi
cat testnets/onionnet/tmuxinator.yml | sed "s/PAGERGOESHERE/$pager/g" >> "$HOME/.tmuxinator/kozo-onionnet.yml"
echo 'Warning: This will only work if you properly set up Tor, transparent .onion DNS resolution/proxying, the 2 hidden services, and update config.yml to match.'
sleep 3
exec tmuxinator kozo-onionnet
