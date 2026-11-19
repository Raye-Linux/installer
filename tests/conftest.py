# SPDX-License-Identifier: GPL-3.0-or-later
import pytest


@pytest.fixture(autouse=True)
def look_dir_of_the_test(tmp_path, monkeypatch):
    # the probe mounts other systems' volumes under root's folder in /run
    monkeypatch.setenv("RAYE_LOOK_DIR", str(tmp_path / "look"))
