# SPDX-License-Identifier: GPL-3.0-or-later
"""The writing side of the disk job, on real tools and on image files.

sfdisk and ntfsresize run for real, on regular files in a temporary folder.
Only the steps that need a block device (the kernel's view, mkfs, LUKS) are
answered by a stand-in. Nothing here can reach a real disk: the "disk" is a
path under tmp_path, and test_every_write_names_the_disk_of_the_plan holds it.
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
# what rayedisk_probe.hardware_of says of the image, before and during the write
HARDWARE = "ID_SERIAL=image;size=1"


class Failed(apply.CommandFailed):
    pass


def real(argv, feed=None, tolerate=False):
    done = subprocess.run(argv, input=feed, capture_output=True, text=True, errors="replace",
                          env={**os.environ, "LC_ALL": "C"})
    if done.returncode and not tolerate:
        raise apply.CommandFailed(argv, done.returncode, done.stderr + done.stdout)
    return done.stdout


def table(path):
    data = json.loads(real(["sfdisk", "--json", str(path)]))["partitiontable"]
    return data


def as_disk(path, size):
    data = table(path)
    return {"node": str(path), "size": size, "sector": SECTOR, "table": "gpt",
            "first": data["firstlba"], "last": data["lastlba"], "id": "x", "hardware": HARDWARE,
            "parts": [{"node": p["node"], "number": int(p["node"].rsplit("img", 1)[1]) if "img" in p["node"] else 0,
                       "start": p["start"], "sectors": p["size"], "type": p["type"],
                       "fstype": "", "findings": []}
                      for p in data.get("partitions", [])]}


def windows_image(path, size=200 * GIB):
    """A GPT disk as Windows leaves it: EFI, reserved, C: and recovery behind it."""
    with open(path, "wb") as f:
        f.truncate(size)
    script = ("label: gpt\n"
              f'start=2048, size={100 * MIB // SECTOR}, type={core.ESP_TYPE}, name="EFI system partition"\n'
              f"start={(100 * MIB + MIB) // SECTOR}, size={16 * MIB // SECTOR}, type={core.MS_RESERVED_TYPE}\n"
              f"start={(117 * MIB) // SECTOR}, size={(size - 2 * GIB) // SECTOR}, type={core.MS_BASIC_TYPE}\n"
              f"start={(size - GIB) // SECTOR}, size={512 * MIB // SECTOR}, type={core.MS_RECOVERY_TYPE}\n")
    real(["sfdisk", "--no-reread", "--no-tell-kernel", str(path)], feed=script)


@pytest.fixture
def image(tmp_path):
    path = tmp_path / "disk.img"
    windows_image(path)
    return path


class Recording:
    """Stands in for what needs a block device; sfdisk itself runs for real."""

    def __init__(self, ntfs_size=0):
        self.calls = []
        self.ntfs_size = ntfs_size

    def __call__(self, argv, feed=None, tolerate=False):
        self.calls.append((argv, feed))
        if argv[0] == "sfdisk":
            return real(argv, feed, tolerate)
        if argv[0] == "blkid":
            return "11111111-2222\n"
        if argv[0] == "ntfsresize" and "--info" in argv:
            return "Current volume size: %d bytes\n" % int(self.ntfs_size)
        return ""


def writer(run):
    def read_table(node):
        data = table(node)
        return {"parts": [{"node": p["node"], "start": p["start"], "sectors": p["size"], "type": p["type"]}
                          for p in data["partitions"]]}
    w = apply.Writer(run, read_table, identify=lambda node: HARDWARE)
    w.wait_for = lambda nodes: None
    return w


@pytest.fixture(autouse=True)
def backup_here(tmp_path, monkeypatch):
    monkeypatch.setattr(apply, "BACKUP_DIR", str(tmp_path / "root-only"))


def erase_plan(image, encrypt=False):
    d = as_disk(image, os.path.getsize(image))
    return d, core.plan(d, "efi", {"mode": "erase", "disk": d["node"], "id": "x", "encrypt": encrypt}, encrypt)


def test_erase_leaves_a_new_table_with_efi_boot_and_root(image):
    d, plan = erase_plan(image)
    run = Recording()
    made = writer(run).apply(plan, d, "")
    parts = table(image)["partitions"]
    assert [p["name"] for p in parts] == ["EFI", "raye_boot", "raye"]
    assert parts[0]["type"] == core.ESP_TYPE
    assert [m["mountPoint"] for m in made] == ["/boot/efi", "/boot", "/"]
    assert all(m["claimed"] for m in made)
    assert made[1]["fs"] == "ext4"
    assert made[2]["fs"] == "btrfs"
    ext4 = [a for a, _ in run.calls if a[0] == "mkfs.ext4"]
    assert len(ext4) == 1 and ext4[0][-3:] == ["-L", "raye_boot", made[1]["device"]]
    assert not any(a[0] == "cryptsetup" for a, _ in run.calls)


def test_the_old_table_is_saved_before_it_is_replaced(image):
    d, plan = erase_plan(image)
    before = real(["sfdisk", "--dump", str(image)])
    writer(Recording()).apply(plan, d, "")
    assert open(apply.backup_name(str(image))).read() == before


def test_encrypting_gives_the_jobs_after_this_one_what_they_read(image):
    d, plan = erase_plan(image, True)
    run = Recording()
    made = writer(run).apply(plan, d, "s3cret-words")
    root = [m for m in made if m["mountPoint"] == "/"][0]
    boot = [m for m in made if m["mountPoint"] == "/boot"][0]
    assert boot["fs"] == "ext4"
    assert root["luksPassphrase"] == "s3cret-words"
    assert root["luksMapperName"].startswith("luks-")
    assert root["luksUuid"]
    formatted = [a for a, _ in run.calls if a[0] == "mkfs.btrfs"][0]
    assert formatted[-1] == "/dev/mapper/" + root["luksMapperName"], "btrfs goes inside the LUKS volume"


def test_a_passphrase_never_goes_on_a_command_line(image):
    d, plan = erase_plan(image, True)
    run = Recording()
    writer(run).apply(plan, d, "s3cret-words")
    for argv, _ in run.calls:
        assert "s3cret-words" not in " ".join(argv)
    fed = [feed for argv, feed in run.calls if argv[0] == "cryptsetup"]
    assert fed == ["s3cret-words", "s3cret-words"]


def test_every_write_names_the_disk_of_the_plan(image):
    d, plan = erase_plan(image)
    run = Recording()
    writer(run).apply(plan, d, "")
    made_nodes = {p["node"] for p in table(image)["partitions"]}
    for argv, _ in run.calls:
        if argv[0] in ("sfdisk", "blockdev", "partx", "mkfs.vfat", "mkfs.ext4", "mkfs.btrfs"):
            assert argv[-1] == str(image) or argv[-1] in made_nodes, argv


def shrink_plan(image):
    d = as_disk(image, os.path.getsize(image))
    win = d["parts"][2]
    win.update({"fstype": "ntfs", "shrink_minimum": 40 * GIB, "os": "Windows"})
    offer = [o for o in core.options_for(d)[0] if o["mode"] == "shrink"][0]
    answer = {"mode": "shrink", "disk": d["node"], "id": "x", "encrypt": False,
              "partition": offer["node"], "keep": offer["keepDefault"]}
    return d, core.plan(d, "efi", answer, False)


def test_a_filesystem_that_did_not_shrink_stops_the_install(image):
    d, plan = shrink_plan(image)
    run = Recording(ntfs_size=plan["shrink"]["bytes"] + MIB)
    before = real(["sfdisk", "--dump", str(image)])
    with pytest.raises(core.Refused):
        writer(run).apply(plan, d, "")
    assert real(["sfdisk", "--dump", str(image)]) == before


def test_shrinking_leaves_every_other_partition_exactly_where_it_was(image):
    d, plan = shrink_plan(image)
    run = Recording()
    writer(run).apply(plan, d, "")
    after = {p["start"]: p for p in table(image)["partitions"]}
    for before in d["parts"]:
        assert before["start"] in after
        if before["node"] != plan["shrink"]["node"]:
            assert after[before["start"]]["size"] == before["sectors"]
            assert after[before["start"]]["type"] == before["type"]
    win = after[plan["shrink"]["start"]]
    assert win["size"] == plan["shrink"]["sectors"]
    assert win["type"] == core.MS_BASIC_TYPE, "shrinking must not change what the partition is"


def test_the_filesystem_shrinks_before_the_table_and_never_with_force(image):
    d, plan = shrink_plan(image)
    run = Recording()
    writer(run).apply(plan, d, "")
    names = [a[0] for a, _ in run.calls]
    resize = [a for a, _ in run.calls if a[0] == "ntfsresize"]
    # only the read-only look afterwards may force its way past the check
    # the shrink itself scheduled
    writing = [a for a in resize if "--info" not in a]
    assert writing and all("--force" not in a and "-f" not in a for a in writing)
    assert "--no-action" in resize[0], "the dry pass comes first"
    assert names.index("ntfsresize") < names.index("sfdisk", names.index("ntfsresize"))
    first_write = next(i for i, (a, _) in enumerate(run.calls)
                       if a[0] == "sfdisk" and "--dump" not in a)
    last_resize = max(i for i, (a, _) in enumerate(run.calls) if a[0] == "ntfsresize")
    assert last_resize < first_write
    assert not any(a[0] == "mkfs.vfat" for a, _ in run.calls), "the EFI partition of Windows is shared, not formatted"


def test_when_the_dry_pass_says_no_nothing_is_written(image):
    d, plan = shrink_plan(image)
    before = real(["sfdisk", "--dump", str(image)])
    calls = []

    def refusing(argv, feed=None, tolerate=False):
        calls.append(argv)
        if argv[0] == "ntfsresize" and "--no-action" in argv:
            raise apply.CommandFailed(argv, 1, "The NTFS journal file is unclean.")
        return real(argv, feed, tolerate) if argv[0] == "sfdisk" else ""

    with pytest.raises(apply.CommandFailed):
        writer(refusing).apply(plan, d, "")
    assert real(["sfdisk", "--dump", str(image)]) == before
    assert not any(a[0] == "ntfsresize" and "--no-action" not in a and "--info" not in a for a in calls)


def test_a_neighbour_that_moved_stops_the_install_before_any_format(image):
    d, plan = shrink_plan(image)
    run = Recording()
    w = writer(run)
    honest = w.read_table

    def lying(node):
        seen = honest(node)
        seen["parts"][1]["sectors"] -= 2048
        return seen

    w.read_table = lying
    with pytest.raises(core.Refused) as no:
        w.apply(plan, d, "")
    assert no.value.code == "table-mismatch"
    assert not any(a[0].startswith("mkfs") or a[0] == "cryptsetup" for a, _ in run.calls)


def test_replacing_leaves_the_neighbours_and_keeps_the_efi_partition(image):
    d = as_disk(image, os.path.getsize(image))
    answer = {"mode": "replace", "disk": d["node"], "id": "x", "encrypt": False,
              "partition": d["parts"][2]["node"]}
    plan = core.plan(d, "efi", answer, False)
    run = Recording()
    made = writer(run).apply(plan, d, "")
    after = {p["start"]: p for p in table(image)["partitions"]}
    for keep in (d["parts"][0], d["parts"][1], d["parts"][3]):
        assert after[keep["start"]]["size"] == keep["sectors"]
    assert [after[n["start"]]["name"] for n in plan["add"]] == ["raye_boot", "raye"]
    assert [m["mountPoint"] for m in made] == ["/boot/efi", "/boot", "/"]
    assert [m["claimed"] for m in made] == [False, True, True]


NTFS_BYTES = 64 * MIB
# The two tests below need ntfs-3g. The package build has it (debian/control)
# and sets RAYE_TESTS_STRICT, so there a missing tool fails instead of
# skipping; a machine without it says so rather than going red.
NEEDS_NTFS = pytest.mark.skipif(
    not os.environ.get("RAYE_TESTS_STRICT") and shutil.which("mkntfs") is None,
    reason="mkntfs is not installed (package ntfs-3g)")


@NEEDS_NTFS
def test_a_real_ntfs_volume_keeps_its_files_through_the_real_shrink(tmp_path):
    """mkntfs and ntfsresize for real: the files read back the same after."""
    volume = tmp_path / "ntfs.img"
    with open(volume, "wb") as f:
        f.truncate(NTFS_BYTES)
    real(["mkntfs", "--quiet", "--fast", "--force", "--label", "Windows", str(volume)])
    payload = tmp_path / "payload.bin"
    payload.write_bytes(os.urandom(4 * MIB))
    wanted = hashlib.sha256(payload.read_bytes()).hexdigest()
    real(["ntfscp", str(volume), str(payload), "kept.bin"])

    info = real(["ntfsresize", "--no-progress-bar", "--info", str(volume)])
    minimum = core.bytes_of_ntfsresize(info)
    assert minimum and minimum < NTFS_BYTES

    size = 32 * MIB
    w = writer(real)
    w.shrink_filesystem({"node": str(volume), "bytes": size})

    after = real(["ntfsresize", "--no-progress-bar", "--info", "--force", str(volume)])
    assert "Current volume size" in after
    current = int(after.split("Current volume size:")[1].split()[0])
    assert current <= size
    read_back = tmp_path / "out.bin"
    with open(read_back, "wb") as out:
        subprocess.run(["ntfscat", "--force", str(volume), "kept.bin"], stdout=out, check=True)
    assert hashlib.sha256(read_back.read_bytes()).hexdigest() == wanted


@NEEDS_NTFS
def test_after_a_real_shrink_ntfsresize_refuses_on_its_own_and_the_job_reads_it(tmp_path):
    """Measured: this is why the look afterwards has to push past the check."""
    volume = tmp_path / "ntfs.img"
    with open(volume, "wb") as f:
        f.truncate(NTFS_BYTES)
    real(["mkntfs", "--quiet", "--fast", "--force", str(volume)])
    writer(real).shrink_filesystem({"node": str(volume), "bytes": 32 * MIB})
    with pytest.raises(apply.CommandFailed):
        real(["ntfsresize", "--no-progress-bar", "--info", str(volume)])
    text = real(["ntfsresize", "--no-progress-bar", "--info", "--force", str(volume)])
    assert apply.ntfs_current_size(text) <= 32 * MIB


def test_a_partition_that_stays_mounted_stops_the_install(image):
    d, plan = erase_plan(image)
    plan["unmount"] = ["/dev/sdz1"]

    def busy(argv, feed=None, tolerate=False):
        if argv[0] == "lsblk":
            return "/somewhere\n"
        if argv[0] == "sfdisk":
            return real(argv, feed, tolerate)
        return ""

    before = real(["sfdisk", "--dump", str(image)])
    with pytest.raises(core.Refused) as no:
        writer(busy).apply(plan, d, "")
    assert no.value.code == "in-use"
    assert real(["sfdisk", "--dump", str(image)]) == before


def test_swap_on_the_disk_is_turned_off_rather_than_refused(image):
    d, plan = erase_plan(image)
    plan["unmount"] = ["/dev/sdz1"]
    run = Recording()
    writer(run).apply(plan, d, "")
    assert (["swapoff", "/dev/sdz1"], None) in run.calls
