# SPDX-License-Identifier: GPL-3.0-or-later
"""How the job reads the machine and what it leaves behind. No disk involved."""
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
    {"path": "/dev/sda", "type": "disk", "size": 256 * GIB, "model": "SSD  ", "rm": False, "tran": "sata",
     "fstype": None, "label": None, "mountpoints": [None], "log-sec": 512, "children": [
        {"path": "/dev/sda1", "type": "part", "size": GIB, "fstype": "vfat", "label": "EFI", "mountpoints": [None]},
        {"path": "/dev/sda2", "type": "part", "size": 100 * GIB, "fstype": "ntfs", "label": "C", "mountpoints": [None]},
        {"path": "/dev/sda3", "type": "part", "size": 100 * GIB, "fstype": "ext4", "label": "", "mountpoints": ["/mnt/x"]},
     ]},
    {"path": "/dev/sdb", "type": "disk", "size": 32 * GIB, "model": "Stick", "rm": True, "tran": "usb",
     "fstype": None, "label": None, "mountpoints": [None], "log-sec": 512, "children": [
        {"path": "/dev/sdb1", "type": "part", "size": 4 * GIB, "fstype": "iso9660", "label": "Raye", "mountpoints": ["/cdrom"]},
     ]},
    {"path": "/dev/sdc", "type": "disk", "size": 500 * GIB, "model": "Old", "rm": False, "tran": "sata",
     "fstype": None, "label": None, "mountpoints": [None], "log-sec": 512, "children": [
        {"path": "/dev/sdc1", "type": "part", "size": 500 * GIB, "fstype": "crypto_LUKS", "label": "", "mountpoints": [None],
         "children": [{"path": "/dev/mapper/x", "type": "crypt", "mountpoints": ["/data"]}]},
     ]},
    {"path": "/dev/sr0", "type": "rom", "size": GIB, "model": "CD", "rm": True, "mountpoints": [None]},
    {"path": "/dev/zram0", "type": "disk", "size": 8 * GIB, "model": None, "rm": False, "mountpoints": ["[SWAP]"]},
]}


def sfdisk_json(node, parts):
    return json.dumps({"partitiontable": {
        "label": "gpt", "id": "X", "device": node, "unit": "sectors", "firstlba": 2048,
        "lastlba": 500000000, "sectorsize": 512,
        "partitions": [dict(node=f"{node}{i + 1}", start=2048 + i * 1000000, size=s, type=t)
                       for i, (s, t) in enumerate(parts)]}})


def fake(argv):
    tool, last = argv[0], argv[-1]
    if tool == "lsblk":
        # measured: without --tree the partitions come out beside their disk
        assert any(a.startswith("--tree") for a in argv), argv
        return 0, json.dumps(LSBLK)
    if tool == "sfdisk" and "--json" in argv:
        if last == "/dev/sda":
            return 0, sfdisk_json(last, [(2097152, core.ESP_TYPE), (209715200, core.MS_BASIC_TYPE),
                                         (209715200, core.LINUX_TYPE)])
        if last == "/dev/sdb":
            return 0, sfdisk_json(last, [(8388608, "0FC63DAF-8483-4772-8E79-3D69D8477DE4")])
        return 0, sfdisk_json(last, [(1048576000, core.LINUX_TYPE)])
    if tool == "sfdisk":
        return 0, f"label: gpt\ndevice: {last}\n"
    if tool == "udevadm":
        return 0, f"ID_SERIAL=Disk_{last}\nID_PATH=pci-0000:00:17.0\n"
    if tool == "blockdev":
        return 0, "1000\n"
    if tool.endswith("raye-preflight"):
        return 0, "hibernated /dev/sdx9\nshared-efi /dev/sda1\n"
    if tool == "os-prober":
        return 0, "/dev/sda1@/EFI/Microsoft/Boot/bootmgfw.efi:Windows Boot Manager:Windows:efi\n/dev/sda3:Debian GNU/Linux 13:Debian:linux\n"
    if tool == "ntfsresize":
        return 0, "You might resize at 42949672960 bytes or 42950 MB\n"
    if tool == "ntfsls":
        return 0, ""
    return 1, ""


