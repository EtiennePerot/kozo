#!/usr/bin/env bash

set -e

rootDir="$(dirname "$(dirname "$BASH_SOURCE")")"
mkdir -p "$HOME/.tmuxinator"
echo "project_root: $rootDir" > "$HOME/.tmuxinator/kozo-testnet.yml"
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
cat testnet/tmuxinator.yml | sed "s/PAGERGOESHERE/$pager/g" >> "$HOME/.tmuxinator/kozo-testnet.yml"
exec tmuxinator kozo-testnet
