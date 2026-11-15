#!/bin/sh
# Shows tests/ui/gallery.qml with the module laid out as installed.
#   tests/ui/run-gallery.sh [--fr] [--page controls|pictures|frame|edge] [--reduced]
# org.raye.ui comes from the system, or from RAYE_UI_QML_DIR (the qml
# folder of the theme source, ../theme/qml when it sits next to this repo).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
top=$(cd "$here/../.." && pwd)
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT INT TERM
"$here/stage-module.sh" "$stage"
ui=${RAYE_UI_QML_DIR:-}
if [ -z "$ui" ] && [ -f "$top/../theme/qml/org/raye/ui/qmldir" ]; then
    ui="$top/../theme/qml"
fi
QML_IMPORT_PATH="$stage${ui:+:$ui}${QML_IMPORT_PATH:+:$QML_IMPORT_PATH}" \
    qml6 "$here/gallery.qml" -- "$@"
