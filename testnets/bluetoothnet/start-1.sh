#!/usr/bin/env bash

set -e

rootDir="$(dirname "$(dirname "$(dirname "$BASH_SOURCE")")")"
exec ./kozo testnets/bluetoothnet/config.yml node1
