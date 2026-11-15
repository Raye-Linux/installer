#!/bin/sh
# Shows a page of Raye Setup with tests/ui/page-preview.qml on $DISPLAY.
#   tests/ui/run-page-preview.sh Ready.qml ready encrypted [fr_CA]
# org.raye.ui comes from RAYE_UI_QML_DIR, or the theme repository next door.
set -eu
top=$(cd "$(dirname "$0")/../.." && pwd)
ui=${RAYE_UI_QML_DIR:-$top/../theme/qml}
stage=$(mktemp -d "${TMPDIR:-/tmp}/raye-setup-qml.XXXXXX")
trap 'rm -r -f -- "$stage"' EXIT INT TERM
sh "$top/tests/ui/stage-module.sh" "$stage"
LANG=${4:-en_US.UTF-8} QT_QUICK_BACKEND=software QML_XHR_ALLOW_FILE_READ=1 \
    qml6 -I "$top/tests/ui/fakes" -I "$stage" -I "$ui" \
    "$top/tests/ui/page-preview.qml" -- "$1" "$2" "$3"
