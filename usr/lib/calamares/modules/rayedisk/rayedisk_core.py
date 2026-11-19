# SPDX-License-Identifier: GPL-3.0-or-later
"""What Raye Setup may do to a disk, worked out without touching one.

raye-disks reads the machine and calls report() to tell the disk page what
it can offer. The rayedisk job reads the machine again and calls plan() to
turn the page's answer into a list of changes. Nothing here runs a command,
so every rule below is tested on made-up disks.

The rules that keep someone's data:

 - A plan names every partition it changes. Everything else on the disk
   has to read back the same after the write (check_written).
 - The disk has to look the way it did when the page was drawn: the
   answer carries the table's fingerprint, and a different one is a refusal.
 - A Windows volume is only shrunk when ntfs-3g.probe and ntfsresize both
   said it is fine, and never below what ntfsresize says it needs. A Linux
   volume (ext2/3/4, btrfs) only when it was shut down cleanly, and never
   below what resize2fs or btrfs say it uses. XFS cannot shrink at all.
 - The disk Raye started from is never offered.
 - A disk that could not be read is never offered either: "could not read
   the table" is not "no table", and only the second may look empty.
 - "Replace and keep my files" never needs anything deleted before it is
   copied: the room for two copies of the files is there, or the choice is
   refused with how much it would take.
"""

MIB = 1024 ** 2
GIB = 1024 ** 3

# what welcomeq asks of the disk (requiredStorage)
RAYE_MINIMUM = 25 * GIB
ESP_SIZE = 1 * GIB
# Windows creates its own at "100 MB", 95.37 MiB read as decimal
ESP_MINIMUM = 64 * MIB
# /boot is ext4 even without encryption: GRUB cannot write its recordfail
# flag on btrfs, and Ubuntu's 00_header then shows the menu at every start
BOOT_SIZE = 2 * GIB
# Room Windows keeps on top of what it already uses, to run and to update.
WINDOWS_ROOM = 10 * GIB
# Asked for when a region is judged, whether the disk ends up encrypted or
# not: the page never has to change its answer when the box is ticked.
RAYE_NEEDS = RAYE_MINIMUM + BOOT_SIZE

ESP_TYPE = "C12A7328-F81F-11D2-BA4B-00A0C93EC93B"
# where GRUB puts itself on a GPT disk started in BIOS mode
BIOS_BOOT_TYPE = "21686148-6449-6E6F-744E-656564454649"
LINUX_TYPE = "0FC63DAF-8483-4772-8E79-3D69D8477DE4"
MS_BASIC_TYPE = "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7"
# never offered for anything: they are small and belong to another system
MS_RESERVED_TYPE = "E3C9E316-0B5C-4DB8-817D-F92DF00215AE"
MS_RECOVERY_TYPE = "DE94BBA4-06D1-4D40-A16A-BFD50179D6AC"
# the same on an old-style table: EFI, Windows' hidden recovery
HIDDEN_TYPES = {ESP_TYPE, MS_RESERVED_TYPE, MS_RECOVERY_TYPE, BIOS_BOOT_TYPE, "EF", "27"}

# An old-style (MBR) table: four partitions at most, sectors counted on 32
# bits. With an extended partition the numbering of what Raye appends is
# not worth guessing: only erasing is offered.
DOS_SLOTS = 4
DOS_LIMIT = 2 ** 32
DOS_EXTENDED = {"5", "F", "85"}
DOS_LINUX = "83"

LINUX_FS = {"ext2", "ext3", "ext4", "btrfs"}
RESIZABLE = LINUX_FS | {"ntfs"}
# room another Linux keeps on top of what it uses
LINUX_ROOM = 10 * GIB
# volumes Raye never makes smaller, and the finding that says why
NEVER_SHRUNK = {"xfs": "xfs", "crypto_LUKS": "encrypted", "LVM2_member": "lvm"}

# what raye-preflight says about a volume ntfsresize would refuse
SHRINK_BLOCKERS = {"bitlocker", "hibernated", "ntfs-dirty", "ntfs-check",
                   "ntfs-busy", "ntfs-unknown",
                   # another Linux: not shut down cleanly, spread over
                   # several disks, or hibernated (its swap holds the image)
                   "linux-check", "btrfs-multi", "linux-hibernated", "linux-unknown"}
