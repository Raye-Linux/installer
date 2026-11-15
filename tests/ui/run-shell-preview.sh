#!/bin/sh
# Shows a whole Raye Setup screen with tests/ui/shell-preview.qml on $DISPLAY.
#   tests/ui/run-shell-preview.sh Disk.qml disk encrypted [fr_CA.UTF-8]
set -eu
top=$(cd "$(dirname "$0")/../.." && pwd)
ui=${RAYE_UI_QML_DIR:-$top/../theme/qml}
stage=$(mktemp -d "${TMPDIR:-/tmp}/raye-setup-qml.XXXXXX")
trap 'rm -r -f -- "$stage"' EXIT INT TERM
sh "$top/tests/ui/stage-module.sh" "$stage"
LANG=${4:-en_US.UTF-8} LANGUAGE= LC_ALL=${4:-en_US.UTF-8} QT_QUICK_BACKEND=software QML_XHR_ALLOW_FILE_READ=1 \
    qml6 -I "$top/tests/ui/fakes" -I "$stage" -I "$ui" \
    "$top/tests/ui/shell-preview.qml" -- "$1" "$2" "$3"
