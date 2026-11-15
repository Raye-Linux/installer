# SPDX-License-Identifier: GPL-3.0-or-later
"""raye-preflight: what it says about a disk that already holds Windows.

Installing next to Windows means shrinking its volume, and the shrink is
ntfsresize. Both halves of that were measured on 2026-11-06 rather than
assumed:

  ntfs-3g 1:2022.10.3-5+deb13u3, strings over /usr/sbin/ntfsresize --
    "The NTFS partition is hibernated. Windows must be resumed and turned off"
    "The NTFS journal file is unclean. Please shutdown Windows properly"
    "Volume is scheduled for check. Run chkdsk /f and please try again"
    "NTFS is inconsistent. Run chkdsk /f on Windows then reboot it TWICE!"

  libkpmcore.so.24.12.3, UTF-16 literals -- "ntfsresize",
    "--no-progress-bar", "--force", "--size". KPMcore is what Calamares
    drives, and the ntfsresize manual says of that flag: "Forces ntfsresize
    to proceed ... if the filesystem is marked for consistency check."

So a volume Windows left dirty is not refused before the install. It is
argued with in the middle of one, while the partition table is being
rewritten. raye-preflight is the only place that can say so in time, and
until this file it read ONE of ntfs-3g.probe's twelve exit codes.

The codes are the probe's own, from ntfs-3g.probe(8):
  0 mountable  11 syntax  12 not NTFS  13 inconsistent/FakeRAID
  14 hibernated  15 unclean  16 in use  17 FakeRAID
  18 unknown  19 privilege  20 memory  21 FUSE

Every test here runs the real script with lsblk, ntfs-3g.probe, mount and
mktemp replaced on PATH, so no device and no filesystem is touched.
"""
import pathlib
import re
import subprocess

import pytest

REPO = pathlib.Path(__file__).parent.parent
PREFLIGHT = REPO / "usr/libexec/raye-preflight"

# one NTFS volume, the shape lsblk -rnpo PATH,FSTYPE,PARTTYPE prints
NTFS_DISK = "/dev/sda1 vfat ebd0a0a2-b9e5-4433-87c0-68b6b72699c7\n/dev/sda3 ntfs ebd0a0a2-b9e5-4433-87c0-68b6b72699c7\n"
ESP = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"


def run(tmp_path, table, probe=0, uid="0", esp_holds=None, no_probe=False):
    """raye-preflight with its tools stubbed. Returns its lines."""
    stub = tmp_path / "stub"
    stub.mkdir(exist_ok=True)

    def write(name, body):
        path = stub / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o755)

    write("id", f'echo {uid}\n')
    write("lsblk", "cat <<'EOF'\n" + table + "EOF\n")
    if not no_probe:
        write("ntfs-3g.probe", f"exit {probe}\n")
    # the ESP is never really mounted: mktemp hands out a folder of the
    # test, mount fills it in, umount and rmdir do nothing
    fake_esp = tmp_path / "esp"
    write("mktemp", f'mkdir -p "{fake_esp}"; echo "{fake_esp}"\n')
    if esp_holds is None:
        write("mount", "exit 1\n")
    else:
        write("mount", f'mkdir -p "{fake_esp}/EFI/{esp_holds}" && '
                       f'touch "{fake_esp}/EFI/{esp_holds}/grub.cfg"\n')
    write("umount", "exit 0\n")
    write("rmdir", "exit 0\n")

    done = subprocess.run(["sh", str(PREFLIGHT)], capture_output=True, text=True,
                          env={"PATH": f"{stub}:/usr/bin:/bin"})
    return done.returncode, [l for l in done.stdout.splitlines() if l.strip()]


def test_a_clean_windows_volume_says_nothing(tmp_path):
    code, lines = run(tmp_path, NTFS_DISK, probe=0)
    assert code == 0
    assert lines == []


# every exit code the probe documents, and what the person has to be told
PROBE = [
    (13, "ntfs-check"),     # inconsistent, or a FakeRAID set
    (14, "hibernated"),     # Fast Startup, or a real hibernation
    (15, "ntfs-dirty"),     # not cleanly unmounted
    (16, "ntfs-busy"),      # another driver or system holds it
    (17, "ntfs-check"),     # unsetup FakeRAID
    (11, "ntfs-unknown"),   # our own command line was wrong
    (12, "ntfs-unknown"),   # blkid says ntfs, libntfs-3g does not
    (18, "ntfs-unknown"),
    (19, "ntfs-unknown"),   # we run as root, so this is an anomaly
    (20, "ntfs-unknown"),
    (21, "ntfs-unknown"),
]
assert PROBE, "an empty table here would be reported as a skip, not a gap"


