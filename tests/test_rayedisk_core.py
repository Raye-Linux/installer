# SPDX-License-Identifier: GPL-3.0-or-later
"""The rules of the disk page, on made-up disks. Nothing here touches one."""
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
             "sectors": sectors(size_gib), "type": ptype, "fstype": fstype}
    entry.update(more)
    return entry


def disk(parts, size_gib=256, table="gpt", **more):
    total = sectors(size_gib)
    entry = {"node": "/dev/sda", "model": "Test", "size": total * SECTOR, "sector": SECTOR,
             "table": table, "first": 2048, "last": total - 34, "parts": parts, "id": "abc"}
    entry.update(more)
    return entry


def windows(findings=(), used_gib=40, size_gib=200, after_gib=0):
    esp = part(1, 2048, 0.1, core.ESP_TYPE, "vfat", label="SYSTEM")
    msr = part(2, 2048 + sectors(0.1), 0.016, core.MS_RESERVED_TYPE)
    start = align(2048 + sectors(0.1) + sectors(0.016))
    win = part(3, start, size_gib, core.MS_BASIC_TYPE, "ntfs", os="Windows",
               shrink_minimum=used_gib * GIB, findings=list(findings))
    rec_start = start + sectors(size_gib) + sectors(after_gib)
    rec = part(4, rec_start, 0.6, core.MS_RECOVERY_TYPE, "ntfs")
    return [esp, msr, win, rec]


def align(sector):
    return core.align_up(sector, 2048)


def option(options, mode):
    return [o for o in options if o["mode"] == mode]


def answer(mode, **more):
    entry = {"mode": mode, "disk": "/dev/sda", "id": "abc", "encrypt": False}
    entry.update(more)
    return entry


# what the page is offered

def test_a_blank_disk_only_offers_erase():
    options, refused = core.options_for(disk([], table="none"))
    assert [o["mode"] for o in options] == ["erase"]
    assert refused == []


def test_a_healthy_windows_can_be_shrunk_and_its_limits_hold():
    options, refused = core.options_for(disk(windows()))
    shrink = option(options, "shrink")
    assert refused == []
    assert len(shrink) == 1, "the recovery partition is NTFS too and is not offered"
    assert shrink[0]["node"] == "/dev/sda3"
    # never under what Windows uses plus its room
    assert shrink[0]["keepMin"] >= 40 * GIB + core.WINDOWS_ROOM
    # Raye always fits in what is left
    assert shrink[0]["total"] - shrink[0]["keepMax"] >= core.RAYE_NEEDS
    assert shrink[0]["keepMin"] <= shrink[0]["keepDefault"] <= shrink[0]["keepMax"]


@pytest.mark.parametrize("finding", sorted(core.SHRINK_BLOCKERS))
def test_a_volume_ntfsresize_would_refuse_is_never_offered(finding):
    options, refused = core.options_for(disk(windows([finding])))
    assert option(options, "shrink") == []
    assert refused[0]["finding"] == finding
    # erasing is still possible: it does not need the volume to agree
    assert option(options, "erase")


def test_a_volume_whose_size_nobody_read_is_not_shrunk():
    parts = windows()
    del parts[2]["shrink_minimum"]
    options, refused = core.options_for(disk(parts))
    assert option(options, "shrink") == []
    assert refused[0]["finding"] == "ntfs-unknown"


def test_a_full_windows_is_not_offered():
    options, _ = core.options_for(disk(windows(used_gib=180)))
    assert option(options, "shrink") == []


def test_free_space_is_offered_when_it_fits_and_not_when_it_does_not():
    roomy = disk(windows(size_gib=100))
    assert [o["mode"] for o in core.options_for(roomy)[0]].count("free") == 1
    tight = disk(windows(size_gib=100), size_gib=120)
    assert option(core.options_for(tight)[0], "free") == []


def test_an_old_partition_table_gets_a_reason_and_only_erase():
    old = disk([part(1, 2048, 100, "7", "ntfs")], table="dos")
    options, refused = core.options_for(old)
    assert [o["mode"] for o in options] == ["erase"]
    assert refused == [{"mode": "beside", "reason": "old-table"}]


def test_a_shared_efi_folder_stops_every_install_beside_it():
    parts = windows()
    parts[0]["findings"] = ["shared-efi"]
    options, refused = core.options_for(disk(parts))
    assert [o["mode"] for o in options] == ["erase"]
    assert {"mode": "beside", "reason": "shared-efi"} in refused