def machine(look=True):
    return {d["node"]: d for d in probe.read_machine(run=lambda argv, timeout=60: fake(argv), look=look)[1]}


def test_only_real_disks_are_read():
    assert sorted(machine()) == ["/dev/sda", "/dev/sdb", "/dev/sdc"]


def test_the_stick_raye_started_from_is_marked():
    assert machine()["/dev/sdb"]["live"]
    assert not machine()["/dev/sda"]["live"]


def test_a_disk_holding_an_open_encrypted_volume_is_marked_in_use():
    assert machine()["/dev/sdc"]["holders"] == ["crypt"]


def test_partitions_carry_what_the_rules_read():
    parts = machine()["/dev/sda"]["parts"]
    assert parts[0]["findings"] == ["shared-efi"]
    assert parts[1]["fstype"] == "ntfs"
    assert parts[1]["os"] == "Windows"
    assert parts[1]["shrink_minimum"] == 40 * GIB
    assert parts[2]["mounted"] is True
    assert parts[2]["os"] == "Debian GNU/Linux 13"
    assert parts[1]["number"] == 2


def test_the_job_still_reads_how_small_ntfs_can_go_without_os_prober():
    assert machine(look=False)["/dev/sda"]["parts"][1]["shrink_minimum"] == 40 * GIB


def test_nvme_partitions_keep_their_number():
    assert probe.number_of("/dev/nvme0n1p7") == 7


def test_a_changed_table_changes_the_fingerprint():
    one = probe.fingerprint("/dev/sda", 1, "", run=lambda a: (0, "start=1"))
    two = probe.fingerprint("/dev/sda", 1, "", run=lambda a: (0, "start=2"))
    assert one != two


