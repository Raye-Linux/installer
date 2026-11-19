# SPDX-License-Identifier: GPL-3.0-or-later
"""The new system's apt lists get the country mirror before the first boot.

raye-ubuntu-mirrors (raye-system) reads the time zone, so it has to run
after localecfg wrote it, and before anything in the new system downloads
packages (raye_drivers, packages). A failure must not stop the install:
the same script runs again before every apt update.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).parent.parent
ETC = REPO / "etc/calamares"
BASE_PATHS = REPO.parent / "iso/packages/raye-base/debian/raye-release-paths"


def exec_steps():
    steps, inside = [], False
    for line in (ETC / "settings.conf").read_text().splitlines():
        if line.strip() == "- exec:":
            inside = True
            continue
        if inside:
            m = re.match(r"^  - (\S+)$", line)
            if m:
                steps.append(m.group(1))
            elif line.startswith("- "):
                break
    return steps


def test_the_step_is_declared_and_runs_after_the_time_zone():
    conf = (ETC / "settings.conf").read_text()
    assert re.search(r"- id: raye_mirrors\n  module: shellprocess\n"
                     r"  config: shellprocess_raye_mirrors.conf\n", conf)
    steps = exec_steps()
    assert "shellprocess@raye_mirrors" in steps
    at = steps.index("shellprocess@raye_mirrors")
    assert steps.index("localecfg") < at
    for later in ("shellprocess@raye_drivers", "packages"):
        assert at < steps.index(later)


def test_it_runs_in_the_new_system_and_cannot_stop_the_install():
    text = (ETC / "modules/shellprocess_raye_mirrors.conf").read_text()
    assert re.search(r"^dontChroot: false$", text, re.M)
    scripts = re.findall(r'^\s+- "(.*)"$', text, re.M)
    assert scripts == ["-/usr/libexec/raye-ubuntu-mirrors"]


def test_the_script_is_where_raye_system_puts_it():
    if not BASE_PATHS.exists():
        import pytest
        pytest.skip("raye-base is not next to this repo")
    assert re.search(r"^raye-system\s+release/apt/raye-ubuntu-mirrors\s+"
                     r"usr/libexec/raye-ubuntu-mirrors$", BASE_PATHS.read_text(), re.M)
