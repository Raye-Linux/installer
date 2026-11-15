# SPDX-License-Identifier: GPL-3.0-or-later
"""The four ways the disk job could lose someone's data or their disk password.

 - A disk sfdisk cannot read must never look empty: that is the disk the page
   would pick the "erase" card for on its own.
 - Two disks that read the same must still be told apart by the hardware,
   and the hardware is checked again right before each write.
 - What the job writes as root never goes through a folder someone else owns.
 - The disk password only ever sits in a folder only root can enter, and is
   gone whatever way Setup ends.
"""
import json
import os
import pathlib
import stat
import subprocess
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).parent.parent
FOLDER = ROOT / "usr/lib/calamares/modules/rayedisk"
sys.path.insert(0, str(FOLDER))
import rayedisk_apply as apply  # noqa: E402
import rayedisk_core as core  # noqa: E402
import rayedisk_probe as probe  # noqa: E402

GIB = core.GIB
MIB = core.MIB


# ---- reading the disk ------------------------------------------------------

def blk(node, size=256 * GIB, children=(), fstype=None, uuid=None, mounts=(None,)):
    return {"path": node, "type": "disk", "size": size, "model": "Disk", "rm": False, "tran": "sata",
            "fstype": fstype, "label": None, "uuid": uuid, "mountpoints": list(mounts), "log-sec": 512,
            "children": list(children)}


def part(node, size=10 * GIB, fstype="ext4", mounts=(None,), children=()):
    return {"path": node, "type": "part", "size": size, "fstype": fstype, "label": "", "uuid": None,
            "mountpoints": list(mounts), "children": list(children)}


def gpt(node, parts):
    return json.dumps({"partitiontable": {
        "label": "gpt", "id": "X", "device": node, "unit": "sectors", "firstlba": 2048,
        "lastlba": 500000000, "sectorsize": 512,
        "partitions": [dict(node=n, start=2048 + i * 30000000, size=s, type=t)
                       for i, (n, s, t) in enumerate(parts)]}})


class Machine:
    """Answers the probe's commands for made-up disks.

    tables: {node: sfdisk --json text, or None when sfdisk fails}
    signatures: {node: [wipefs types], or None when wipefs fails}
    serials: {node: serial}
    """

    def __init__(self, disks, tables=None, signatures=None, serials=None, preflight=(0, ""),
                 hardware_fails=()):
        self.disks = disks
        self.tables = tables or {}
        self.signatures = signatures or {}
        self.serials = serials or {}
        self.preflight = preflight
        self.hardware_fails = set(hardware_fails)

    def __call__(self, argv, timeout=60):
        tool, last = argv[0], argv[-1]
        if tool == "lsblk":
            return 0, json.dumps({"blockdevices": self.disks})
        if tool == "sfdisk" and "--json" in argv:
            text = self.tables.get(last)
            return (1, "") if text is None else (0, text)
        if tool == "sfdisk" and "--dump" in argv:
            text = self.tables.get(last)
            return (1, "") if text is None else (0, f"label: gpt\ndevice: {last}\n")
        if tool == "wipefs":
            found = self.signatures.get(last, [])
            if found is None:
                return 1, ""
            return 0, json.dumps({"signatures": [{"device": last, "type": t} for t in found]})
        if tool == "udevadm":
            node = argv[-1].split("=", 1)[-1]
            if node in self.hardware_fails:
                return 1, ""
            serial = self.serials.get(node, "S-" + node)
            return 0, (f"DEVNAME={node}\nID_SERIAL=Disk_{serial}\nID_SERIAL_SHORT={serial}\n"
                       f"ID_PATH=pci-0000:00:17.0-ata-1\nID_MODEL=Disk\nID_PART_TABLE_UUID=abc\n")
        if tool == "blockdev":
            for d in self.disks:
                if d["path"] == last:
                    return 0, f"{d['size']}\n"
            return 1, ""
        if tool.endswith("raye-preflight"):
            return self.preflight
        if tool == "ntfsresize":
            return 0, "You might resize at 42949672960 bytes or 42950 MB\n"
        return 1, ""


def read(machine, look=False):
    return {d["node"]: d for d in probe.read_machine(run=machine, look=look)[1]}


def shown(machine):
    firmware, disks = probe.read_machine(run=machine, look=False)
    return {d["node"]: d for d in core.report(firmware, disks)["disks"]}


