# SPDX-License-Identifier: GPL-3.0-or-later
"""tests/ui/run-tests.sh: the launcher's way into the QML test.

It is the twin of add_test(qml-setup) in tests/ui/CMakeLists.txt, and the
two must answer the same way to the same tree -- the installer already
paid for a pair of files that drifted apart (two copies of one file). The one input a test can force is RAYE_UI_QML_DIR.
"""
import pathlib
import subprocess

import pytest

TOP = pathlib.Path(__file__).resolve().parents[2]


def test_an_override_with_no_module_is_a_named_skip(tmp_path):
    """Pointed at a folder holding no org/raye/ui the script used to fall
    back to the search and test a module other than the one asked for, or
    run the runner against nothing and die on an import error no one reads
    as "wrong path". 77 is ctest's skip code, which tools/raye-tests
    honours as a named skip with the last line as the reason.
    """
    done = subprocess.run(["sh", str(TOP / "tests/ui/run-tests.sh")],
                          cwd=TOP, capture_output=True, text=True,
                          env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                               "RAYE_UI_QML_DIR": str(tmp_path / "no-module")})
    output = done.stdout + done.stderr
    # This guard first read "names qmltestrunner and not RAYE_UI_QML_DIR",
    # and the old script -- which fell back to the search and RAN the real
    # test -- printed "Start testing of qmltestrunner": the guard turned the
    # regression into a skip and the proof into silence. A skip is only a
    # skip when the script actually skipped, which means exit 77.
    if done.returncode == 77 and "RAYE_UI_QML_DIR" not in output:
        pytest.skip("no working qmltestrunner here: " + output.strip().splitlines()[-1])
    assert done.returncode == 77, f"exit {done.returncode}, output: {output.strip()}"
    assert "RAYE_UI_QML_DIR" in output and "org/raye/ui" in output, output.strip()
