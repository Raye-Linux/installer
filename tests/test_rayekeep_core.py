# SPDX-License-Identifier: GPL-3.0-or-later
""""Replace and keep my files": when it is offered, and what a plan does.

Made-up disks, like test_rayedisk_linux.py.
"""
import importlib.util
import pathlib

import pytest

MODULE = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedisk/rayedisk_core.py"
spec = importlib.util.spec_from_file_location("rayedisk_core_keep", MODULE)
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


def kept(files_gib=20, files=5000, home=None, system="linux"):
    users = [{"name": "alice", "home": "alice", "uid": 1000,
              "folders": [{"kind": "documents", "path": "Documents", "files": files, "bytes": int(files_gib * GIB),
                           "unreadable": 0}]}]
    entry = {"system": system, "name": "Linux Mint 22", "base": "home", "users": users}
    if home:
        entry["home"] = home
        entry["base"] = ""
    return entry


def mint(size_gib=200, used_gib=30, files_gib=20, **more):
    esp = part(1, 2048, 0.5, core.ESP_TYPE, "vfat")
    root = part(2, 2048 + sectors(0.5), size_gib, core.LINUX_TYPE, "ext4", os="Linux Mint 22",
                shrink_minimum=used_gib * GIB, keep=kept(files_gib), **more)
    return [esp, root]


def keeps(options):
    return [o for o in options if o["mode"] == "keep"]


def answer(**more):
    entry = {"mode": "keep", "disk": "/dev/sda", "id": "abc", "encrypt": False, "partition": "/dev/sda2"}
    entry.update(more)
    return entry


def test_keep_is_offered_next_to_replace():
    options, refused = core.options_for(disk(mint()))
    assert [o["mode"] for o in options].count("replace") == 1
    option = keeps(options)[0]
    assert option["way"] == "stage" and option["name"] == "Linux Mint 22"
    assert option["files"] == 5000 and option["size"] == 20 * GIB
    assert option["users"] == [{"name": "alice", "folders": [{"kind": "documents", "files": 5000,
                                                              "bytes": 20 * GIB}]}]
    assert refused == []


def test_too_little_room_is_refused_with_what_it_takes():
    # 60 GB disk, 40 GB of files: Raye and two copies don't fit
    options, refused = core.options_for(disk(mint(size_gib=59, used_gib=45, files_gib=40), size_gib=60))
    assert keeps(options) == []
    refusal = [r for r in refused if r["mode"] == "keep"][0]
    assert refusal["reason"] == "room" and refusal["needed"] > refusal["have"]
    # what it takes: Raye, its own copy of the files, and the staging copy
    assert refusal["needed"] >= core.RAYE_NEEDS + 2 * 40 * GIB
    assert any(o["mode"] == "replace" for o in options)


def test_unreadable_files_are_refused_rather_than_promised():
    parts = mint()
    parts[1]["keep"]["users"][0]["folders"][0]["unreadable"] = 2
    options, refused = core.options_for(disk(parts))
    assert keeps(options) == []
    assert [r["reason"] for r in refused if r["mode"] == "keep"] == ["unreadable"]


@pytest.mark.parametrize("blocker", ["linux-check", "hibernated", "bitlocker", "linux-unknown"])
def test_a_volume_that_cannot_shrink_is_not_offered(blocker):
    options, refused = core.options_for(disk(mint(findings=[blocker])))
    assert keeps(options) == []
    assert not [r for r in refused if r["mode"] == "keep"]


def test_nothing_to_keep_offers_nothing():
    parts = mint()
    parts[1]["keep"]["users"] = []
    assert keeps(core.options_for(disk(parts))[0]) == []


def plan_of(parts, size_gib=256, **more):
    return core.plan(disk(parts, size_gib), "efi", answer(**more), False)


def test_stage_plan_keeps_raye_and_the_copies_apart():
    parts = mint()
    result = plan_of(parts)
    old = parts[1]
    stage, add = result["stage"], result["add"]
    assert result["delete"]["node"] == "/dev/sda2"
    assert result["reuse_esp"] == "/dev/sda1"
    # the old volume shrinks to what it uses, never below
    assert result["shrink"]["bytes"] >= 30 * GIB
    assert old["start"] + result["shrink"]["sectors"] <= stage["start"]
    # Raye's partitions sit where the old volume was, in front of the copies
    assert add[0]["start"] >= old["start"]
    assert add[-1]["start"] + add[-1]["sectors"] <= stage["start"]
    # the copies may use the free space behind it too, never past the disk's end
    assert stage["start"] + stage["sectors"] <= core.disk_end(disk(parts))
    assert stage["sectors"] * SECTOR >= core.staged_bytes(5000, 20 * GIB)
    root = add[-1]
    assert root["role"] == "root"
    assert root["sectors"] * SECTOR >= core.RAYE_MINIMUM + core.home_bytes(5000, 20 * GIB) - MIB
    assert result["keep"]["way"] == "stage" and result["keep"]["users"][0]["home"] == "alice"


def test_keep_steps_shrink_first_and_delete_second():
    result = plan_of(mint())
    first, second = core.keep_steps(result)
    assert first["delete"] is None and first["add"] == [result["stage"]]
    assert first["shrink"] == result["shrink"]
    assert second["shrink"] is None and second["delete"] == result["delete"]
    assert [a["role"] for a in second["add"]] == ["boot", "root"]


