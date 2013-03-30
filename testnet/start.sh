#!/usr/bin/env bash

set -e

rootDir="$(dirname "$(dirname "$BASH_SOURCE")")"
mkdir -p "$HOME/.tmuxinator"
echo "project_root: $rootDir" > "$HOME/.tmuxinator/kozo-testnet.yml"
cat testnet/tmuxinator.yml >> "$HOME/.tmuxinator/kozo-testnet.yml"
exec tmuxinator kozo-testnet
