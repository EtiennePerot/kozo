#!/usr/bin/env bash

set -e

rootDir="$(dirname "$(dirname "$(dirname "$BASH_SOURCE")")")"
cd "$rootDir"
exec ./kozo testnets/bluetoothnet/config.yml node2