FIRMWARES = ("efi", "bios")

MODES = ("erase", "shrink", "free", "replace", "keep")

# Left in the old volume on top of its minimum while its files are copied
# out of it: it never starts again, it only has to shrink safely.
KEEP_MARGIN = 2 * GIB
# what a separate /home of the other Linux can stay as, mounted by Raye
HOME_FS = {"ext2", "ext3", "ext4", "xfs", "btrfs"}


class Refused(Exception):
    """The answer cannot be carried out. code names the reason in strings.js."""

    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def align_up(sector, align):
    return ((sector + align - 1) // align) * align


def align_down(sector, align):
    return (sector // align) * align


def align_of(disk):
    return MIB // disk["sector"]


def disk_end(disk):
    """The first sector past what a new partition may use."""
    end = disk["last"] + 1
    return min(end, DOS_LIMIT) if disk["table"] == "dos" else end


def free_regions(disk):
    """The gaps between partitions, in sectors, on 1 MiB boundaries."""
    if disk["table"] not in ("gpt", "dos"):
        return []
    align = align_of(disk)
    regions = []
    at = disk["first"]
    for part in sorted(disk["parts"], key=lambda p: p["start"]):
        start, end = align_up(at, align), align_down(min(part["start"], disk_end(disk)), align)
        if end - start >= align:
            regions.append({"start": start, "sectors": end - start})
        at = max(at, part["start"] + part["sectors"])
    start, end = align_up(at, align), align_down(disk_end(disk), align)
    if end - start >= align:
        regions.append({"start": start, "sectors": end - start})
    return regions


def usable_esp(disk):
    """The EFI system partition to share on this disk: the biggest, or None."""
    found = [p for p in disk["parts"]
             if p["type"].upper() == ESP_TYPE and p["sectors"] * disk["sector"] >= ESP_MINIMUM]
    return max(found, key=lambda p: p["sectors"]) if found else None


def esp_to_share(disk):
    """The EFI partition Raye shares, or None when it makes its own.

    One where another system of Raye's family keeps EFI/ubuntu is never
    shared: Raye would write over how that system starts. Raye gets an EFI
    partition of its own in the new room instead.
    """
    esp = usable_esp(disk)
    if esp is None or "shared-efi" in esp.get("findings", []):
        return None
    return esp


def has_bios_boot(disk):
    return any(p["type"].upper() == BIOS_BOOT_TYPE for p in disk["parts"])


def extra_for(disk, firmware, label=None):
    """The small partition the new room starts with: "esp", "biosboot" or None."""
    label = label or disk["table"]
    if firmware == "efi":
        return None if esp_to_share(disk) else "esp"
    if label == "gpt" and not has_bios_boot(disk):
        return "biosboot"
    return None


def need_on(disk, firmware="efi"):
    """Bytes Raye needs from one region of this disk."""
    extra = extra_for(disk, firmware)
    return RAYE_NEEDS + {"esp": ESP_SIZE, "biosboot": MIB, None: 0}[extra]


def dos_slots(disk):
    """Primary partitions still free on an old-style table, 0 with an extended one."""
    if any(p["type"].upper() in DOS_EXTENDED for p in disk["parts"]):
        return 0
    return max(0, DOS_SLOTS - len(disk["parts"]))


def _room_after(disk, part):
    """Free sectors right behind a partition, up to the next one or the end."""
    end = part["start"] + part["sectors"]
    later = [p["start"] for p in disk["parts"] if p["start"] >= end]
    limit = min(later) if later else disk_end(disk)
    return max(0, limit - end)


def _name(part):
    return part.get("os") or part.get("label") or ""


def _linux_hibernated(disk):
    return any("linux-hibernated" in p.get("findings", []) for p in disk["parts"])


def _shrink_option(disk, part, firmware="efi"):
    """What the page can offer for one volume: option, or a refusal."""
    fstype = part.get("fstype")
    blockers = [f for f in part.get("findings", []) if f in SHRINK_BLOCKERS]
    if fstype in LINUX_FS and _linux_hibernated(disk):
        blockers.insert(0, "linux-hibernated")
    if blockers:
        return None, {"mode": "shrink", "node": part["node"], "name": _name(part), "finding": blockers[0]}
    minimum = part.get("shrink_minimum")
    if not minimum:
        return None, {"mode": "shrink", "node": part["node"], "name": _name(part),
                      "finding": "ntfs-unknown" if fstype == "ntfs" else "linux-unknown"}
    need = need_on(disk, firmware)
    size = disk["sector"] * part["sectors"]
    behind = disk["sector"] * _room_after(disk, part)
    room = WINDOWS_ROOM if fstype == "ntfs" else LINUX_ROOM
    keep_min = min(size, minimum + room)
    # the room left has to hold Raye, on a 1 MiB boundary and whatever the
    # table's backup at the end of the disk takes
    keep_max = size + behind - need - 2 * MIB
    keep_max = min(keep_max, size - MIB)
    keep_max -= keep_max % MIB
    keep_min += -keep_min % MIB
    if keep_max < keep_min:
        return None, None
    half = (size + behind - keep_min) // 2
    share = max(half, need + 2 * MIB)
    keep_default = min(keep_max, max(keep_min, size + behind - share))
    keep_default -= keep_default % MIB
    return {"mode": "shrink", "node": part["node"], "number": part["number"],
            "name": _name(part), "fstype": fstype,
            "total": size + behind, "keepMin": keep_min, "keepMax": keep_max,
            "keepDefault": max(keep_min, keep_default)}, None


def _up_mib(value):
    return value + (-value % MIB)


def staged_bytes(files, size):
    """Room the copied folders take on a new ext4: its tables, a block per file."""
    return _up_mib(size + size // 32 + files * 4096 + GIB)


def home_bytes(files, size):
    """Room the folders take in Raye's own volume."""
    return _up_mib(size + size // 50 + files * 4096)


def _keep_summary(keep):
    """What the page lists: whose folders, and how big."""
    return [{"name": u["name"], "folders": [{"kind": f["kind"], "files": f["files"], "bytes": f["bytes"]}
                                            for f in u["folders"]]}
            for u in keep["users"]]


def _home_partition(disks, node):
    for disk in disks or []:
        for part in disk.get("parts", []):
            if part["node"] == node:
                return disk, part
    return None, None


def _keep_option(disk, part, firmware="efi", disks=None):
    """"Replace this system and keep my files": the option, or a refusal."""
    keep = part.get("keep")
    if not keep or not keep.get("users"):
        return None, None
    files = sum(f["files"] for u in keep["users"] for f in u["folders"])
    size_files = sum(f["bytes"] for u in keep["users"] for f in u["folders"])
    unreadable = sum(f.get("unreadable", 0) for u in keep["users"] for f in u["folders"])
    base = {"mode": "keep", "node": part["node"], "number": part["number"],
            "name": keep.get("name") or _name(part), "fstype": part.get("fstype") or "",
            "users": _keep_summary(keep), "files": files, "size": size_files}
    if unreadable:
        return None, {"mode": "keep", "node": part["node"], "name": base["name"], "reason": "unreadable"}
    size = part["sectors"] * disk["sector"]
    need = need_on(disk, firmware)
    home = keep.get("home")
    if home:
        # the files are on a partition of their own, which stays as it is
        _, other = _home_partition(disks or [disk], home)
        if other is None or other.get("mounted") or other.get("findings") \
                or other.get("fstype") not in HOME_FS or keep.get("base"):
            return None, None
        if size < need:
            return None, None
        return dict(base, way="home", bytes=size, home=home, homeFs=other["fstype"]), None
    fstype = part.get("fstype")
    if fstype not in RESIZABLE or part.get("mounted"):
        return None, None
    blockers = [f for f in part.get("findings", []) if f in SHRINK_BLOCKERS]
    if blockers or (fstype in LINUX_FS and _linux_hibernated(disk)) or not part.get("shrink_minimum"):
        # the card of "install next to" already says why
        return None, None
    behind = disk["sector"] * _room_after(disk, part)
    total = size + behind
    old_keep = min(size, _up_mib(part["shrink_minimum"] + KEEP_MARGIN))
    region = _up_mib(max(old_keep, need + home_bytes(files, size_files)))
    needed = region + staged_bytes(files, size_files) + 2 * MIB
    if total < needed:
        return None, {"mode": "keep", "node": part["node"], "name": base["name"], "reason": "room",
                      "needed": needed, "have": total}
    return dict(base, way="stage", bytes=total, shrinkTo=old_keep, region=region), None


def _beside_table(disk, firmware):
    """Whether Raye can go next to what is on this disk's table, and the reason when not."""
    if disk["table"] == "gpt":
        return True, ""
    if disk["table"] == "dos" and firmware == "bios":
        return True, ""
    return False, "old-table"


def options_for(disk, firmware="efi", disks=None):
    """Everything the page can offer for one disk, with what it refuses."""
    options, refused = [], []
    beside, reason = _beside_table(disk, firmware)
    if beside and not disk.get("holders"):
        dos = disk["table"] == "dos"
        slots = dos_slots(disk) if dos else DOS_SLOTS
        need = need_on(disk, firmware)
        # Raye adds two partitions; a replace frees one of its own
        two_fit = slots >= 2
        if dos and not two_fit:
            refused.append({"mode": "beside", "reason": "full-table"})
        for part in sorted(disk["parts"], key=lambda p: p["start"]):
            fstype = part.get("fstype")
            if part.get("mounted") or part["type"].upper() in HIDDEN_TYPES or not two_fit:
                continue
            size = part["sectors"] * disk["sector"]
            if fstype in NEVER_SHRUNK:
                # only worth a word when it is big enough to have mattered
                if size >= need + LINUX_ROOM:
                    refused.append({"mode": "shrink", "node": part["node"], "name": _name(part),
                                    "finding": NEVER_SHRUNK[fstype]})
                continue
            if fstype not in RESIZABLE:
                continue
            option, refusal = _shrink_option(disk, part, firmware)
            if option:
                options.append(option)
            elif refusal:
                refused.append(refusal)
        if two_fit:
            for region in free_regions(disk):
                size = region["sectors"] * disk["sector"]
                if size >= need:
                    options.append({"mode": "free", "start": region["start"], "bytes": size})
        # keeping the files comes before plain replacing: it loses less.
        # Staging adds a partition before Raye's two are made
        if not dos or slots >= 2:
            for part in sorted(disk["parts"], key=lambda p: p["start"]):
                if part["type"].upper() in HIDDEN_TYPES:
                    continue
                option, refusal = _keep_option(disk, part, firmware, disks)
                if option:
                    options.append(option)
                elif refusal:
                    refused.append(refusal)
        # dos_slots is 0 with an extended partition, so this keeps out of it too
        if not dos or slots + 1 >= 2:
            for part in sorted(disk["parts"], key=lambda p: p["start"]):
                size = part["sectors"] * disk["sector"]
                if part["type"].upper() in HIDDEN_TYPES or part.get("mounted"):
                    continue
                if size >= need:
                    options.append({"mode": "replace", "node": part["node"], "number": part["number"],
                                    "name": _name(part), "fstype": part.get("fstype") or "", "bytes": size})
    elif not beside and disk["table"] not in ("gpt", "none") and disk["parts"]:
        refused.append({"mode": "beside", "reason": reason})
    if not disk.get("holders") and disk["size"] >= RAYE_NEEDS + ESP_SIZE + 2 * MIB:
        options.append({"mode": "erase"})
    return options, refused


def report(firmware, disks):
    """What raye-disks hands to the page."""
    shown = []
    for disk in disks:
        entry = dict(disk)
        entry["options"], entry["refused"] = [], []
        if disk.get("live"):
            entry["blocked"] = "live"
        elif disk.get("unreadable"):
            entry["blocked"] = "unreadable"
        elif disk.get("holders"):
            entry["blocked"] = "in-use"
        elif disk["size"] < RAYE_NEEDS + ESP_SIZE + 2 * MIB:
            entry["blocked"] = "small"
        else:
            entry["blocked"] = ""
            entry["options"], entry["refused"] = options_for(disk, firmware, disks)
        entry["empty"] = not disk.get("unreadable") and not disk["parts"] and not disk.get("signature")
        shown.append(entry)
    return {"firmware": firmware, "disks": shown}


def _layout(disk, start, sectors, extra=None, label="gpt", active=True):
    """The new partitions, in order, inside one region."""
    align = align_of(disk)
    end = start + sectors
    if label == "dos":
        end = min(end, DOS_LIMIT)
    new, at = [], start

    def take(role, size, ptype, name, bootable=False):
        nonlocal at
        count = align_up(size // disk["sector"], align)
        new.append({"role": role, "start": at, "sectors": count, "type": ptype, "name": name,
                    "bootable": bootable})
        at += count
    linux = DOS_LINUX if label == "dos" else LINUX_TYPE
    if extra == "esp":
        take("esp", ESP_SIZE, ESP_TYPE, "EFI")
    elif extra == "biosboot":
        take("biosboot", MIB, BIOS_BOOT_TYPE, "BIOS boot")
    # some old BIOS only start a disk whose table marks a partition active
    take("boot", BOOT_SIZE, linux, "raye_boot", bootable=label == "dos" and active)
    count = align_down(end - at, align)
    if count * disk["sector"] < RAYE_MINIMUM:
        raise Refused("too-small", disk["node"])
    new.append({"role": "root", "start": at, "sectors": count, "type": linux, "name": "raye",
                "bootable": False})
    return new


def _partition(disk, node):
    for part in disk["parts"]:
        if part["node"] == node:
            return part
    raise Refused("disk-changed", node)


def plan(disk, firmware, answer, encrypt_passphrase_given, disks=None):
    """Turn the page's answer into the changes to make, or refuse."""
    mode = answer.get("mode")
    if mode not in MODES:
        raise Refused("no-choice")
    if firmware not in FIRMWARES:
        raise Refused("no-efi")
    if disk.get("live"):
        raise Refused("live", disk["node"])
    if disk.get("unreadable"):
        raise Refused("unreadable", disk["node"])
    if disk.get("holders"):
        raise Refused("in-use", disk["node"])
    if answer.get("disk") != disk["node"] or answer.get("id") != disk.get("id"):
        raise Refused("disk-changed", disk["node"])
    encrypt = bool(answer.get("encrypt"))
    if encrypt and not encrypt_passphrase_given:
        raise Refused("no-passphrase")

    # the writer checks the hardware is still this one before every write
    result = {"disk": disk["node"], "hardware": disk.get("hardware") or "",
              "mode": mode, "encrypt": encrypt, "wipe": False, "firmware": firmware, "label": "gpt",
              "shrink": None, "delete": None, "reuse_esp": None, "add": [], "unmount": [],
              "stage": None, "keep": None}

    if mode == "erase":
        if disk["size"] < RAYE_NEEDS + ESP_SIZE + 2 * MIB:
            raise Refused("too-small", disk["node"])
        align = align_of(disk)
        total = disk["size"] // disk["sector"]
        # an old BIOS starts an old-style table best, as long as it can count the disk
        label = "dos" if firmware == "bios" and total <= DOS_LIMIT else "gpt"
        extra = "esp" if firmware == "efi" else ("biosboot" if label == "gpt" else None)
        # the backup of a GPT table lives in the last sectors
        end = align_down(total - align, align)
        result["wipe"] = True
        result["label"] = label
        result["unmount"] = [p["node"] for p in disk["parts"] if p.get("mounted")]
        result["add"] = _layout(disk, align, end - align, extra, label)
        return result

    beside, reason = _beside_table(disk, firmware)
    if not beside:
        raise Refused(reason, disk["node"])
    dos = disk["table"] == "dos"
    slots = dos_slots(disk) if dos else DOS_SLOTS
    if dos and any(p["type"].upper() in DOS_EXTENDED for p in disk["parts"]):
        raise Refused("full-table", disk["node"])
    if dos and slots + (1 if mode == "replace" else 0) < 2:
        raise Refused("full-table", disk["node"])
    label = disk["table"]
    result["label"] = label
    extra = extra_for(disk, firmware)
    if firmware == "efi" and extra is None:
        result["reuse_esp"] = esp_to_share(disk)["node"]

    if mode == "free":
        wanted = answer.get("start")
        for region in free_regions(disk):
            if region["start"] == wanted:
                if region["sectors"] * disk["sector"] < need_on(disk, firmware):
                    raise Refused("too-small", disk["node"])
                result["add"] = _layout(disk, region["start"], region["sectors"], extra, label, False)
                return result
        raise Refused("disk-changed", disk["node"])

    part = _partition(disk, answer.get("partition"))
    if part["type"].upper() in HIDDEN_TYPES:
        raise Refused("not-offered", part["node"])

    if mode == "keep":
        return _plan_keep(disk, firmware, part, extra, label, result, disks)

    if mode == "replace":
        size = part["sectors"] * disk["sector"]
        if size < need_on(disk, firmware):
            raise Refused("too-small", part["node"])
        if part.get("mounted"):
            raise Refused("in-use", part["node"])
        align = align_of(disk)
        start = align_up(part["start"], align)
        end = align_down(min(part["start"] + part["sectors"], disk_end(disk)), align)
        result["delete"] = {"node": part["node"], "number": part["number"]}
        result["add"] = _layout(disk, start, end - start, extra, label, False)
        return result

    # shrink: the page only offered it inside these limits; check them again
    fstype = part.get("fstype")
    if fstype in NEVER_SHRUNK:
        raise Refused(NEVER_SHRUNK[fstype], part["node"])
    option, refusal = _shrink_option(disk, part, firmware) if fstype in RESIZABLE else (None, None)
    if refusal:
        raise Refused(refusal["finding"], part["node"])
    if option is None or part.get("mounted"):
        raise Refused("cannot-shrink", part["node"])
    keep = answer.get("keep")
    if not isinstance(keep, int) or keep < option["keepMin"] or keep > option["keepMax"]:
        raise Refused("keep-out-of-range", part["node"])
    align = align_of(disk)
    keep_sectors = align_down(keep // disk["sector"], align)
    result["shrink"] = {"node": part["node"], "number": part["number"], "fstype": fstype,
                        "devid": part.get("btrfs_devid") or 1,
                        "start": part["start"], "old_sectors": part["sectors"],
                        "sectors": keep_sectors, "bytes": keep_sectors * disk["sector"]}
    start = align_up(part["start"] + keep_sectors, align)
    room = _room_after(disk, part)
    end = align_down(min(part["start"] + part["sectors"] + room, disk_end(disk)), align)
    # next to another system the table keeps the active partition it has:
    # Windows' boot code refuses one with two
    result["add"] = _layout(disk, start, end - start, extra, label, False)
    return result


def _plan_keep(disk, firmware, part, extra, label, result, disks):
    """Replace a system and keep its folders: see rayedisk_keep."""
    if disk["table"] == "dos" and dos_slots(disk) < 2:
        raise Refused("full-table", disk["node"])
    option, refusal = _keep_option(disk, part, firmware, disks)
    if refusal:
        raise Refused("keep-" + refusal["reason"], part["node"])
    if option is None:
        raise Refused("cannot-keep", part["node"])
    keep = part["keep"]
    align = align_of(disk)
    start = align_up(part["start"], align)
    result["delete"] = {"node": part["node"], "number": part["number"]}
    result["keep"] = {"way": option["way"], "source": part["node"], "fstype": part.get("fstype") or "",
                      "system": keep.get("system", "linux"), "name": option["name"],
                      "base": keep.get("base", ""), "home": keep.get("home") or "",
                      "homeFs": option.get("homeFs", ""), "users": keep["users"],
                      "files": option["files"], "bytes": option["size"]}
    if option["way"] == "home":
        end = align_down(min(part["start"] + part["sectors"], disk_end(disk)), align)
        result["add"] = _layout(disk, start, end - start, extra, label, False)
        return result
    keep_sectors = align_down(option["shrinkTo"] // disk["sector"], align)
    if keep_sectors < part["sectors"]:
        result["shrink"] = {"node": part["node"], "number": part["number"], "fstype": part.get("fstype"),
                            "devid": part.get("btrfs_devid") or 1,
                            "start": part["start"], "old_sectors": part["sectors"],
                            "sectors": keep_sectors, "bytes": keep_sectors * disk["sector"]}
    region = align_up(option["region"] // disk["sector"], align)
    stage_start = start + region
    end = align_down(min(part["start"] + part["sectors"] + _room_after(disk, part), disk_end(disk)), align)
    if (end - stage_start) * disk["sector"] < staged_bytes(option["files"], option["size"]):
        raise Refused("keep-room", part["node"])
    stage_type = DOS_LINUX if label == "dos" else LINUX_TYPE
    result["stage"] = {"role": "stage", "start": stage_start, "sectors": end - stage_start,
                       "type": stage_type, "name": "raye_files", "bootable": False}
    result["add"] = _layout(disk, start, region, extra, label, False)
    return result


def keep_steps(result):
    """The two table changes of a staged keep, as plans check_written reads.

    First the old volume shrinks and the staging partition is added; then the
    old volume goes and Raye's partitions are added in front of the copies.
    """
    first = dict(result, delete=None, add=[result["stage"]])
    second = dict(result, shrink=None, add=result["add"])
    return first, second


def table_script(result, sector_size=None):
    """The lines sfdisk reads for the partitions this plan adds."""
    lines = []
    for new in result["add"]:
        if result.get("label") == "dos":
            line = "start=%d, size=%d, type=%s" % (new["start"], new["sectors"], new["type"])
            lines.append(line + (", bootable" if new.get("bootable") else ""))
        else:
            lines.append('start=%d, size=%d, type=%s, name="%s"'
                         % (new["start"], new["sectors"], new["type"], new["name"]))
    return "\n".join(lines) + "\n"


def check_written(before, after, result):
    """Every partition the plan does not name must read back the same.

    Runs between writing the table and formatting anything, so a surprise
    stops the install while the new partitions are still empty.
    """
    deleted = result["delete"]["node"] if result["delete"] else None
    shrunk = result["shrink"]
    now = {(p["start"]): p for p in after["parts"]}
    for part in before["parts"]:
        if result["wipe"] or part["node"] == deleted:
            continue
        seen = now.get(part["start"])
        if seen is None:
            raise Refused("table-mismatch", part["node"])
        if seen["type"].upper() != part["type"].upper() or seen["node"] != part["node"]:
            raise Refused("table-mismatch", part["node"])
        if shrunk and part["node"] == shrunk["node"]:
            if seen["sectors"] != shrunk["sectors"]:
                raise Refused("table-mismatch", part["node"])
        elif seen["sectors"] != part["sectors"]:
            raise Refused("table-mismatch", part["node"])
    new = {}
    for wanted in result["add"]:
        seen = now.get(wanted["start"])
        if seen is None or seen["sectors"] != wanted["sectors"]:
            raise Refused("table-mismatch", wanted["role"])
        new[wanted["role"]] = seen["node"]
    return new


def bytes_of_ntfsresize(text):
    """The smallest size ntfsresize says a volume can have, or None.

    ntfsresize --info prints "You might resize at 8589934592 bytes or ...".
    """
    for line in text.splitlines():
        words = line.split()
        if line.startswith("You might resize at") and len(words) > 4 and words[4].isdigit():
            return int(words[4])
    return None


def _fields(text):
    """"key: value" lines, as a dict."""
    found = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            found[key.strip()] = value.strip()
    return found


def ext_info(text):
    """What dumpe2fs -h says of an ext2/3/4 volume: clean, size in bytes, block size."""
    fields = _fields(text)
    count, block = fields.get("Block count", ""), fields.get("Block size", "")
    if not count.isdigit() or not block.isdigit():
        return None
    clean = fields.get("Filesystem state") == "clean" \
        and "needs_recovery" not in fields.get("Filesystem features", "").split()
    return {"clean": clean, "bytes": int(count) * int(block), "block": int(block)}


def ext_minimum(text, block):
    """The smallest size resize2fs -P says a volume can have, or None."""
    for line in text.splitlines():
        if line.startswith("Estimated minimum size of the filesystem:"):
            value = line.rsplit(":", 1)[1].strip()
            if value.isdigit():
                return int(value) * block
    return None


def btrfs_info(text):
    """What btrfs inspect-internal dump-super says of one device of a volume."""
    fields = {}
    for line in text.splitlines():
        words = line.split()
        if len(words) >= 2:
            fields[words[0]] = words[1]
    keys = ("num_devices", "dev_item.total_bytes", "dev_item.bytes_used", "dev_item.devid", "log_root")
    if not all(fields.get(k, "").isdigit() for k in keys):
        return None
    return {"devices": int(fields["num_devices"]), "bytes": int(fields["dev_item.total_bytes"]),
            "used": int(fields["dev_item.bytes_used"]), "devid": int(fields["dev_item.devid"]),
            "log": fields["log_root"] != "0"}
