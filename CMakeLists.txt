# Raye Linux installer: the setup app (raye-setup) and the welcome after
# the first sign-in (raye-first-run). Everything else in this repo is
# shipped as is; debian/raye-paths says where each file goes.
cmake_minimum_required(VERSION 3.25)
project(raye-installer LANGUAGES CXX)

include(GNUInstallDirs)
option(BUILD_TESTING "Build and run the tests" ON)
# Every "?" line of debian/raye-paths must then point at a file that
# exists. NOTHING sets it: measured 2026-11-06, iso/build.sh builds this
# package with `dpkg-buildpackage -b -us -uc` behind `env -i` and passes no
# -DRAYE_RELEASE, so turning it on is a deliberate act. The gate is run by
# `iso/tools/raye-tests --release`, which calls debian/raye_paths.py with
# RAYE_PATHS_STRICT=1 and never goes through CMake at all. What keeps the
# count in front of us in the ordinary run is the OWED figure of
# debian/test_raye_paths.py, not this option.
option(RAYE_RELEASE "Everything the packaging list names has to be there" OFF)
if(BUILD_TESTING)
    enable_testing()
endif()

# Where the apps find org.raye.setup when run from the source tree.
set(RAYE_SETUP_QML_DIR "${CMAKE_CURRENT_SOURCE_DIR}/qml")

# Each part comes with its own CMakeLists.txt; a part that is not written
# yet is skipped, so the rest still builds.
set(RAYE_PARTS app/setup app/firstrun tests/setup tests/firstrun tests/ui)
set(raye_found_parts)
foreach(part IN LISTS RAYE_PARTS)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${part}/CMakeLists.txt")
        list(APPEND raye_found_parts ${part})
    else()
        message(STATUS "${part}: not there yet, skipped")
    endif()
endforeach()

if(raye_found_parts)
    find_package(Qt6 6.8 REQUIRED COMPONENTS Core)
    qt_standard_project_setup(REQUIRES 6.8)
    set(CMAKE_CXX_STANDARD 20)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
    foreach(part IN LISTS raye_found_parts)
        add_subdirectory(${part})
    endforeach()
endif()

# The Python tests: Calamares job modules and the packaging list.
if(BUILD_TESTING)
    find_package(Python3 COMPONENTS Interpreter)
    if(Python3_FOUND)
        execute_process(COMMAND ${Python3_EXECUTABLE} -c "import pytest"
                        RESULT_VARIABLE raye_no_pytest OUTPUT_QUIET ERROR_QUIET)
    endif()
    if(Python3_FOUND AND raye_no_pytest EQUAL 0)
        add_test(NAME python
                 COMMAND ${Python3_EXECUTABLE} -m pytest -q -p no:cacheprovider
                         tests debian/test_raye_paths.py
                 WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
        set_tests_properties(python PROPERTIES ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")

        # Nothing else ever runs the strict mode, so a half-written tree
        # would reach an image without a word. The image build turns this on.
        if(RAYE_RELEASE)
            add_test(NAME paths-strict
                     COMMAND ${Python3_EXECUTABLE} debian/raye_paths.py check
                     WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
            set_tests_properties(paths-strict PROPERTIES
                                 ENVIRONMENT "RAYE_PATHS_STRICT=1;PYTHONDONTWRITEBYTECODE=1")
        endif()
    else()
        message(FATAL_ERROR "python3-pytest is missing: the Python tests cannot run")
    endif()

    # There was a second registration here, for tests/test_session.sh,
    # wrapped in if(EXISTS ...). That file HAS NEVER EXISTED in this repository
    # -- `git log --diff-filter=D -- tests/test_session.sh` finds no deletion,
    # so it was never added either. The live session check is tests/test_session.py,
    # and the pytest run above already collects it with the rest of tests/.
    #
    # The lesson is the guard, not the typo. if(EXISTS) around an add_test()
    # reads like care and behaves like silence: the test never registered, ctest
    # never missed it, and nothing anywhere said a check was absent. A path that
    # is expected to exist must be named without a guard, so CMake fails loudly
    # when it moves. Found on 2026-11-06 by the first run of iso/tools/raye-tests.
endif()
