# SPDX-License-Identifier: GPL-3.0-or-later
"""Installing next to another Linux: what is offered, what a plan does.

Made-up disks only, like test_rayedisk_core.py.
"""
import importlib.util
import pathlib

import pytest

MODULE = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedisk/rayedisk_core.py"
spec = importlib.util.spec_from_file_location("rayedisk_core", MODULE)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

GIB = core.GIB
MIB = core.MIB
SECTOR = 512


def sectors(gib):
    return int(gib * GIB) // SECTOR


def part(number, start, size_gib, ptype=core.LINUX_TYPE, fstype="", **more):
    entry = {"node": f"/dev/sda{number}", "number": number, "start": start,
             "sectors": sectors(size_gib), "type": ptype, "fstype": fstype, "findings": []}
    entry.update(more)
    return entry


def disk(parts, size_gib=256, **more):
    total = sectors(size_gib)
    entry = {"node": "/dev/sda", "model": "Test", "size": total * SECTOR, "sector": SECTOR,
             "table": "gpt", "first": 2048, "last": total - 34, "parts": parts, "id": "abc",
             "hardware": "hw"}
    entry.update(more)
    return entry


def linux(fstype="ext4", used_gib=30, size_gib=200, esp_findings=(), **more):
    """A disk as another Linux leaves it: EFI, its root, a swap partition."""
    esp = part(1, 2048, 0.5, core.ESP_TYPE, "vfat", findings=list(esp_findings))
    root = part(2, 2048 + sectors(0.5), size_gib, core.LINUX_TYPE, fstype, os="Arch Linux",
                shrink_minimum=used_gib * GIB, **more)
    swap = part(3, root["start"] + root["sectors"], 8, "0657FD6D-A4AB-43C4-84E5-0933C84B4F4F", "swap")
    return [esp, root, swap]


def modes(options, mode):
    return [o for o in options if o["mode"] == mode]


def answer(mode, **more):
    entry = {"mode": mode, "disk": "/dev/sda", "id": "abc", "encrypt": False}
    entry.update(more)
    return entry


@pytest.mark.parametrize("fstype", ["ext4", "ext3", "btrfs"])
def test_linux_volume_can_be_shrunk(fstype):
    options, refused = core.options_for(disk(linux(fstype)))
    shrink = modes(options, "shrink")
    assert refused == []
    assert [o["node"] for o in shrink] == ["/dev/sda2"]
    assert shrink[0]["name"] == "Arch Linux"
    assert shrink[0]["fstype"] == fstype
    assert shrink[0]["keepMin"] >= 30 * GIB + core.LINUX_ROOM
    assert shrink[0]["total"] - shrink[0]["keepMax"] >= core.RAYE_NEEDS


@pytest.mark.parametrize("fstype,finding", [
    ("xfs", "xfs"), ("crypto_LUKS", "encrypted"), ("LVM2_member", "lvm"),
])
def test_volume_that_cannot_shrink_says_why(fstype, finding):
    options, refused = core.options_for(disk(linux(fstype)))
    assert modes(options, "shrink") == []
    assert {"mode": "shrink", "node": "/dev/sda2", "name": "Arch Linux", "finding": finding} in refused
    # replacing or erasing still work, they don't need the volume to agree
    assert modes(options, "replace") and modes(options, "erase")


def test_small_volume_that_cannot_shrink_is_not_mentioned():
    parts = linux()
    parts[2]["fstype"] = "crypto_LUKS"
    _, refused = core.options_for(disk(parts))
    assert refused == []


@pytest.mark.parametrize("finding", ["linux-check", "btrfs-multi"])
def test_volume_with_a_finding_is_not_shrunk(finding):
    options, refused = core.options_for(disk(linux(findings=[finding])))
    assert modes(options, "shrink") == []
    assert refused[0]["finding"] == finding


def test_hibernated_linux_on_the_disk_stops_every_linux_shrink():
    parts = linux()
    parts[2]["findings"] = ["linux-hibernated"]
    options, refused = core.options_for(disk(parts))
    assert modes(options, "shrink") == []
    assert refused[0]["finding"] == "linux-hibernated"


def test_volume_nobody_measured_is_not_shrunk():
    parts = linux()
    del parts[1]["shrink_minimum"]
    options, refused = core.options_for(disk(parts))
    assert modes(options, "shrink") == []
    assert refused[0]["finding"] == "linux-unknown"


