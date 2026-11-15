# The QML test of org.raye.setup (focus order, states, pictures, page
# entrance). The module is laid out the way the package installs it
# under the build folder, then qmltestrunner runs tst_setup.qml on the
# offscreen platform.
#
# It needs org.raye.ui (raye-style) and the QML modules of QtTest,
# QtQuick.Shapes and Kirigami. When a piece is missing the test is
# registered as a SKIP that names what is missing -- never left out: point
# RAYE_UI_QML_DIR at the qml folder of the theme source to run it anyway.
#
# Until 2026-11-06 a missing piece made this file return() with one
# message(STATUS), and the package build is exactly where every piece is
# missing: iso/build.sh wipes the build tree and copies ONE repository
# into it, so there is no sibling theme checkout, and raye-style is not a
# Build-Depends, so the module is not installed either. Measured that day,
# on a copy of the source with no sibling: `ctest -N` listed ONE test,
# `python`. These 22 checks had never run in the package build, and
# CTEST_NO_TESTS_ACTION=error cannot catch it -- it only fires on a run
# with NO test at all. The rule this tree lives by is that a check which
# cannot run says so and is never read as a pass; ctest honours it through
# SKIP_REGULAR_EXPRESSION, so the reason lands in the build log's summary.

if(NOT BUILD_TESTING)
    return()
endif()

function(raye_qml_setup_skipped reason)
    add_test(NAME qml-setup COMMAND ${CMAKE_COMMAND} -E echo
             "SKIPPED: the QML test of org.raye.setup did not run: ${reason}")
    set_tests_properties(qml-setup PROPERTIES SKIP_REGULAR_EXPRESSION "SKIPPED:")
endfunction()

find_program(RAYE_QMLTESTRUNNER qmltestrunner
             HINTS "${QT6_INSTALL_PREFIX}/${QT6_INSTALL_BINS}" /usr/lib/qt6/bin)

set(RAYE_UI_QML_DIR "" CACHE PATH "Folder holding org/raye/ui (the theme's qml folder)")
set(raye_ui_dir "${RAYE_UI_QML_DIR}")
set(raye_ui_why "org.raye.ui is nowhere: install raye-style, or set RAYE_UI_QML_DIR to the theme's qml folder")
if(raye_ui_dir)
    # An override says WHERE the module is. Wrong, it must NOT be quietly
    # swapped for whatever the search below finds: that would test another
    # module than the one asked for, and the mistake would never surface.
    # Taken on trust it registered a test that could only die on an import
    # error no one reads as "wrong path".
    if(NOT EXISTS "${raye_ui_dir}/org/raye/ui/qmldir")
        set(raye_ui_why "RAYE_UI_QML_DIR=${raye_ui_dir} holds no org/raye/ui/qmldir")
        set(raye_ui_dir "")
    endif()
else()
    foreach(candidate
            "/usr/lib/${CMAKE_LIBRARY_ARCHITECTURE}/qt6/qml"
            "${CMAKE_SOURCE_DIR}/../theme/qml")
        if(EXISTS "${candidate}/org/raye/ui/qmldir")
            set(raye_ui_dir "${candidate}")
            break()
        endif()
    endforeach()
endif()

set(stage "${CMAKE_CURRENT_BINARY_DIR}/qml")
file(GLOB raye_setup_qml CONFIGURE_DEPENDS
     "${CMAKE_SOURCE_DIR}/qml/org/raye/setup/*.qml"
     "${CMAKE_SOURCE_DIR}/qml/org/raye/setup/qmldir")
file(GLOB raye_setup_pictures CONFIGURE_DEPENDS
     "${CMAKE_SOURCE_DIR}/assets/illustrations/*.png")
add_custom_command(
    OUTPUT "${stage}/org/raye/setup/qmldir"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${stage}/org/raye/setup/illustrations"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${raye_setup_qml} "${stage}/org/raye/setup/"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${raye_setup_pictures} "${stage}/org/raye/setup/illustrations/"
    DEPENDS ${raye_setup_qml} ${raye_setup_pictures}
    COMMENT "Laying out org.raye.setup for the tests")
add_custom_target(raye-setup-qml-stage ALL DEPENDS "${stage}/org/raye/setup/qmldir")

if(NOT RAYE_QMLTESTRUNNER)
    raye_qml_setup_skipped("qmltestrunner is not installed (qt6-declarative-dev-tools)")
    return()
endif()
if(NOT raye_ui_dir)
    raye_qml_setup_skipped("${raye_ui_why}")
    return()
endif()

# One runner over this folder, so every tst_*.qml in it runs: the shared
# look (tst_setup.qml) and the recovery key page of raye-first-run
# (tst_firstrun.qml), which loads straight from app/firstrun/qml and needs
# no build -- the page takes its key as a property.
#
# -input is NOT a list. Passing it twice keeps only the LAST file:
# measured 2026-11-06, two -input arguments ran 8 checks instead of 43,
# and the 22 checks of tst_setup.qml had gone without one word about it.
# Hence the folder -- and hence the FATAL_ERROR below, because a folder
# hides the opposite mistake: a renamed or deleted file simply stops
# being found, and the suite stays green on fewer checks. Both files are
# named here so CMake stops when one moves.
foreach(raye_qml_test tst_setup.qml tst_firstrun.qml tst_pages.qml tst_disk.qml tst_user.qml)
    if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${raye_qml_test}")
        message(FATAL_ERROR "tests/ui/${raye_qml_test} is gone: the runner takes the \
whole folder, so its checks would vanish without failing anything")
    endif()
endforeach()

add_test(NAME qml-setup
         COMMAND ${RAYE_QMLTESTRUNNER}
                 -input "${CMAKE_CURRENT_SOURCE_DIR}"
                 -import "${CMAKE_CURRENT_SOURCE_DIR}/fakes"
                 -import "${stage}" -import "${raye_ui_dir}")
set_tests_properties(qml-setup PROPERTIES
    ENVIRONMENT "QT_QPA_PLATFORM=offscreen;QT_QUICK_BACKEND=software;LANG=C.UTF-8;LC_ALL=C.UTF-8;LANGUAGE=;QML_XHR_ALLOW_FILE_READ=1")