def test_a_table_sfdisk_cannot_read_never_hides_the_stick_raye_started_from():
    """sfdisk failing used to leave an empty table, so the partition mounted
    on /run/live/medium was never looked at: live=false, empty=true, and the
    page picked "erase" for the person."""
    m = Machine([blk("/dev/sdd", children=[part("/dev/sdd1", mounts=["/run/live/medium"])])],
                signatures={"/dev/sdd": ["gpt", "PMBR"]})
    disk = shown(m)["/dev/sdd"]
    assert disk["live"] is True
    assert disk["blocked"] != ""
    assert disk["empty"] is False
    assert {"mode": "erase"} not in disk["options"]


def test_a_table_sfdisk_cannot_read_is_blocked_even_with_nothing_mounted():
    m = Machine([blk("/dev/sdd", children=[part("/dev/sdd1"), part("/dev/sdd2")])],
                signatures={"/dev/sdd": ["gpt", "PMBR"]})
    disk = shown(m)["/dev/sdd"]
    assert disk["blocked"] == "unreadable"
    assert disk["empty"] is False and disk["options"] == []


def test_a_disk_that_cannot_be_read_at_all_is_blocked_not_empty():
    m = Machine([blk("/dev/sdd")], signatures={"/dev/sdd": None})
    disk = shown(m)["/dev/sdd"]
    assert disk["blocked"] == "unreadable"
    assert disk["empty"] is False and disk["options"] == []


def test_a_table_wipefs_sees_but_sfdisk_cannot_read_is_blocked():
    """No partition known to the kernel, but a table is there all the same."""
    m = Machine([blk("/dev/sdd")], signatures={"/dev/sdd": ["dos"]})
    assert shown(m)["/dev/sdd"]["blocked"] == "unreadable"


def test_a_partition_the_kernel_shows_and_sfdisk_does_not_blocks_the_disk():
    m = Machine([blk("/dev/sda", children=[part("/dev/sda1"), part("/dev/sda2", mounts=["/home"])])],
                tables={"/dev/sda": gpt("/dev/sda", [("/dev/sda1", 2097152, core.LINUX_TYPE)])})
    assert shown(m)["/dev/sda"]["blocked"] == "unreadable"


def test_what_holds_a_partition_is_seen_without_sfdisk():
    m = Machine([blk("/dev/sdc", children=[part("/dev/sdc1", fstype="crypto_LUKS", children=[
                    {"path": "/dev/mapper/x", "type": "crypt", "mountpoints": ["/data"]}])])],
                signatures={"/dev/sdc": ["gpt", "PMBR"]})
    disk = read(m)["/dev/sdc"]
    assert "crypt" in disk["holders"]


def test_a_blank_disk_is_still_empty_and_offers_erase():
    m = Machine([blk("/dev/sdd")], signatures={"/dev/sdd": []})
    disk = shown(m)["/dev/sdd"]
    assert disk["blocked"] == "" and disk["empty"] is True
    assert disk["table"] == "none"
    assert disk["options"] == [{"mode": "erase"}]


def test_a_disk_holding_one_filesystem_is_readable_but_not_empty():
    m = Machine([blk("/dev/sdd", fstype="ext4", uuid="1111")], signatures={"/dev/sdd": ["ext4"]})
    disk = shown(m)["/dev/sdd"]
    assert disk["blocked"] == "" and disk["empty"] is False
    assert disk["options"] == [{"mode": "erase"}]


def test_a_disk_whose_hardware_cannot_be_read_is_blocked():
    m = Machine([blk("/dev/sdd")], signatures={"/dev/sdd": []}, hardware_fails={"/dev/sdd"})
    disk = shown(m)["/dev/sdd"]
    assert disk["blocked"] == "unreadable" and disk["options"] == []


def test_the_job_refuses_a_disk_it_cannot_read():
    m = Machine([blk("/dev/sdd")], signatures={"/dev/sdd": None})
    disk = read(m)["/dev/sdd"]
    with pytest.raises(core.Refused) as no:
        core.plan(disk, "efi", {"mode": "erase", "disk": "/dev/sdd", "id": disk["id"]}, False)
    assert no.value.code == "unreadable"


def test_findings_that_could_not_be_read_count_as_trouble():
    """raye-preflight that never ran is not "nothing found": Windows could be
    hibernated, another system could own the EFI partition."""
    m = Machine([blk("/dev/sda", children=[part("/dev/sda1", fstype="vfat"), part("/dev/sda2", fstype="ntfs")])],
                tables={"/dev/sda": gpt("/dev/sda", [("/dev/sda1", 2097152, core.ESP_TYPE),
                                                     ("/dev/sda2", 20971520, core.MS_BASIC_TYPE)])},
                preflight=(127, ""))
    parts = read(m)["/dev/sda"]["parts"]
    assert "shared-efi" in parts[0]["findings"]
    assert "ntfs-unknown" in parts[1]["findings"]