def test_a_nearly_full_volume_is_left_its_size():
    # the volume is small and full: no shrink, the copies go behind it
    esp = part(1, 2048, 0.5, core.ESP_TYPE, "vfat")
    root = part(2, 2048 + sectors(0.5), 40, core.LINUX_TYPE, "ext4", shrink_minimum=39 * GIB,
                keep=kept(files_gib=5, files=100))
    result = plan_of([esp, root])
    assert result["shrink"] is None
    assert result["stage"]["start"] >= root["start"] + root["sectors"]


def test_stage_plan_is_refused_when_room_is_gone():
    parts = mint(size_gib=59, used_gib=45, files_gib=40)
    with pytest.raises(core.Refused) as no:
        plan_of(parts, size_gib=60)
    assert no.value.code == "keep-room"


def test_plan_without_files_to_keep_is_refused():
    parts = mint()
    del parts[1]["keep"]
    with pytest.raises(core.Refused) as no:
        plan_of(parts)
    assert no.value.code == "cannot-keep"


def home_disk(home_fs="ext4", root_fs="ext4", **home_more):
    esp = part(1, 2048, 0.5, core.ESP_TYPE, "vfat")
    root = part(2, 2048 + sectors(0.5), 40, core.LINUX_TYPE, root_fs, keep=kept(files_gib=150, home="/dev/sda3"))
    home = part(3, root["start"] + root["sectors"], 200, core.LINUX_TYPE, home_fs, **home_more)
    return [esp, root, home]


@pytest.mark.parametrize("root_fs", ["ext4", "xfs", "btrfs"])
def test_separate_home_is_reused_whatever_the_old_root(root_fs):
    options, _ = core.options_for(disk(home_disk(root_fs=root_fs), size_gib=300))
    option = keeps(options)[0]
    assert option["way"] == "home" and option["home"] == "/dev/sda3" and option["homeFs"] == "ext4"


def test_home_plan_replaces_the_root_and_never_names_the_home():
    parts = home_disk()
    result = core.plan(disk(parts, 300), "efi", answer(), False)
    assert result["stage"] is None and result["shrink"] is None
    assert result["delete"]["node"] == "/dev/sda2"
    assert result["keep"]["home"] == "/dev/sda3"
    home = parts[2]
    for new in result["add"]:
        assert new["start"] + new["sectors"] <= home["start"]
    # the home partition reads back unchanged, like any other
    after = {"parts": [parts[0], home] + [{"node": f"/dev/sda{i + 4}", "start": a["start"], "sectors": a["sectors"],
                                          "type": a["type"]} for i, a in enumerate(result["add"])]}
    core.check_written(disk(parts, 300), after, result)


@pytest.mark.parametrize("trouble", [{"mounted": True}, {"findings": ["linux-check"]}, {"fstype": "crypto_LUKS"}])
def test_a_home_partition_in_any_doubt_is_not_reused(trouble):
    parts = home_disk()
    parts[2].update(trouble)
    assert keeps(core.options_for(disk(parts, size_gib=300))[0]) == []


def test_home_on_another_disk_is_found_through_every_disk():
    parts = home_disk()
    other = disk([dict(parts[2], node="/dev/sdb1", number=1, start=2048)], node="/dev/sdb")
    parts[1]["keep"]["home"] = "/dev/sdb1"
    first = disk(parts[:2], size_gib=300)
    report = core.report("efi", [first, other])
    assert keeps(report["disks"][0]["options"])[0]["home"] == "/dev/sdb1"
    assert core.plan(first, "efi", answer(), False, [first, other])["keep"]["home"] == "/dev/sdb1"


def test_windows_keeps_through_the_same_stage():
    esp = part(1, 2048, 0.25, core.ESP_TYPE, "vfat")
    msr = part(2, 2048 + sectors(0.25), 0.015625, core.MS_RESERVED_TYPE)
    win = part(3, msr["start"] + msr["sectors"], 230, core.MS_BASIC_TYPE, "ntfs", os="Windows",
               shrink_minimum=60 * GIB, keep=dict(kept(files_gib=25), system="windows", base="Users",
                                                  name="Windows"))
    rec = part(4, win["start"] + win["sectors"], 0.7, core.MS_RECOVERY_TYPE, "ntfs")
    options, _ = core.options_for(disk([esp, msr, win, rec]))
    assert keeps(options)[0]["name"] == "Windows"
    result = core.plan(disk([esp, msr, win, rec]), "efi", answer(partition="/dev/sda3"), False)
    assert result["stage"]["start"] + result["stage"]["sectors"] <= rec["start"]
    assert result["keep"]["system"] == "windows"


def test_old_table_with_no_slots_left_is_refused():
    parts = mint()
    for p in parts:
        p["type"] = "83"
    parts[0]["type"] = "EF"
    full = disk(parts + [part(3, sectors(201), 5, "83"), part(4, sectors(207), 5, "83")], table="dos")
    assert keeps(core.options_for(full, "bios")[0]) == []
    with pytest.raises(core.Refused):
        core.plan(full, "bios", answer(), False)
