# SPDX-License-Identifier: GPL-3.0-or-later
"""The writer for Linux volumes and old-style tables, on image files.

e2fsck, resize2fs, debugfs and sfdisk run for real on regular files under
tmp_path. btrfs can only shrink while mounted, so its steps are recorded.
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

FOLDER = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedisk"
sys.path.insert(0, str(FOLDER))
import rayedisk_apply as apply  # noqa: E402
import rayedisk_core as core  # noqa: E402

MIB = core.MIB
GIB = core.GIB
SECTOR = 512
HARDWARE = "ID_SERIAL=image;size=1"

NEEDS_EXT = pytest.mark.skipif(
    not os.environ.get("RAYE_TESTS_STRICT") and shutil.which("resize2fs") is None,
    reason="e2fsprogs is not installed")


def real(argv, feed=None, tolerate=False):
    done = subprocess.run(argv, input=feed, capture_output=True, text=True, errors="replace",
                          env={**os.environ, "LC_ALL": "C"})
    if done.returncode and not tolerate:
        raise apply.CommandFailed(argv, done.returncode, done.stderr + done.stdout)
    return done.stdout


class Recording:
    def __init__(self, answers=None, fail=None):
        self.calls = []
        self.answers = answers or {}
        self.fail = fail

    def __call__(self, argv, feed=None, tolerate=False):
        self.calls.append(argv)
        if self.fail and argv[:len(self.fail)] == self.fail:
            raise apply.CommandFailed(argv, 1, "no")
        for key, text in self.answers.items():
            if " ".join(argv).startswith(key):
                return text
        if argv[0] == "sfdisk":
            return real(argv, feed, tolerate)
        if argv[0] == "blkid":
            return "1111-2222\n"
        return ""


def writer(run):
    def read_table(node):
        data = json.loads(real(["sfdisk", "--json", str(node)]))["partitiontable"]
        return {"parts": [{"node": p["node"], "start": p["start"], "sectors": p["size"], "type": p["type"]}
                          for p in data.get("partitions", [])]}
    w = apply.Writer(run, read_table, identify=lambda node: HARDWARE)
    w.wait_for = lambda nodes: None
    return w


@pytest.fixture(autouse=True)
def backup_here(tmp_path, monkeypatch):
    monkeypatch.setattr(apply, "BACKUP_DIR", str(tmp_path / "root-only"))


@NEEDS_EXT
def test_real_ext4_keeps_its_files_through_the_shrink(tmp_path):
    volume = tmp_path / "ext4.img"
    with open(volume, "wb") as f:
        f.truncate(256 * MIB)
    real(["mke2fs", "-q", "-F", "-t", "ext4", str(volume)])
    payload = tmp_path / "payload.bin"
    payload.write_bytes(os.urandom(4 * MIB))
    wanted = hashlib.sha256(payload.read_bytes()).hexdigest()
    real(["debugfs", "-w", "-R", f"write {payload} kept.bin", str(volume)])

    size = 96 * MIB
    writer(real).shrink_filesystem({"node": str(volume), "bytes": size, "fstype": "ext4"})

    info = core.ext_info(real(["dumpe2fs", "-h", str(volume)]))
    assert info["bytes"] <= size
    out = tmp_path / "out.bin"
    real(["debugfs", "-R", f"dump kept.bin {out}", str(volume)])
    assert hashlib.sha256(out.read_bytes()).hexdigest() == wanted
    real(["e2fsck", "-f", "-n", str(volume)])


@NEEDS_EXT
def test_ext4_too_small_for_its_files_is_left_alone(tmp_path):
    volume = tmp_path / "ext4.img"
    with open(volume, "wb") as f:
        f.truncate(128 * MIB)
    real(["mke2fs", "-q", "-F", "-t", "ext4", str(volume)])
    payload = tmp_path / "big.bin"
    payload.write_bytes(os.urandom(80 * MIB))
    real(["debugfs", "-w", "-R", f"write {payload} big.bin", str(volume)])
    before = core.ext_info(real(["dumpe2fs", "-h", str(volume)]))["bytes"]
    with pytest.raises(apply.CommandFailed):
        writer(real).shrink_filesystem({"node": str(volume), "bytes": 16 * MIB, "fstype": "ext4"})
    assert core.ext_info(real(["dumpe2fs", "-h", str(volume)]))["bytes"] == before


def test_ext4_with_errors_is_refused_before_anything_changes():
    run = Recording(fail=["e2fsck", "-f", "-n"])
    with pytest.raises(core.Refused) as no:
        writer(run).shrink_filesystem({"node": "/dev/sdz2", "bytes": 40 * GIB, "fstype": "ext4"})
    assert no.value.code == "linux-check"
    assert not any(a[0] in ("resize2fs",) or a[:3] == ["e2fsck", "-f", "-y"] for a in run.calls)


def test_ext4_tidied_by_the_second_check_still_shrinks():
    # e2fsck -y says 1 when it only tidied something up (extent trees)
    class Tidy(Recording):
        def __call__(self, argv, feed=None, tolerate=False):
            if argv[:3] == ["e2fsck", "-f", "-y"]:
                self.calls.append(argv)
                raise apply.CommandFailed(argv, 1, "FILE SYSTEM WAS MODIFIED")
            return super().__call__(argv, feed, tolerate)
    run = Tidy(answers={"dumpe2fs": "Filesystem state: clean\nBlock count: 1000\nBlock size: 4096\n"})
    writer(run).shrink_filesystem({"node": "/dev/sdz2", "bytes": 40 * GIB, "fstype": "ext4"})
    assert any(a[0] == "resize2fs" for a in run.calls)


def test_ext4_the_second_check_could_not_fix_stops_everything():
    class Broken(Recording):
        def __call__(self, argv, feed=None, tolerate=False):
            if argv[:3] == ["e2fsck", "-f", "-y"]:
                raise apply.CommandFailed(argv, 4, "errors left uncorrected")
            return super().__call__(argv, feed, tolerate)
    run = Broken()
    with pytest.raises(apply.CommandFailed):
        writer(run).shrink_filesystem({"node": "/dev/sdz2", "bytes": 40 * GIB, "fstype": "ext4"})
    assert not any(a[0] == "resize2fs" for a in run.calls)


def btrfs_super(total):
    return ("log_root\t\t0\nnum_devices\t\t1\ndev_item.total_bytes\t%d\n"
            "dev_item.bytes_used\t10737418240\ndev_item.devid\t\t2\n" % total)


def test_btrfs_is_checked_mounted_shrunk_and_unmounted_in_that_order():
    run = Recording(answers={"btrfs inspect-internal dump-super": btrfs_super(40 * GIB)})
    writer(run).shrink_filesystem({"node": "/dev/sdz2", "bytes": 40 * GIB, "fstype": "btrfs", "devid": 2})
    tools = [" ".join(a[:3]) for a in run.calls]
    check = tools.index("btrfs check --readonly")
    mount = next(i for i, a in enumerate(run.calls) if a[0] == "mount")
    resize = next(i for i, a in enumerate(run.calls) if a[:3] == ["btrfs", "filesystem", "resize"])
    umount = next(i for i, a in enumerate(run.calls) if a[0] == "umount")
    assert check < mount < resize < umount
    assert run.calls[resize][3] == "2:%d" % (40 * GIB)
    assert run.calls[mount][-2] == "/dev/sdz2"
    assert run.calls[mount][-1].startswith(str(apply.BACKUP_DIR))


def test_btrfs_is_unmounted_even_when_the_resize_fails():
    run = Recording(fail=["btrfs", "filesystem", "resize"])
    with pytest.raises(apply.CommandFailed):
        writer(run).shrink_filesystem({"node": "/dev/sdz2", "bytes": 40 * GIB, "fstype": "btrfs", "devid": 1})
    assert any(a[0] == "umount" for a in run.calls)


def test_btrfs_that_did_not_shrink_stops_the_install():
    run = Recording(answers={"btrfs inspect-internal dump-super": btrfs_super(80 * GIB)})
    with pytest.raises(core.Refused) as no:
        writer(run).shrink_filesystem({"node": "/dev/sdz2", "bytes": 40 * GIB, "fstype": "btrfs", "devid": 1})
    assert no.value.code == "table-mismatch"


def test_btrfs_that_fails_its_check_is_refused():
    run = Recording(fail=["btrfs", "check"])
    with pytest.raises(core.Refused) as no:
        writer(run).shrink_filesystem({"node": "/dev/sdz2", "bytes": 40 * GIB, "fstype": "btrfs", "devid": 1})
    assert no.value.code == "linux-check"
    assert not any(a[0] == "mount" for a in run.calls)


def test_a_filesystem_kind_nobody_planned_for_is_never_resized():
    run = Recording()
    with pytest.raises(core.Refused):
        writer(run).shrink_filesystem({"node": "/dev/sdz2", "bytes": 40 * GIB, "fstype": "xfs"})
    assert run.calls == []


def blank_image(tmp_path, size):
    path = tmp_path / "disk.img"
    with open(path, "wb") as f:
        f.truncate(size)
    return path


def as_disk(path):
    size = os.path.getsize(path)
    return {"node": str(path), "size": size, "sector": SECTOR, "table": "none", "first": 2048,
            "last": size // SECTOR - 34, "id": "x", "hardware": HARDWARE, "parts": []}


def test_bios_erase_writes_an_old_style_table_with_the_boot_flag(tmp_path):
    image = blank_image(tmp_path, 64 * GIB)
    d = as_disk(image)
    plan = core.plan(d, "bios", {"mode": "erase", "disk": d["node"], "id": "x", "encrypt": False}, False)
    run = Recording()
    writer(run).apply(plan, d, "")
    data = json.loads(real(["sfdisk", "--json", str(image)]))["partitiontable"]
    assert data["label"] == "dos"
    assert [p["type"] for p in data["partitions"]] == ["83", "83"]
    assert data["partitions"][0].get("bootable") is True
    # the boot partition gets ext4, the root btrfs, and nothing EFI anywhere
    made = [a for a in run.calls if a[0].startswith("mkfs")]
    assert [a[0] for a in made] == ["mkfs.ext4", "mkfs.btrfs"]


def test_bios_boot_partition_is_never_formatted(tmp_path):
    image = blank_image(tmp_path, 64 * GIB)
    d = as_disk(image)
    plan = core.plan(d, "bios", {"mode": "erase", "disk": d["node"], "id": "x", "encrypt": False}, False)
    # what a disk over 2 TiB gets, on a small image
    plan["label"] = "gpt"
    plan["add"] = core._layout(d, 2048, d["last"] - 4096, "biosboot", "gpt")
    run = Recording()
    made = writer(run).apply(plan, d, "")
    data = json.loads(real(["sfdisk", "--json", str(image)]))["partitiontable"]
    assert data["partitions"][0]["type"] == core.BIOS_BOOT_TYPE
    assert [m["mountPoint"] for m in made] == ["/boot", "/"]
    assert not any(a[0].startswith("mkfs") and a[-1].endswith("img1") for a in run.calls)