def test_the_usb_stick_and_small_or_busy_disks_offer_nothing():
    made = core.report("efi", [disk([], live=True),
                               disk([], size_gib=20),
                               disk([part(1, 2048, 100)], holders=["lvm"])])["disks"]
    assert [d["blocked"] for d in made] == ["live", "small", "in-use"]
    assert all(d["options"] == [] for d in made)


def test_the_efi_and_recovery_partitions_cannot_be_replaced():
    options, _ = core.options_for(disk(windows()))
    assert {o["node"] for o in option(options, "replace")} == {"/dev/sda3"}


def test_a_mounted_partition_is_neither_shrunk_nor_replaced():
    parts = windows()
    parts[2]["mounted"] = True
    options, _ = core.options_for(disk(parts))
    assert option(options, "shrink") == [] and option(options, "replace") == []


# what a plan does

def test_erase_writes_esp_boot_and_root_and_keeps_the_table_backup_clear():
    d = disk([], table="none")
    made = core.plan(d, "efi", answer("erase"), False)
    assert made["wipe"]
    assert [n["role"] for n in made["add"]] == ["esp", "boot", "root"]
    assert made["add"][0]["start"] == 2048
    assert made["add"][-1]["start"] + made["add"][-1]["sectors"] <= d["last"]
    assert all(n["start"] % 2048 == 0 and n["sectors"] % 2048 == 0 for n in made["add"])


def test_encrypting_needs_a_passphrase():
    d = disk([], table="none")
    made = core.plan(d, "efi", answer("erase", encrypt=True), True)
    assert [n["role"] for n in made["add"]] == ["esp", "boot", "root"]
    with pytest.raises(core.Refused) as no:
        core.plan(d, "efi", answer("erase", encrypt=True), False)
    assert no.value.code == "no-passphrase"


def plans_of_every_mode(encrypt):
    blank = disk([], table="none")
    roomy = disk(windows(size_gib=100))
    free = [r for r in core.free_regions(roomy) if r["sectors"] * SECTOR >= core.need_on(roomy)][0]
    shrink, _ = shrink_answer(disk(windows()))
    asked = [(blank, answer("erase")),
             (roomy, answer("free", start=free["start"])),
             (disk(windows()), answer("replace", partition="/dev/sda3")),
             (disk(windows()), shrink)]
    for d, a in asked:
        a["encrypt"] = encrypt
        yield a["mode"], core.plan(d, "efi", a, encrypt)


@pytest.mark.parametrize("encrypt", [False, True])
def test_boot_has_its_own_partition_with_or_without_encryption(encrypt):
    # GRUB cannot write recordfail on btrfs, and Ubuntu's 00_header then
    # shows the menu for GRUB_RECORDFAIL_TIMEOUT seconds on every start
    for mode, made in plans_of_every_mode(encrypt):
        roles = [n["role"] for n in made["add"]]
        assert roles[-2:] == ["boot", "root"], mode
        boot = made["add"][-2]
        assert boot["name"] == "raye_boot", mode
        assert boot["sectors"] * SECTOR == core.BOOT_SIZE, mode
        assert made["add"][-1]["sectors"] * SECTOR >= core.RAYE_MINIMUM, mode


def test_the_largest_keep_offered_still_leaves_room_for_boot():
    d = disk(windows())
    a, offered = shrink_answer(d, keep=None)
    a["keep"] = offered["keepMax"]
    made = core.plan(d, "efi", a, False)
    assert [n["role"] for n in made["add"]] == ["boot", "root"]


@pytest.mark.parametrize("change,code", [
    ({"id": "other"}, "disk-changed"),
    ({"disk": "/dev/sdb"}, "disk-changed"),
    ({"mode": "wipe-everything"}, "no-choice"),
])
def test_an_answer_that_no_longer_matches_is_refused(change, code):
    with pytest.raises(core.Refused) as no:
        core.plan(disk(windows()), "efi", {**answer("erase"), **change}, False)
    assert no.value.code == code


def test_a_machine_without_efi_is_refused():
    with pytest.raises(core.Refused) as no:
        core.plan(disk([], table="none"), "bios", answer("erase"), False)
    assert no.value.code == "no-efi"


def test_the_usb_stick_is_refused_even_if_the_page_asked():
    with pytest.raises(core.Refused) as no:
        core.plan(disk([], live=True), "efi", answer("erase"), False)
    assert no.value.code == "live"


def shrink_answer(d, keep=None):
    offered = option(core.options_for(d)[0], "shrink")[0]
    return answer("shrink", partition=offered["node"],
                  keep=offered["keepDefault"] if keep is None else keep), offered


