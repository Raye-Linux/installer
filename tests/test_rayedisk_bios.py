# SPDX-License-Identifier: GPL-3.0-or-later
"""Installing on a PC that started in its old BIOS mode. Made-up disks only."""
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


def part(number, start, size_gib, ptype="83", fstype="", **more):
    entry = {"node": f"/dev/sda{number}", "number": number, "start": start,
             "sectors": sectors(size_gib), "type": ptype, "fstype": fstype, "findings": []}
    entry.update(more)
    return entry


def disk(parts, size_gib=256, table="dos", **more):
    total = sectors(size_gib)
    entry = {"node": "/dev/sda", "model": "Old", "size": total * SECTOR, "sector": SECTOR,
             "table": table, "first": 2048, "last": total - (1 if table == "dos" else 34),
             "parts": parts, "id": "abc", "hardware": "hw"}
    entry.update(more)
    return entry


def old_windows(size_gib=150, used_gib=40):
    """Windows installed in BIOS mode: System Reserved, then C:."""
    reserved = part(1, 2048, 0.5, "7", "ntfs", label="System Reserved", shrink_minimum=100 * MIB)
    c = part(2, 2048 + sectors(0.5), size_gib, "7", "ntfs", os="Windows", shrink_minimum=used_gib * GIB)
    return [reserved, c]


def modes(options, mode):
    return [o for o in options if o["mode"] == mode]


def answer(mode, **more):
    entry = {"mode": mode, "disk": "/dev/sda", "id": "abc", "encrypt": False}
    entry.update(more)
    return entry


def roles(made):
    return [n["role"] for n in made["add"]]


def test_erase_on_bios_makes_an_old_style_table_without_efi():
    made = core.plan(disk([], table="none"), "bios", answer("erase"), False)
    assert made["wipe"] and made["label"] == "dos"
    assert roles(made) == ["boot", "root"]
    assert made["add"][0]["bootable"] is True
    assert all(n["type"] == "83" for n in made["add"])
    assert made["firmware"] == "bios"


def test_erase_on_a_huge_bios_disk_uses_gpt_with_a_bios_boot_partition():
    made = core.plan(disk([], size_gib=3000, table="none"), "bios", answer("erase"), False)
    assert made["label"] == "gpt"
    assert roles(made) == ["biosboot", "boot", "root"]
    assert made["add"][0]["type"] == core.BIOS_BOOT_TYPE
    assert made["add"][0]["sectors"] * SECTOR == MIB


def test_erase_on_efi_still_makes_gpt_with_efi():
    made = core.plan(disk([], table="none"), "efi", answer("erase"), False)
    assert made["label"] == "gpt"
    assert roles(made) == ["esp", "boot", "root"]


def test_old_windows_can_be_shrunk_on_bios():
    d = disk(old_windows())
    options, refused = core.options_for(d, "bios")
    assert refused == []
    shrink = modes(options, "shrink")
    assert [o["node"] for o in shrink] == ["/dev/sda2"]
    made = core.plan(d, "bios", answer("shrink", partition="/dev/sda2", keep=shrink[0]["keepDefault"]), False)
    assert roles(made) == ["boot", "root"]
    assert made["reuse_esp"] is None
    # Windows' own boot code refuses a table with two active partitions
    assert not any(n["bootable"] for n in made["add"])


def test_free_space_on_an_old_table_is_offered_on_bios():
    d = disk(old_windows(size_gib=100))
    options, _ = core.options_for(d, "bios")
    free = modes(options, "free")
    assert len(free) == 1
    made = core.plan(d, "bios", answer("free", start=free[0]["start"]), False)
    assert roles(made) == ["boot", "root"]
    assert made["add"][-1]["start"] + made["add"][-1]["sectors"] <= d["last"] + 1


