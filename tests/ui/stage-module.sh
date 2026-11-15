#!/bin/sh
# Lays org.raye.setup out the way the package installs it, pictures in
# the module folder, under <dest>/org/raye/setup.
#   tests/ui/stage-module.sh <dest>
set -eu
top=$(cd "$(dirname "$0")/../.." && pwd)
dest=${1:?usage: stage-module.sh <dest>}
mkdir -p "$dest/org/raye"
target="$dest/org/raye/setup"
[ ! -e "$target" ] || [ -d "$target" ] || { echo "$target is not a folder" >&2; exit 1; }
mkdir -p "$target/illustrations"
cp "$top"/qml/org/raye/setup/*.qml "$top"/qml/org/raye/setup/qmldir "$target/"
cp "$top"/assets/illustrations/*.png "$target/illustrations/"