def test_shrink_keeps_the_start_and_the_new_partitions_stay_in_the_gap():
    d = disk(windows())
    a, offered = shrink_answer(d)
    made = core.plan(d, "efi", a, False)
    win = d["parts"][2]
    assert made["shrink"]["start"] == win["start"]
    assert made["shrink"]["bytes"] <= a["keep"]
    assert made["shrink"]["bytes"] >= win["shrink_minimum"]
    assert made["reuse_esp"] == "/dev/sda1"
    assert [n["role"] for n in made["add"]] == ["boot", "root"]
    root = made["add"][-1]
    assert root["start"] >= win["start"] + made["shrink"]["sectors"]
    assert root["start"] + root["sectors"] <= win["start"] + win["sectors"]
    assert root["sectors"] * SECTOR >= core.RAYE_MINIMUM


@pytest.mark.parametrize("delta", [-1, +1])
def test_a_size_outside_the_offer_is_refused(delta):
    d = disk(windows())
    _, offered = shrink_answer(d)
    keep = offered["keepMin"] - MIB if delta < 0 else offered["keepMax"] + MIB
    with pytest.raises(core.Refused) as no:
        core.plan(d, "efi", answer("shrink", partition="/dev/sda3", keep=keep), False)
    assert no.value.code == "keep-out-of-range"


def test_shrink_refuses_a_volume_that_turned_hibernated_since_the_page():
    d = disk(windows(["hibernated"]))
    with pytest.raises(core.Refused) as no:
        core.plan(d, "efi", answer("shrink", partition="/dev/sda3", keep=100 * GIB), False)
    assert no.value.code == "hibernated"


def test_shrink_never_touches_a_partition_that_is_not_ntfs():
    parts = windows()
    parts[2]["fstype"] = "ext4"
    with pytest.raises(core.Refused) as no:
        core.plan(disk(parts), "efi", answer("shrink", partition="/dev/sda3", keep=100 * GIB), False)
    assert no.value.code == "cannot-shrink"


def test_no_efi_partition_on_the_disk_gets_one_of_its_own_in_the_new_room():
    parts = [part(1, 2048, 100)]
    made = core.plan(disk(parts), "efi",
                     answer("free", start=core.free_regions(disk(parts))[0]["start"]), False)
    assert made["reuse_esp"] is None
    assert [n["role"] for n in made["add"]] == ["esp", "boot", "root"]


def test_replace_stays_inside_the_partition_it_replaces():
    parts = windows()
    made = core.plan(disk(parts), "efi", answer("replace", partition="/dev/sda3"), False)
    win = parts[2]
    assert made["delete"]["number"] == 3
    assert made["add"][0]["start"] >= win["start"]
    assert made["add"][-1]["start"] + made["add"][-1]["sectors"] <= win["start"] + win["sectors"]


def test_the_efi_partition_cannot_be_named_by_a_forged_answer():
    with pytest.raises(core.Refused) as no:
        core.plan(disk(windows()), "efi", answer("replace", partition="/dev/sda1"), False)
    assert no.value.code == "not-offered"


# what gets checked after writing

def after(parts):
    return {"parts": parts}


def test_a_changed_neighbour_stops_the_install_before_anything_is_formatted():
    d = disk(windows())
    a, _ = shrink_answer(d)
    made = core.plan(d, "efi", a, False)
    written = [dict(p) for p in d["parts"]]
    written[2]["sectors"] = made["shrink"]["sectors"]
    for number, new in enumerate(made["add"], 5):
        written.append({"node": f"/dev/sda{number}", "start": new["start"],
                        "sectors": new["sectors"], "type": new["type"]})
    assert core.check_written(d, after(written), made) == {"boot": "/dev/sda5", "root": "/dev/sda6"}
    bad = [dict(p) for p in written]
    bad[3]["sectors"] -= 2048
    with pytest.raises(core.Refused) as no:
        core.check_written(d, after(bad), made)
    assert no.value.code == "table-mismatch"
    gone = [dict(p) for p in written if p["node"] != "/dev/sda1"]
    with pytest.raises(core.Refused):
        core.check_written(d, after(gone), made)
    # the shrink itself must have landed at the agreed size
    not_shrunk = [dict(p) for p in written]
    not_shrunk[2]["sectors"] = d["parts"][2]["sectors"]
    with pytest.raises(core.Refused):
        core.check_written(d, after(not_shrunk), made)


def test_reading_what_ntfsresize_said():
    text = ("ntfsresize v2022.10.3\nCluster size : 4096\n"
            "You might resize at 8589934592 bytes or 8590 MB (freeing 91 GB).\n")
    assert core.bytes_of_ntfsresize(text) == 8589934592
    assert core.bytes_of_ntfsresize("nothing to see") is None