def test_old_table_with_no_slot_left_only_offers_erase():
    parts = old_windows(size_gib=50)
    parts.append(part(3, parts[1]["start"] + parts[1]["sectors"], 20, "83", "ext4"))
    options, refused = core.options_for(disk(parts), "bios")
    assert modes(options, "free") == [] and modes(options, "shrink") == []
    assert {"mode": "beside", "reason": "full-table"} in refused
    # replacing one partition frees its slot: one stays, Raye takes two
    assert modes(options, "erase")


def test_replace_on_an_old_table_with_three_partitions_fits():
    parts = old_windows(size_gib=50)
    parts.append(part(3, parts[1]["start"] + parts[1]["sectors"], 60, "83", "ext4"))
    options, _ = core.options_for(disk(parts), "bios")
    assert "/dev/sda3" in [o["node"] for o in modes(options, "replace")]
    made = core.plan(disk(parts), "bios", answer("replace", partition="/dev/sda3"), False)
    assert roles(made) == ["boot", "root"]


def test_extended_partition_keeps_raye_off_the_old_table():
    parts = old_windows(size_gib=50)
    parts.append(part(3, parts[1]["start"] + parts[1]["sectors"], 20, "5"))
    options, refused = core.options_for(disk(parts), "bios")
    assert [o["mode"] for o in options] == ["erase"]
    assert {"mode": "beside", "reason": "full-table"} in refused


def test_old_table_stays_erase_only_when_the_pc_started_in_efi():
    options, refused = core.options_for(disk(old_windows()), "efi")
    assert [o["mode"] for o in options] == ["erase"]
    assert refused == [{"mode": "beside", "reason": "old-table"}]


def test_gpt_on_bios_gets_a_bios_boot_partition_when_it_has_none():
    parts = [part(1, 2048, 100, core.LINUX_TYPE, "ext4", os="Debian", shrink_minimum=20 * GIB)]
    d = disk(parts, table="gpt")
    free = modes(core.options_for(d, "bios")[0], "free")[0]
    made = core.plan(d, "bios", answer("free", start=free["start"]), False)
    assert roles(made) == ["biosboot", "boot", "root"]


def test_gpt_on_bios_reuses_its_bios_boot_partition():
    parts = [part(1, 2048, 0.001, core.BIOS_BOOT_TYPE),
             part(2, 4096, 100, core.LINUX_TYPE, "ext4", os="Debian", shrink_minimum=20 * GIB)]
    d = disk(parts, table="gpt")
    options = core.options_for(d, "bios")[0]
    assert "/dev/sda1" not in [o.get("node") for o in options]
    free = modes(options, "free")[0]
    made = core.plan(d, "bios", answer("free", start=free["start"]), False)
    assert roles(made) == ["boot", "root"]


def test_report_names_the_firmware_and_offers_for_it():
    made = core.report("bios", [disk(old_windows())])
    assert made["firmware"] == "bios"
    assert modes(made["disks"][0]["options"], "shrink")


def test_an_unknown_firmware_is_refused():
    with pytest.raises(core.Refused) as no:
        core.plan(disk([], table="none"), "", answer("erase"), False)
    assert no.value.code == "no-efi"


def test_old_table_script_has_types_and_the_boot_flag():
    made = core.plan(disk([], table="none"), "bios", answer("erase"), False)
    lines = core.table_script(made).splitlines()
    assert lines[0].endswith("type=83, bootable")
    assert "name=" not in lines[0]
    assert lines[1].endswith("type=83")


def test_gpt_script_still_names_partitions():
    made = core.plan(disk([], table="none"), "efi", answer("erase"), False)
    assert 'name="EFI"' in core.table_script(made)


def test_a_partition_past_the_old_table_limit_is_never_made():
    # an old table counts sectors on 32 bits: nothing may end past 2 TiB
    parts = [part(1, 2048, 100, "7", "ntfs")]
    d = disk(parts, size_gib=2200)
    for o in modes(core.options_for(d, "bios")[0], "free"):
        made = core.plan(d, "bios", answer("free", start=o["start"]), False)
        assert all(n["start"] + n["sectors"] <= 2 ** 32 for n in made["add"])
