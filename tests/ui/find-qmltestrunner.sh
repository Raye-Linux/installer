# Sourced, not run. Sets QMLTESTRUNNER, or exits 77 (ctest's skip code,
# which tools/raye-tests honours as a named skip with the last line as the
# reason).
#
# THIS FILE IS A TWIN of theme/tests/find-qmltestrunner.sh. Correct one
# and correct the other. It is duplicated rather than shared because the
# two repositories are packaged separately: the installer's own package
# build has to find the runner without the theme being checked out.
#
# Two traps, and PATH walks into both.
#
# 1. Debian puts the binary in /usr/lib/qt6/bin, which is NOT on PATH,
#    while Ubuntu -- the base Raye is built on -- has something called
#    qmltestrunner on PATH. Asking only `command -v` says "not installed"
#    on Debian about a binary that is installed.
#
# 2. And the thing on Ubuntu's PATH is a **symlink to qtchooser**, which
#    defaults to Qt 5 and fails outright:
#      $ /usr/bin/qmltestrunner -help
#      qmltestrunner: could not exec '/usr/lib/qt5/bin/qmltestrunner'
#      exit 1
#    Measured 2026-11-06 in the resolute chroot. Trusting PATH does not
#    merely find the wrong Qt: on the platform Raye ships on it finds a
#    binary that cannot run at all.
#
# Hence: the Qt 6 directories FIRST, PATH last, and every candidate is
# PROVED to work -- `-help` exits 0 on the real runner and 1 on the
# wrapper. Existing and being executable is not the same as working.
RAYE_QT_BIN_DIRS_DEFAULT="/usr/lib/qt6/bin /usr/lib/x86_64-linux-gnu/qt6/bin
/usr/lib/aarch64-linux-gnu/qt6/bin /usr/lib64/qt6/bin /usr/local/lib/qt6/bin"

raye_qmltestrunner_works() {
    [ -x "$1" ] || return 1
    QT_QPA_PLATFORM=offscreen "$1" -help >/dev/null 2>&1
}

raye_find_qmltestrunner() {
    if [ -n "${QMLTESTRUNNER:-}" ]; then
        raye_qmltestrunner_works "$QMLTESTRUNNER" && return 0
        QMLTESTRUNNER=
    fi
    for _d in ${RAYE_QT_BIN_DIRS-$RAYE_QT_BIN_DIRS_DEFAULT}; do
        if raye_qmltestrunner_works "$_d/qmltestrunner"; then
            QMLTESTRUNNER=$_d/qmltestrunner; return 0
        fi
    done
    if command -v qmake6 >/dev/null 2>&1; then
        for _q in QT_INSTALL_LIBEXECS QT_INSTALL_BINS; do
            _d=$(qmake6 -query "$_q" 2>/dev/null) || _d=
            if [ -n "$_d" ] && raye_qmltestrunner_works "$_d/qmltestrunner"; then
                QMLTESTRUNNER=$_d/qmltestrunner; return 0
            fi
        done
    fi
    _d=$(command -v qmltestrunner 2>/dev/null) || _d=
    if [ -n "$_d" ] && raye_qmltestrunner_works "$_d"; then
        QMLTESTRUNNER=$_d; return 0
    fi
    echo "no working qmltestrunner (looked in the Qt 6 bin directories, at"
    echo "what qmake6 reports, and on PATH; a candidate must answer -help)"
    exit 77
}
