# SPDX-License-Identifier: GPL-3.0-or-later
"""The pieces around the desktop choice that are not the job itself: the
flag the page reads, the result the last page reads, and the packaging."""
import os
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUN_TEXT = (ROOT / "usr/libexec/raye-setup-run").read_text()
BRANDING = ROOT / "etc/calamares/branding/raye"
HELPER = ROOT / "usr/libexec/raye-setup-private"


def shell_function(name):
    lines = RUN_TEXT.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(f"{name}() {{"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "}")
    return "\n".join(lines[start:end + 1]) + "\n"


def offline(pool):
    script = shell_function("hyprland_offline") + "hyprland_offline && echo 1 || echo 0\n"
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "RAYE_DESKTOP_POOL": str(pool)})
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def test_flag_says_offline_when_the_stick_carries_hyprland(tmp_path):
    (tmp_path / "Packages").write_text("Package: hyprland\n\nPackage: raye-hyprland\nVersion: 1\n")
    assert offline(tmp_path) == "1"


def test_flag_says_online_without_the_pool(tmp_path):
    assert offline(tmp_path / "none") == "0"


def test_flag_wants_the_package_itself_not_a_lookalike(tmp_path):
    (tmp_path / "Packages").write_text("Package: raye-hyprland-extras\n")
    assert offline(tmp_path) == "0"


def test_flag_is_written_for_the_pages():
    block = RUN_TEXT[RUN_TEXT.index('} > "$dir/flags"') - 600:RUN_TEXT.index('} > "$dir/flags"')]
    assert "hyprland_offline=" in block


def test_flag_and_job_look_in_the_same_place():
    conf = (ROOT / "etc/calamares/modules/rayedesktop.conf").read_text()
    pool = re.search(r"^pool: (\S+)$", conf, re.M).group(1)
    assert f"RAYE_DESKTOP_POOL:-{pool}" in shell_function("hyprland_offline")


@pytest.mark.skipif(os.geteuid() != 0, reason="the helper hands its folder to root: it only runs as root")
def test_a_new_setup_forgets_the_last_desktop_result(tmp_path):
    folder = tmp_path / "root-only"
    subprocess.run([str(HELPER), "prepare", str(folder)], check=True)
    (folder / "desktop-result").write_text("plasma-fallback\n")
    subprocess.run([str(HELPER), "prepare", str(folder)], check=True)
    assert not (folder / "desktop-result").exists()


def test_last_page_reads_the_desktop_result():
    done = (BRANDING / "pages/Done.qml").read_text()
    assert 'readPrivate("desktop-result"' in done


def test_the_job_and_its_settings_are_shipped():
    paths = (ROOT / "debian/raye-paths").read_text()
    assert re.search(r"^calamares-settings-raye  usr/lib/calamares/modules/rayedesktop$", paths, re.M)
    # etc/calamares as a whole ships the module's .conf
    assert re.search(r"^calamares-settings-raye  etc/calamares$", paths, re.M)