@pytest.mark.parametrize("probe,finding", PROBE)
def test_each_probe_code_is_named(tmp_path, probe, finding):
    code, lines = run(tmp_path, NTFS_DISK, probe=probe)
    assert code == 0
    assert lines == [f"{finding} /dev/sda3"], (probe, lines)


def test_a_state_nobody_listed_is_refused_rather_than_passed(tmp_path):
    """🚨 The point of ntfs-unknown. A volume whose state this script
    cannot name is exactly the one not to shrink, and the old script passed
    every code but 14 in silence.
    """
    for probe in (1, 22, 30, 42, 99):
        code, lines = run(tmp_path, NTFS_DISK, probe=probe)
        assert lines == ["ntfs-unknown /dev/sda3"], (probe, lines)


def test_no_probe_installed_is_not_a_clean_disk(tmp_path):
    """ntfs-3g.probe missing makes the shell exit 127. The old script read
    that as "not 14", which is to say "fine", and the install would have
    gone on to shrink a volume nothing had looked at.
    """
    code, lines = run(tmp_path, NTFS_DISK, no_probe=True)
    assert code == 0
    assert lines == ["ntfs-unknown /dev/sda3"], lines


def test_bitlocker_is_named_without_probing(tmp_path):
    code, lines = run(tmp_path, "/dev/sda3 BitLocker -\n", no_probe=True)
    assert lines == ["bitlocker /dev/sda3"], lines


def test_several_volumes_each_get_their_line(tmp_path):
    table = ("/dev/sda3 ntfs -\n/dev/sdb1 BitLocker -\n/dev/sdc1 ext4 -\n")
    code, lines = run(tmp_path, table, probe=15)
    assert lines == ["ntfs-dirty /dev/sda3", "bitlocker /dev/sdb1"], lines


def test_another_linux_owning_the_esp_is_named(tmp_path):
    code, lines = run(tmp_path, f"/dev/sda1 vfat {ESP}\n", no_probe=True,
                      esp_holds="ubuntu")
    assert lines == ["shared-efi /dev/sda1"], lines


def test_an_esp_of_our_own_family_only_is_left_alone(tmp_path):
    code, lines = run(tmp_path, f"/dev/sda1 vfat {ESP}\n", no_probe=True,
                      esp_holds="Microsoft")
    assert lines == [], lines


def test_a_vfat_partition_that_is_not_an_esp_is_not_opened(tmp_path):
    """mount is stubbed to fail, so a line here could only come from a
    partition type the script should not have looked at."""
    code, lines = run(tmp_path, "/dev/sdd1 vfat 0fc63daf-8483-4772-8e79-3d69d8477de4\n",
                      no_probe=True, esp_holds="ubuntu")
    assert lines == [], lines


def test_it_refuses_to_run_as_anyone_but_root(tmp_path):
    """The probe needs the device, and the ESP needs mounting."""
    code, lines = run(tmp_path, NTFS_DISK, probe=15, uid="1000")
    assert code == 1
    assert lines == []


def test_the_volume_is_probed_for_WRITING(tmp_path):
    """--readonly would answer the wrong question: a hibernated or dirty
    volume mounts read-only perfectly well, and still cannot be shrunk.
    """
    assert "--readwrite" in PREFLIGHT.read_text()
    assert "--readonly" not in PREFLIGHT.read_text()


def test_the_findings_are_ready_before_calamares_starts():
    """The card is on the very first page, so the file has to be there
    before Calamares is. raye-setup-run writes it, then starts Calamares --
    in that order, and a warning that arrives after the disk page has been
    passed is no warning.
    """
    run = (REPO / "usr/libexec/raye-setup-run").read_text()
    written = run.index("/usr/libexec/raye-preflight >")
    started = run.index("        calamares\n")
    assert written < started, "the findings are written after Calamares starts"


def test_nothing_here_ever_forces_ntfsresize():
    """The answer to a dirty volume is to send the person back to Windows,
    never to write over it. The one place that runs ntfsresize is rayedisk,
    and tests/test_rayedisk_apply.py holds that it never pushes past a refusal.
    """
    for path in sorted(REPO.glob("usr/libexec/*")) + sorted(REPO.glob("usr/bin/*")):
        # comments out: they are free to explain why the tool is not called
        code = re.sub(r"^\s*#.*$", "", path.read_text(), flags=re.M)
        for tool in ("ntfsresize", "ntfsfix"):
            assert tool not in code, f"{path} calls {tool}"
