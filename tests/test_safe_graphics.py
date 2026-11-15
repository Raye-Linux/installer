# SPDX-License-Identifier: GPL-3.0-or-later
"""raye-safe-graphics: an install started with "Safe graphics" keeps it.

Reported on an AMD RX 550: the install USB starts only with its "Safe
graphics" entry (nomodeset), the install goes through, and the installed
system then starts without nomodeset and the screen stays black. The
script runs with the live session's /proc/cmdline and the new system's
files; here both are stand-ins under tmp_path, and update-grub is a stub
that records whether it ran.
"""
import os
import pathlib
import subprocess

REPO = pathlib.Path(__file__).parent.parent
SCRIPT = REPO / "usr/libexec/raye-safe-graphics"
ETC = REPO / "etc/calamares"

DROPIN = "etc/default/grub.d/90-raye-safe-graphics.cfg"
LIVE_SAFE = ("BOOT_IMAGE=/casper/vmlinuz boot=casper noprompt nomodeset "
             "quiet splash ---")
LIVE_NORMAL = "BOOT_IMAGE=/casper/vmlinuz boot=casper noprompt quiet splash ---"


def run(tmp_path, cmdline, grub_exit=0):
    root = tmp_path / "target"
    root.mkdir(exist_ok=True)
    (tmp_path / "cmdline").write_text(cmdline + "\n")
    stub = tmp_path / "update-grub"
    stub.write_text(f'#!/bin/sh\necho run >> "{tmp_path}/runs"\nexit {grub_exit}\n')
    stub.chmod(0o755)
    env = dict(os.environ, RAYE_ROOT=str(root), RAYE_CMDLINE=str(tmp_path / "cmdline"),
               RAYE_UPDATE_GRUB=str(stub))
    r = subprocess.run(["sh", str(SCRIPT)], env=env, capture_output=True, text=True)
    runs = tmp_path / "runs"
    return r, root, len(runs.read_text().splitlines()) if runs.exists() else 0


def cmdline_after(root, before):
    """GRUB_CMDLINE_LINUX_DEFAULT once 50-raye.cfg (here: before) and the
    drop-in are sourced, in that order, as grub-mkconfig does."""
    out = subprocess.run(
        ["sh", "-c", 'GRUB_CMDLINE_LINUX_DEFAULT="$1"; . "$2"; '
         'printf %s "$GRUB_CMDLINE_LINUX_DEFAULT"', "sh", before, str(root / DROPIN)],
        capture_output=True, text=True, check=True)
    return out.stdout.split()


def test_safe_graphics_live_session_keeps_nomodeset(tmp_path):
    r, root, runs = run(tmp_path, LIVE_SAFE)
    assert r.returncode == 0, r.stderr
    assert (root / DROPIN).is_file()
    assert cmdline_after(root, "quiet splash loglevel=3") == [
        "quiet", "splash", "loglevel=3", "nomodeset"]
    # the menu is written again, or nomodeset waits for the next kernel
    assert runs == 1


def test_normal_live_session_changes_nothing(tmp_path):
    r, root, runs = run(tmp_path, LIVE_NORMAL)
    assert r.returncode == 0
    assert not (root / "etc").exists()
    assert runs == 0


def test_only_the_whole_word_counts(tmp_path):
    # nomodeset is a kernel word; something that merely contains it is not
    r, root, runs = run(tmp_path, "quiet splash raye.nomodeset_hint=1")
    assert not (root / DROPIN).exists() and runs == 0


def test_nomodeset_only_once(tmp_path):
    r, root, _ = run(tmp_path, LIVE_SAFE)
    assert cmdline_after(root, "quiet nomodeset splash").count("nomodeset") == 1


def test_dropin_sorts_after_the_raye_command_line(tmp_path):
    # 50-raye.cfg (raye-base) sets GRUB_CMDLINE_LINUX_DEFAULT outright; a
    # drop-in read before it would be overwritten
    assert pathlib.PurePath(DROPIN).name > "50-raye.cfg"


def test_failed_update_grub_is_reported(tmp_path):
    r, root, runs = run(tmp_path, LIVE_SAFE, grub_exit=1)
    assert r.returncode != 0
    # the drop-in stays: the next kernel update writes the menu with it
    assert (root / DROPIN).is_file()


def test_runs_after_the_boot_loader_and_cannot_fail_the_install():
    text = (ETC / "settings.conf").read_text()
    exec_part = text.split("- exec:", 1)[1].split("- show:", 1)[0]
    steps = [l.strip().lstrip("- ").strip()
             for l in exec_part.splitlines() if l.strip().startswith("-")]
    assert "shellprocess@raye_safe_graphics" in steps, steps
    # after bootloader, which writes grub.cfg; before packages, which
    # removes the installer (and this script) from the new system
    assert steps.index("shellprocess@raye_safe_graphics") > steps.index("bootloader")
    assert steps.index("shellprocess@raye_safe_graphics") < steps.index("packages")
    assert "config: shellprocess_raye_safe_graphics.conf" in text
    conf = (ETC / "modules/shellprocess_raye_safe_graphics.conf").read_text()
    assert '"-/usr/libexec/raye-safe-graphics"' in conf
    # in the new system: /proc/cmdline there is still the live session's
    assert "dontChroot: false" in conf


def test_shipped_and_executable():
    paths = (REPO / "debian/raye-paths").read_text().split()
    assert "usr/libexec/raye-safe-graphics" in paths
    assert os.access(SCRIPT, os.X_OK)
