#!/bin/sh
# The QML tests of org.raye.setup and of the recovery key page of
# raye-first-run, without a build and without a display:
#   tests/ui/run-tests.sh
#
# The suite table of iso/tools said this one needed "qmltestrunner ...
# and the module has to be laid out by the build first". Half of that was
# never true: stage-module.sh lays the module out exactly as the package
# installs it, and it needs no build at all. The other half stopped being
# true the day qmltestrunner was installed, and nothing re-read the
# sentence. Measured 2026-11-06: 22 tests, all green, in 1.8 s.
#
# org.raye.ui comes from the installed raye-style when there is one, and
# from the theme repository next door otherwise. RAYE_UI_QML_DIR overrides
# both. Exits 77 (skip) when neither the runner nor org.raye.ui is there.
set -eu
top=$(cd "$(dirname "$0")/../.." && pwd)
cd "$top"

# -input is NOT a list: given twice, qmltestrunner keeps only the last
# file. Measured 2026-11-06: two -input arguments ran 8 checks instead of
# 43 and said nothing about the 35 it had dropped. So the whole folder is
# passed -- and because a folder hides a renamed file just as quietly,
# every tst_*.qml expected in it is named here.
for f in tst_setup.qml tst_firstrun.qml tst_pages.qml tst_disk.qml tst_user.qml; do
    if [ ! -f "$top/tests/ui/$f" ]; then
        echo "tests/ui/$f is gone: its checks would vanish without failing anything"
        exit 1
    fi
done
. "$top/tests/ui/find-qmltestrunner.sh"
raye_find_qmltestrunner

ui=${RAYE_UI_QML_DIR:-}
if [ -n "$ui" ]; then
    # An override says WHERE the module is. Wrong, it must not be quietly
    # swapped for whatever the search below finds: that tests another
    # module than the one asked for. tests/ui/CMakeLists.txt says the same.
    if [ ! -f "$ui/org/raye/ui/qmldir" ]; then
        echo "RAYE_UI_QML_DIR=$ui holds no org/raye/ui/qmldir"
        exit 77
    fi
else
    for c in "/usr/lib/$(dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null || echo x86_64-linux-gnu)/qt6/qml" \
             "$top/../theme/qml"; do
        if [ -f "$c/org/raye/ui/qmldir" ]; then ui=$c; break; fi
    done
    if [ -z "$ui" ]; then
        echo "org.raye.ui is nowhere to be found: install raye-style, check the"
        echo "theme repository out next door, or set RAYE_UI_QML_DIR"
        exit 77
    fi
fi

stage=$(mktemp -d "${TMPDIR:-/tmp}/raye-setup-qml.XXXXXX")
trap 'rm -r -f -- "$stage"' EXIT INT TERM
sh "$top/tests/ui/stage-module.sh" "$stage"
# The whole locale is pinned, not LANG alone: Qt.locale() follows LANGUAGE
# first, and a caller with LANGUAGE=en (iso/tools/raye-tests sets it) made
# the French summary name English as the language (2026-11-08).
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software LANG=C.UTF-8 LC_ALL=C.UTF-8 LANGUAGE= \
    QML_XHR_ALLOW_FILE_READ=1 exec "$QMLTESTRUNNER" -input "$top/tests/ui" \
    -import "$top/tests/ui/fakes" -import "$stage" -import "$ui"
