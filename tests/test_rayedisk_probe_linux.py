# SPDX-License-Identifier: GPL-3.0-or-later
"""How Linux volumes are read for the disk page, and what the job leaves
behind on a BIOS install. Commands are answered by a stand-in."""
import json
import pathlib
import sys
import types

import pytest

FOLDER = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedisk"
sys.path.insert(0, str(FOLDER))
import rayedisk_core as core  # noqa: E402
import rayedisk_probe as probe  # noqa: E402

GIB = core.GIB

LSBLK = {"blockdevices": [
    {"path": "/dev/sda", "type": "disk", "size": 256 * GIB, "model": "SSD", "rm": False, "tran": "sata",
     "fstype": None, "mountpoints": [None], "log-sec": 512, "children": [
        {"path": "/dev/sda1", "type": "part", "size": GIB, "fstype": "vfat", "mountpoints": [None]},
        {"path": "/dev/sda2", "type": "part", "size": 100 * GIB, "fstype": "ext4", "mountpoints": [None]},
        {"path": "/dev/sda3", "type": "part", "size": 100 * GIB, "fstype": "btrfs", "mountpoints": [None]},
        {"path": "/dev/sda4", "type": "part", "size": 50 * GIB, "fstype": "ext4", "mountpoints": [None]},
     ]},
]}

DUMPE2FS = ("Filesystem features:      has_journal extent 64bit\n"
            "Filesystem state:         clean\nBlock count:              26214400\nBlock size:               4096\n")