def test_shared_efi_gets_raye_its_own_efi_partition():
    d = disk(linux(esp_findings=["shared-efi"]))
    options, refused = core.options_for(d)
    assert refused == []
    assert modes(options, "shrink") and modes(options, "replace")
    shrink = modes(options, "shrink")[0]
    # the new EFI partition comes out of Raye's share
    assert shrink["total"] - shrink["keepMax"] >= core.RAYE_NEEDS + core.ESP_SIZE
    made = core.plan(d, "efi", answer("shrink", partition="/dev/sda2", keep=shrink["keepDefault"]), False)
    assert made["reuse_esp"] is None
    assert [n["role"] for n in made["add"]] == ["esp", "boot", "root"]


def test_plain_efi_partition_of_another_linux_is_shared():
    made = core.plan(disk(linux()), "efi", answer("replace", partition="/dev/sda2"), False)
    assert made["reuse_esp"] == "/dev/sda1"


def test_linux_shrink_plan_carries_what_the_writer_needs():
    d = disk(linux("btrfs", btrfs_devid=3))
    offered = modes(core.options_for(d)[0], "shrink")[0]
    made = core.plan(d, "efi", answer("shrink", partition="/dev/sda2", keep=offered["keepMin"]), False)
    assert made["shrink"]["fstype"] == "btrfs"
    assert made["shrink"]["devid"] == 3
    assert made["shrink"]["bytes"] >= 30 * GIB
    assert made["shrink"]["bytes"] % MIB == 0
    assert [n["role"] for n in made["add"]] == ["boot", "root"]


def test_linux_shrink_below_the_offer_is_refused():
    d = disk(linux())
    offered = modes(core.options_for(d)[0], "shrink")[0]
    with pytest.raises(core.Refused) as no:
        core.plan(d, "efi", answer("shrink", partition="/dev/sda2", keep=offered["keepMin"] - MIB), False)
    assert no.value.code == "keep-out-of-range"


def test_xfs_shrink_is_refused_even_when_asked():
    d = disk(linux("xfs"))
    with pytest.raises(core.Refused) as no:
        core.plan(d, "efi", answer("shrink", partition="/dev/sda2", keep=100 * GIB), False)
    assert no.value.code == "xfs"


def test_shrink_of_a_volume_that_turned_unclean_is_refused():
    d = disk(linux(findings=["linux-check"]))
    with pytest.raises(core.Refused) as no:
        core.plan(d, "efi", answer("shrink", partition="/dev/sda2", keep=100 * GIB), False)
    assert no.value.code == "linux-check"


def test_reading_dumpe2fs():
    text = ("Filesystem volume name:   <none>\n"
            "Filesystem features:      has_journal ext_attr resize_inode dir_index filetype extent 64bit\n"
            "Filesystem state:         clean\n"
            "Block count:              52428800\n"
            "Block size:               4096\n")
    info = core.ext_info(text)
    assert info == {"clean": True, "bytes": 52428800 * 4096, "block": 4096}
    dirty = text.replace("filetype", "filetype needs_recovery")
    assert core.ext_info(dirty)["clean"] is False
    assert core.ext_info(text.replace("state:         clean", "state:         not clean"))["clean"] is False
    assert core.ext_info("nothing") is None


def test_reading_resize2fs_minimum():
    assert core.ext_minimum("Estimated minimum size of the filesystem: 1234567\n", 4096) == 1234567 * 4096
    assert core.ext_minimum("Please run 'e2fsck -f /dev/sda2' first.\n", 4096) is None


def test_reading_btrfs_super():
    text = ("csum_type\t\t0 (crc32c)\n"
            "log_root\t\t0\n"
            "num_devices\t\t1\n"
            "dev_item.total_bytes\t214748364800\n"
            "dev_item.bytes_used\t40802189312\n"
            "dev_item.devid\t\t1\n")
    assert core.btrfs_info(text) == {"devices": 1, "bytes": 214748364800, "used": 40802189312,
                                     "devid": 1, "log": False}
    assert core.btrfs_info(text.replace("log_root\t\t0", "log_root\t\t30605312"))["log"] is True
    assert core.btrfs_info("nothing") is None