def test_every_reason_a_disk_is_blocked_has_words_in_both_languages():
    logic = (ROOT / "etc/calamares/branding/raye/components/DiskLogic.js").read_text()
    strings = (ROOT / "etc/calamares/branding/raye/strings.js").read_text()
    assert 'case "unreadable": return S.t(lang, "diskBlockedUnreadable")' in logic
    assert strings.count("diskBlockedUnreadable:") == 2
    job = (FOLDER / "main.py").read_text()
    assert job.count('"unreadable":') == 2 and job.count('"unsafe-folder":') == 2


# ---- telling two disks apart -----------------------------------------------

def test_two_disks_with_no_table_of_the_same_size_and_kind_have_different_ids():
    """Two sticks holding one ext4 each, same size: the old fingerprint was
    "none <size> ext4" for both, so swapping them kept the consent."""
    m = Machine([blk("/dev/sdd", size=64 * GIB, fstype="ext4", uuid="aaaa"),
                 blk("/dev/sde", size=64 * GIB, fstype="ext4", uuid="aaaa")],
                signatures={"/dev/sdd": ["ext4"], "/dev/sde": ["ext4"]},
                serials={"/dev/sdd": "ONE", "/dev/sde": "TWO"})
    disks = read(m)
    assert disks["/dev/sdd"]["id"] != disks["/dev/sde"]["id"]


def test_the_same_stick_with_a_new_filesystem_has_a_new_id():
    one = read(Machine([blk("/dev/sdd", fstype="ext4", uuid="aaaa")], signatures={"/dev/sdd": ["ext4"]}))
    two = read(Machine([blk("/dev/sdd", fstype="ext4", uuid="bbbb")], signatures={"/dev/sdd": ["ext4"]}))
    assert one["/dev/sdd"]["id"] != two["/dev/sdd"]["id"]


def test_the_hardware_identity_leaves_out_what_the_install_itself_changes():
    m = Machine([blk("/dev/sdd")])
    text = probe.hardware_of("/dev/sdd", run=m)
    assert "ID_SERIAL_SHORT=S-/dev/sdd" in text and "ID_PATH=pci-0000:00:17.0-ata-1" in text
    assert "PART_TABLE" not in text
    assert probe.hardware_of("/dev/sdd", run=Machine([blk("/dev/sdd")], hardware_fails={"/dev/sdd"})) == ""


def test_the_plan_carries_the_hardware_it_was_made_for():
    disk = read(Machine([blk("/dev/sdd")], signatures={"/dev/sdd": []}))["/dev/sdd"]
    made = core.plan(disk, "efi", {"mode": "erase", "disk": "/dev/sdd", "id": disk["id"]}, False)
    assert made["hardware"] == disk["hardware"] != ""