@pytest.fixture
def job(monkeypatch, tmp_path):
    stored = {}
    lib = types.ModuleType("libcalamares")
    lib.globalstorage = types.SimpleNamespace(insert=stored.__setitem__)
    lib.job = types.SimpleNamespace(setprogress=lambda part: None, working_path=str(FOLDER))
    lib.utils = types.SimpleNamespace(debug=lambda text: None, warning=lambda text: None)
    monkeypatch.setitem(sys.modules, "libcalamares", lib)
    sys.modules.pop("rayedisk_main", None)
    import importlib.util
    spec = importlib.util.spec_from_file_location("rayedisk_main", FOLDER / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ANSWER", str(tmp_path / "answer-disk"))
    monkeypatch.setattr(module, "PASSPHRASE", str(tmp_path / "answer-disk-passphrase"))
    monkeypatch.setattr(module, "CHOICES", str(tmp_path / "choices"))
    module.stored = stored
    module.folder = tmp_path
    return module


def test_no_answer_stops_the_install_before_any_write(job, monkeypatch):
    writes = []
    monkeypatch.setattr(job, "Writer", lambda *a, **k: writes.append(a))
    monkeypatch.setattr(job, "read_machine", lambda look=False: ("efi", []))
    title, text = job.run()
    assert "Nothing on the disk was changed" in text
    assert writes == [] and job.stored == {}


def test_a_disk_that_changed_stops_the_install_before_any_write(job, monkeypatch):
    (job.folder / "answer-disk").write_text(json.dumps(
        {"mode": "erase", "disk": "/dev/sda", "id": "old", "encrypt": False}))
    disk = {"node": "/dev/sda", "id": "new", "size": 256 * GIB, "sector": 512, "table": "gpt",
            "first": 2048, "last": 500000000, "parts": [], "holders": [], "live": False}
    monkeypatch.setattr(job, "read_machine", lambda look=False: ("efi", [disk]))
    writes = []
    monkeypatch.setattr(job, "Writer", lambda *a, **k: writes.append(a))
    title, text = job.run()
    assert "changed after you chose" in text and writes == []


def test_the_passphrase_leaves_its_file_when_it_is_read(job):
    (job.folder / "answer-disk-passphrase").write_text("s3cret words")
    assert job.take_passphrase() == "s3cret words"
    assert not (job.folder / "answer-disk-passphrase").exists()


def test_a_failed_command_never_shows_what_it_was_fed(job, monkeypatch):
    (job.folder / "answer-disk").write_text(json.dumps(
        {"mode": "erase", "disk": "/dev/sda", "id": "same", "encrypt": True}))
    (job.folder / "answer-disk-passphrase").write_text("s3cret words")
    disk = {"node": "/dev/sda", "id": "same", "size": 256 * GIB, "sector": 512, "table": "none",
            "first": 2048, "last": 500000000, "parts": [], "holders": [], "live": False}
    monkeypatch.setattr(job, "read_machine", lambda look=False: ("efi", [disk]))

    class Failing:
        def __init__(self, *a, **k):
            pass

        def apply(self, plan, before, passphrase):
            raise job.CommandFailed(["cryptsetup", "luksFormat", "/dev/sda2"], 1, "no entropy")

    monkeypatch.setattr(job, "Writer", Failing)
    title, text = job.run()
    assert "s3cret" not in title + text and "cryptsetup" in text


def test_what_the_next_jobs_read_is_left_behind(job):
    made = [{"device": "/dev/sda1", "mountPoint": "/boot/efi"}, {"device": "/dev/sda2", "mountPoint": "/"}]
    job.fill_storage(job.libcalamares.globalstorage, made, {"mode": "shrink"})
    assert job.stored["partitions"] == made
    assert job.stored["firmwareType"] == "efi"
    assert job.stored["efiSystemPartition"] == "/boot/efi"
    assert job.stored["partitionChoices"] == {"install": "alongside", "swap": "file"}


def test_every_message_of_the_job_exists_in_both_languages(job):
    assert set(job.TEXT["en"]) == set(job.TEXT["fr"])
    for code in ("no-choice", "disk-changed", "table-mismatch", "keep-out-of-range", "hibernated"):
        assert job.TEXT["fr"][code] != job.TEXT["en"][code], code


def test_the_job_finds_its_own_files_the_way_calamares_runs_it():
    """Calamares evaluates main.py with no folder on the import path: without
    the line that adds working_path, the install dies on its first import."""
    text = (FOLDER / "main.py").read_text()
    assert "sys.path.insert(0, libcalamares.job.working_path)" in text
    assert text.index("sys.path.insert") < text.index("from rayedisk_apply")


def test_wifi_of_the_replaced_linux_is_read_before_it_goes(job, monkeypatch, tmp_path):
    import contextlib
    old = tmp_path / "old"
    conns = old / "etc/NetworkManager/system-connections"
    conns.mkdir(parents=True)
    (old / "etc/fstab").write_text("UUID=x / ext4 defaults 0 1\n")
    (old / "etc/os-release").write_text('NAME="Mint"\n')
    (conns / "Home.nmconnection").write_text("[connection]\nid=Home\nuuid=1\ntype=wifi\n[wifi]\nssid=Home\n"
                                             "[wifi-security]\nkey-mgmt=wpa-psk\npsk=pw\n")
    private = tmp_path / "root-only"
    private.mkdir(mode=0o700)
    monkeypatch.setattr(job, "WIFI", str(private / "keep-wifi"))
    monkeypatch.setattr(job, "mounted_read_only", lambda part: contextlib.nullcontext(str(old)))
    disk = {"parts": [{"node": "/dev/sda2"}]}
    job.save_wifi(disk, {"system": "linux", "source": "/dev/sda2"})
    saved = json.loads((private / "keep-wifi").read_text())
    assert [c["ssid"] for c in saved] == ["Home"] and "psk=pw" in saved[0]["text"]
    assert ((private / "keep-wifi").stat().st_mode & 0o777) == 0o600
    # Windows' networks can't be read: nothing is left
    (private / "keep-wifi").unlink()
    job.save_wifi(disk, {"system": "windows", "source": "/dev/sda2"})
    assert not (private / "keep-wifi").exists()