def fake(argv, state=None):
    tool, last = argv[0], argv[-1]
    if tool == "lsblk":
        return 0, json.dumps(LSBLK)
    if tool == "sfdisk" and "--json" in argv:
        return 0, json.dumps({"partitiontable": {
            "label": "gpt", "firstlba": 2048, "lastlba": 500000000, "sectorsize": 512,
            "partitions": [{"node": f"/dev/sda{i + 1}", "start": 2048 + i * 300000000 // 4, "size": s, "type": t}
                           for i, (s, t) in enumerate([(2097152, core.ESP_TYPE), (209715200, core.LINUX_TYPE),
                                                       (209715200, core.LINUX_TYPE), (104857600, core.LINUX_TYPE)])]}})
    if tool == "sfdisk":
        return 0, "label: gpt\n"
    if tool == "udevadm":
        return 0, "ID_SERIAL=x\n"
    if tool == "blockdev":
        return 0, "1000\n"
    if tool.endswith("raye-preflight"):
        return 0, ""
    if tool == "os-prober":
        return 0, "/dev/sda2:Arch Linux:Arch:linux\n"
    if tool == "dumpe2fs":
        if last == "/dev/sda4":
            return 0, DUMPE2FS.replace("clean", "not clean")
        return 0, DUMPE2FS
    if tool == "resize2fs" and "-P" in argv:
        return 0, "Estimated minimum size of the filesystem: 5242880\n"
    if tool == "btrfs":
        return 0, ("log_root\t\t0\nnum_devices\t\t1\ndev_item.total_bytes\t107374182400\n"
                   "dev_item.bytes_used\t21474836480\ndev_item.devid\t\t1\n")
    return 1, ""


def machine(look=True):
    found = probe.read_machine(run=lambda argv, timeout=60: fake(argv), look=look)[1]
    return {p["node"]: p for p in found[0]["parts"]}


def test_ext4_minimum_comes_from_resize2fs():
    parts = machine()
    assert parts["/dev/sda2"]["shrink_minimum"] == 5242880 * 4096
    assert parts["/dev/sda2"]["os"] == "Arch Linux"
    assert parts["/dev/sda2"]["findings"] == []


def test_unclean_ext4_gets_a_finding_and_no_minimum():
    part = machine()["/dev/sda4"]
    assert "linux-check" in part["findings"]
    assert "shrink_minimum" not in part


def test_btrfs_minimum_is_what_it_has_allocated():
    part = machine()["/dev/sda3"]
    assert part["shrink_minimum"] == 21474836480
    assert part["btrfs_devid"] == 1


def test_the_job_reads_the_same_minimum_without_os_prober():
    assert machine(look=False)["/dev/sda2"]["shrink_minimum"] == 5242880 * 4096
    assert machine(look=False)["/dev/sda3"]["shrink_minimum"] == 21474836480


def test_btrfs_on_several_disks_is_marked():
    def several(argv, timeout=60):
        code, text = fake(argv)
        if argv[0] == "btrfs":
            text = text.replace("num_devices\t\t1", "num_devices\t\t2")
        return code, text
    found = probe.read_machine(run=several)[1]
    part = {p["node"]: p for p in found[0]["parts"]}["/dev/sda3"]
    assert "btrfs-multi" in part["findings"]


def test_btrfs_left_with_a_log_is_marked():
    def logged(argv, timeout=60):
        code, text = fake(argv)
        if argv[0] == "btrfs":
            text = text.replace("log_root\t\t0", "log_root\t\t1234")
        return code, text
    found = probe.read_machine(run=logged)[1]
    part = {p["node"]: p for p in found[0]["parts"]}["/dev/sda3"]
    assert "linux-check" in part["findings"]


def test_mounted_linux_volume_is_not_read():
    calls = []

    def seen(argv, timeout=60):
        calls.append(argv)
        return fake(argv)
    LSBLK["blockdevices"][0]["children"][1]["mountpoints"] = ["/mnt"]
    try:
        probe.read_machine(run=seen)
    finally:
        LSBLK["blockdevices"][0]["children"][1]["mountpoints"] = [None]
    assert ["dumpe2fs", "-h", "/dev/sda2"] not in calls


def test_old_table_ends_at_the_last_sector():
    def dos(argv, timeout=60):
        if argv[0] == "sfdisk" and "--json" in argv:
            return 0, json.dumps({"partitiontable": {"label": "dos", "sectorsize": 512, "partitions": []}})
        return fake(argv)
    found = probe.read_machine(run=dos)[1][0]
    assert found["table"] == "dos"
    assert found["last"] == 256 * GIB // 512 - 1


@pytest.fixture
def job(monkeypatch, tmp_path):
    stored = {}
    lib = types.ModuleType("libcalamares")
    lib.globalstorage = types.SimpleNamespace(insert=stored.__setitem__)
    lib.job = types.SimpleNamespace(setprogress=lambda part: None, working_path=str(FOLDER))
    lib.utils = types.SimpleNamespace(debug=lambda text: None, warning=lambda text: None)
    monkeypatch.setitem(sys.modules, "libcalamares", lib)
    import importlib.util
    spec = importlib.util.spec_from_file_location("rayedisk_main_bios", FOLDER / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.stored = stored
    return module


def test_bios_install_tells_grub_which_disk(job):
    made = [{"device": "/dev/sda1", "mountPoint": "/boot"}, {"device": "/dev/sda2", "mountPoint": "/"}]
    job.fill_storage(job.libcalamares.globalstorage, made,
                     {"mode": "erase", "firmware": "bios", "disk": "/dev/sda"})
    assert job.stored["firmwareType"] == "bios"
    assert job.stored["bootLoader"] == {"installPath": "/dev/sda"}
    assert "efiSystemPartition" not in job.stored


def test_efi_install_leaves_no_bios_target(job):
    job.fill_storage(job.libcalamares.globalstorage, [], {"mode": "erase", "firmware": "efi", "disk": "/dev/sda"})
    assert job.stored["firmwareType"] == "efi"
    assert "bootLoader" not in job.stored


def test_every_new_message_exists_in_both_languages(job):
    for code in ("linux-check", "linux-hibernated", "btrfs-multi", "xfs", "encrypted", "lvm",
                 "linux-unknown", "full-table"):
        assert job.TEXT["en"][code] and job.TEXT["fr"][code], code
        assert job.TEXT["en"][code] != job.TEXT["fr"][code], code