class Calls:
    """Stands in for every command; nothing here can touch a disk."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, feed=None, tolerate=False):
        self.calls.append(argv)
        if argv[0] == "blkid":
            return "1111\n"
        return ""

    def writes(self):
        return [a for a in self.calls if a[0] in ("sfdisk", "ntfsresize", "mkfs.vfat", "mkfs.ext4",
                                                  "mkfs.btrfs", "cryptsetup")
                and "--dump" not in a and "--info" not in a]


def erase_plan(hardware="serial=ONE"):
    disk = {"node": "/dev/sdz", "size": 256 * GIB, "sector": 512, "table": "gpt", "first": 2048,
            "last": 500000000, "id": "x", "hardware": hardware, "parts": [], "holders": [], "live": False}
    return disk, core.plan(disk, "efi", {"mode": "erase", "disk": "/dev/sdz", "id": "x"}, False)


@pytest.fixture
def private(tmp_path, monkeypatch):
    folder = tmp_path / "root-only"
    monkeypatch.setattr(apply, "BACKUP_DIR", str(folder))
    return folder


def test_a_disk_swapped_after_the_choice_is_never_written(private):
    disk, plan = erase_plan()
    run = Calls()
    w = apply.Writer(run, lambda node: {"parts": []}, identify=lambda node: "serial=TWO")
    with pytest.raises(core.Refused) as no:
        w.apply(plan, disk, "")
    assert no.value.code == "disk-changed"
    assert run.writes() == []


def test_the_hardware_is_checked_again_right_before_the_table_is_written(private):
    """A shrink takes minutes: a stick pulled and another put in meanwhile
    takes the same /dev name."""
    disk, plan = erase_plan()
    run = Calls()
    seen = iter(["serial=ONE"])
    w = apply.Writer(run, lambda node: {"parts": []}, identify=lambda node: next(seen, "serial=TWO"))
    with pytest.raises(core.Refused):
        w.apply(plan, disk, "")
    assert [a for a in run.writes() if a[0] == "sfdisk"] == []


def test_a_plan_with_no_hardware_identity_is_never_written(private):
    disk, plan = erase_plan(hardware="")
    run = Calls()
    w = apply.Writer(run, lambda node: {"parts": []}, identify=lambda node: "")
    with pytest.raises(core.Refused):
        w.apply(plan, disk, "")
    assert run.writes() == []


def test_the_job_checks_the_hardware_through_the_probe():
    text = (FOLDER / "main.py").read_text()
    assert "identify=" in text and "hardware_of" in text


# ---- what root writes ------------------------------------------------------

def test_the_old_table_is_kept_in_a_folder_only_root_can_enter():
    assert not apply.BACKUP_DIR.startswith("/run/raye-setup/")
    assert apply.BACKUP_DIR != "/run/raye-setup"
    logs = (ROOT / "usr/libexec/raye-install-logs").read_text()
    assert apply.BACKUP_DIR + "/disk-before-" in logs


def test_the_backup_never_follows_a_link_planted_where_it_goes(private):
    private.mkdir(mode=0o700)
    victim = private.parent / "shadow"
    victim.write_text("root:x:0:0\n")
    (private / "disk-before-sdz.sfdisk").symlink_to(victim)
    disk, plan = erase_plan()
    w = apply.Writer(Calls(), lambda node: {"parts": []}, identify=lambda node: "serial=ONE")
    w.wait_for = lambda nodes: None
    with pytest.raises(core.Refused):
        # the stand-in table never reads back as written: stops after the backup
        w.apply(plan, disk, "")
    assert victim.read_text() == "root:x:0:0\n"
    saved = private / "disk-before-sdz.sfdisk"
    assert not saved.is_symlink() and saved.is_file()
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600


def test_a_backup_folder_others_could_reach_is_refused_before_anything_is_written(private):
    private.mkdir(mode=0o755)
    os.chmod(private, 0o755)
    disk, plan = erase_plan()
    run = Calls()
    w = apply.Writer(run, lambda node: {"parts": []}, identify=lambda node: "serial=ONE")
    with pytest.raises(core.Refused) as no:
        w.apply(plan, disk, "")
    assert no.value.code == "unsafe-folder"
    assert run.calls == []


def test_a_backup_folder_that_is_a_link_is_refused(private, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir(mode=0o700)
    private.symlink_to(elsewhere)
    disk, plan = erase_plan()
    run = Calls()
    w = apply.Writer(run, lambda node: {"parts": []}, identify=lambda node: "serial=ONE")
    with pytest.raises(core.Refused) as no:
        w.apply(plan, disk, "")
    assert no.value.code == "unsafe-folder"
    assert list(elsewhere.iterdir()) == []


def test_a_missing_backup_folder_is_made_for_root_only(private):
    disk, plan = erase_plan()
    w = apply.Writer(Calls(), lambda node: {"parts": []}, identify=lambda node: "serial=ONE")
    w.wait_for = lambda nodes: None
    with pytest.raises(core.Refused):
        w.apply(plan, disk, "")
    assert stat.S_IMODE(private.stat().st_mode) == 0o700


# ---- the disk password -----------------------------------------------------

PRIVATE = "/run/raye-setup-root"


def test_the_page_hands_the_password_over_through_the_private_folder():
    page = (ROOT / "etc/calamares/branding/raye/pages/Disk.qml").read_text()
    requests = (ROOT / "etc/calamares/branding/raye/components/Requests.js").read_text()
    assert 'Requests.write("answer-disk-passphrase"' not in page
    assert 'Requests.secret("answer-disk-passphrase"' in page
    assert f'var privateFolder = "file://{PRIVATE}/"' in requests
    secret = requests[requests.index("function secret("):]
    secret = secret[:secret.index("\n}\n")]
    assert "privateFolder" in secret and "folder + " not in secret


def test_the_job_reads_the_password_from_the_private_folder():
    import importlib.util
    lib = types.ModuleType("libcalamares")
    lib.job = types.SimpleNamespace(working_path=str(FOLDER))
    sys.modules["libcalamares"] = lib
    try:
        spec = importlib.util.spec_from_file_location("rayedisk_main_check", FOLDER / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop("libcalamares", None)
    assert module.PASSPHRASE == PRIVATE + "/answer-disk-passphrase"


@pytest.fixture
def job(monkeypatch, tmp_path):
    lib = types.ModuleType("libcalamares")
    lib.globalstorage = types.SimpleNamespace(insert=lambda *a: None)
    lib.job = types.SimpleNamespace(setprogress=lambda part: None, working_path=str(FOLDER))
    lib.utils = types.SimpleNamespace(debug=lambda text: None, warning=lambda text: None)
    monkeypatch.setitem(sys.modules, "libcalamares", lib)
    import importlib.util
    spec = importlib.util.spec_from_file_location("rayedisk_main_safety", FOLDER / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    secret = tmp_path / "root-only"
    secret.mkdir(mode=0o700)
    monkeypatch.setattr(module, "ANSWER", str(tmp_path / "answer-disk"))
    monkeypatch.setattr(module, "PASSPHRASE", str(secret / "answer-disk-passphrase"))
    monkeypatch.setattr(module, "CHOICES", str(tmp_path / "choices"))
    module.folder = tmp_path
    module.secret = secret / "answer-disk-passphrase"
    return module


def test_the_password_goes_even_when_the_answer_is_not_encrypted(job, monkeypatch):
    job.secret.write_text("s3cret words")
    (job.folder / "answer-disk").write_text(json.dumps({"mode": "erase", "disk": "/dev/sda", "id": "x"}))
    monkeypatch.setattr(job, "read_machine", lambda look=False: ("efi", []))
    job.run()
    assert not job.secret.exists()


def test_the_password_is_gone_when_the_job_refuses(job, monkeypatch):
    job.secret.write_text("s3cret words")
    monkeypatch.setattr(job, "read_machine", lambda look=False: ("efi", []))
    job.run()
    assert not job.secret.exists()


def test_a_password_file_that_is_a_link_is_not_followed(job, tmp_path):
    target = tmp_path / "elsewhere"
    target.write_text("not the password")
    job.secret.symlink_to(target)
    assert job.take_passphrase() == ""
    assert not job.secret.is_symlink() and target.read_text() == "not the password"


HELPER = ROOT / "usr/libexec/raye-setup-private"


@pytest.mark.skipif(os.geteuid() != 0, reason="the helper hands its folder to root: it only runs as root")
def test_the_helper_makes_the_folder_root_only_and_empties_the_password(tmp_path):
    folder = tmp_path / "root-only"
    subprocess.run([str(HELPER), "prepare", str(folder)], check=True)
    secret = folder / "answer-disk-passphrase"
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700 and folder.stat().st_uid == 0
    assert secret.read_text() == "" and stat.S_IMODE(secret.stat().st_mode) == 0o600
    secret.write_text("s3cret words")
    (folder / "answer-disk").write_text("{}")
    # Setup started again after a crash: nothing of the last run is left
    subprocess.run([str(HELPER), "prepare", str(folder)], check=True)
    assert secret.read_text() == "" and not (folder / "answer-disk").exists()
    secret.write_text("s3cret words")
    subprocess.run([str(HELPER), "clear", str(folder)], check=True)
    assert not secret.exists()


@pytest.mark.skipif(os.geteuid() != 0, reason="the helper hands its folder to root: it only runs as root")
def test_the_helper_never_follows_a_link_in_place_of_its_folder(tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir(mode=0o755)
    folder = tmp_path / "root-only"
    folder.symlink_to(elsewhere)
    subprocess.run([str(HELPER), "prepare", str(folder)], check=True)
    assert not folder.is_symlink() and folder.is_dir()
    assert list(elsewhere.iterdir()) == []
    assert stat.S_IMODE(elsewhere.stat().st_mode) == 0o755


def test_the_helper_is_shipped():
    paths = (ROOT / "debian/raye-paths").read_text()
    assert "calamares-settings-raye  usr/libexec/raye-setup-private" in paths
    assert os.access(HELPER, os.X_OK)


def _code(path):
    return "\n".join(line.split("#", 1)[0] for line in path.read_text().splitlines())


def test_setup_session_prepares_the_folder_before_each_start_and_clears_it_after():
    text = _code(ROOT / "usr/libexec/raye-setup-run")
    loop = text[text.index("while :; do"):]
    start = loop.index("calamares\n")
    assert "raye-setup-private prepare" in loop[:start]
    assert "raye-setup-private clear" in loop[start:]
    assert "raye-setup-private clear" in text[text.index("done", text.index("while :; do")):]


def test_starting_setup_from_the_desktop_clears_the_password_on_any_exit():
    text = _code(ROOT / "usr/bin/raye-install")
    assert "exec sudo" not in text
    assert "raye-setup-private prepare" in text
    assert "trap" in text and "raye-setup-private clear" in text
    assert text.index("raye-setup-private prepare") < text.index("calamares")
