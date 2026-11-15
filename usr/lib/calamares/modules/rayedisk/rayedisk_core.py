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
   said it is fine, and never below what ntfsresize says it needs.
 - The disk Raye started from is never offered.
 - A disk that could not be read is never offered either: "could not read
   the table" is not "no table", and only the second may look empty.
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
LINUX_TYPE = "0FC63DAF-8483-4772-8E79-3D69D8477DE4"
MS_BASIC_TYPE = "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7"
# never offered for anything: they are small and belong to another system
MS_RESERVED_TYPE = "E3C9E316-0B5C-4DB8-817D-F92DF00215AE"
MS_RECOVERY_TYPE = "DE94BBA4-06D1-4D40-A16A-BFD50179D6AC"
HIDDEN_TYPES = {ESP_TYPE, MS_RESERVED_TYPE, MS_RECOVERY_TYPE}

# what raye-preflight says about a volume ntfsresize would refuse
SHRINK_BLOCKERS = {"bitlocker", "hibernated", "ntfs-dirty", "ntfs-check",
                   "ntfs-busy", "ntfs-unknown"}

MODES = ("erase", "shrink", "free", "replace")


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


def free_regions(disk):
    """The gaps between partitions, in sectors, on 1 MiB boundaries."""
    if disk["table"] != "gpt":
        return []
    align = align_of(disk)
    regions = []
    at = disk["first"]
    for part in sorted(disk["parts"], key=lambda p: p["start"]):
        start, end = align_up(at, align), align_down(part["start"], align)
        if end - start >= align:
            regions.append({"start": start, "sectors": end - start})
        at = max(at, part["start"] + part["sectors"])
    start, end = align_up(at, align), align_down(disk["last"] + 1, align)
    if end - start >= align:
        regions.append({"start": start, "sectors": end - start})
    return regions


def usable_esp(disk):
    """The EFI system partition to share on this disk: the biggest, or None."""
    found = [p for p in disk["parts"]
             if p["type"].upper() == ESP_TYPE and p["sectors"] * disk["sector"] >= ESP_MINIMUM]
    return max(found, key=lambda p: p["sectors"]) if found else None


def need_on(disk, sharing=True):
    """Bytes Raye needs from one region of this disk."""
    if sharing and usable_esp(disk) is not None:
        return RAYE_NEEDS
    return RAYE_NEEDS + ESP_SIZE


def _shared_esp(disk):
    esp = usable_esp(disk)
    return esp is not None and "shared-efi" in esp.get("findings", [])


def _room_after(disk, part):
    """Free sectors right behind a partition, up to the next one or the end."""
    end = part["start"] + part["sectors"]
    later = [p["start"] for p in disk["parts"] if p["start"] >= end]
    limit = min(later) if later else disk["last"] + 1
    return max(0, limit - end)


def _shrink_option(disk, part):
    """What the page can offer for one NTFS volume: option, or a refusal."""
    blockers = [f for f in part.get("findings", []) if f in SHRINK_BLOCKERS]
    if blockers:
        return None, {"mode": "shrink", "node": part["node"], "name": part.get("os") or part.get("label") or "",
                      "finding": blockers[0]}
    minimum = part.get("shrink_minimum")
    if not minimum:
        return None, {"mode": "shrink", "node": part["node"], "name": part.get("os") or part.get("label") or "",
                      "finding": "ntfs-unknown"}
    size = disk["sector"] * part["sectors"]
    behind = disk["sector"] * _room_after(disk, part)
    keep_min = min(size, minimum + WINDOWS_ROOM)
    # the room left has to hold Raye, on a 1 MiB boundary and whatever the
    # table's backup at the end of the disk takes
    keep_max = size + behind - need_on(disk) - 2 * MIB
    keep_max = min(keep_max, size - MIB)
    keep_max -= keep_max % MIB
    keep_min += -keep_min % MIB
    if keep_max < keep_min:
        return None, None
    half = (size + behind - keep_min) // 2
    share = max(half, need_on(disk) + 2 * MIB)
    keep_default = min(keep_max, max(keep_min, size + behind - share))
    keep_default -= keep_default % MIB
    return {"mode": "shrink", "node": part["node"], "number": part["number"],
            "name": part.get("os") or part.get("label") or "",
            "total": size + behind, "keepMin": keep_min, "keepMax": keep_max,
            "keepDefault": max(keep_min, keep_default)}, None


def options_for(disk):
    """Everything the page can offer for one disk, with what it refuses."""
    options, refused = [], []
    if disk["table"] == "gpt" and not disk.get("holders"):
        if _shared_esp(disk):
            refused.append({"mode": "beside", "reason": "shared-efi"})
        else:
            for part in sorted(disk["parts"], key=lambda p: p["start"]):
                if part.get("mounted") or part.get("fstype") != "ntfs" \
                        or part["type"].upper() in HIDDEN_TYPES:
                    continue
                option, refusal = _shrink_option(disk, part)
                if option:
                    options.append(option)
                elif refusal:
                    refused.append(refusal)
            for region in free_regions(disk):
                size = region["sectors"] * disk["sector"]
                if size >= need_on(disk):
                    options.append({"mode": "free", "start": region["start"], "bytes": size})
            for part in sorted(disk["parts"], key=lambda p: p["start"]):
                size = part["sectors"] * disk["sector"]
                if part["type"].upper() in HIDDEN_TYPES or part.get("mounted"):
                    continue
                if size >= need_on(disk):
                    options.append({"mode": "replace", "node": part["node"], "number": part["number"],
                                    "name": part.get("os") or part.get("label") or "",
                                    "fstype": part.get("fstype") or "", "bytes": size})
    elif disk["table"] not in ("gpt", "none") and disk["parts"]:
        refused.append({"mode": "beside", "reason": "old-table"})
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
            entry["options"], entry["refused"] = options_for(disk)
        entry["empty"] = not disk.get("unreadable") and not disk["parts"] and not disk.get("signature")
        shown.append(entry)
    return {"firmware": firmware, "disks": shown}


def _layout(disk, start, sectors, make_esp):
    """The new partitions, in order, inside one region."""
    align = align_of(disk)
    new, at, end = [], start, start + sectors
    def take(role, size, ptype, name):
        nonlocal at
        count = align_up(size // disk["sector"], align)
        new.append({"role": role, "start": at, "sectors": count, "type": ptype, "name": name})
        at += count
    if make_esp:
        take("esp", ESP_SIZE, ESP_TYPE, "EFI")
    take("boot", BOOT_SIZE, LINUX_TYPE, "raye_boot")
    count = align_down(end - at, align)
    if count * disk["sector"] < RAYE_MINIMUM:
        raise Refused("too-small", disk["node"])
    new.append({"role": "root", "start": at, "sectors": count, "type": LINUX_TYPE, "name": "raye"})
    return new


def _partition(disk, node):
    for part in disk["parts"]:
        if part["node"] == node:
            return part
    raise Refused("disk-changed", node)


def plan(disk, firmware, answer, encrypt_passphrase_given):
    """Turn the page's answer into the changes to make, or refuse."""
    mode = answer.get("mode")
    if mode not in MODES:
        raise Refused("no-choice")
    if firmware != "efi":
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
              "mode": mode, "encrypt": encrypt, "wipe": False,
              "shrink": None, "delete": None, "reuse_esp": None, "add": [], "unmount": []}

    if mode == "erase":
        if disk["size"] < RAYE_NEEDS + ESP_SIZE + 2 * MIB:
            raise Refused("too-small", disk["node"])
        align = align_of(disk)
        total = disk["size"] // disk["sector"]
        # the backup of the table lives in the last sectors
        end = align_down(total - align, align)
        result["wipe"] = True
        result["unmount"] = [p["node"] for p in disk["parts"] if p.get("mounted")]
        result["add"] = _layout(disk, align, end - align, True)
        return result

    if disk["table"] != "gpt":
        raise Refused("old-table", disk["node"])
    if _shared_esp(disk):
        raise Refused("shared-efi", disk["node"])
    esp = usable_esp(disk)
    make_esp = esp is None
    result["reuse_esp"] = None if make_esp else esp["node"]

    if mode == "free":
        wanted = answer.get("start")
        for region in free_regions(disk):
            if region["start"] == wanted:
                if region["sectors"] * disk["sector"] < need_on(disk):
                    raise Refused("too-small", disk["node"])
                result["add"] = _layout(disk, region["start"], region["sectors"], make_esp)
                return result
        raise Refused("disk-changed", disk["node"])

    part = _partition(disk, answer.get("partition"))
    if part["type"].upper() in HIDDEN_TYPES:
        raise Refused("not-offered", part["node"])

    if mode == "replace":
        size = part["sectors"] * disk["sector"]
        if size < need_on(disk):
            raise Refused("too-small", part["node"])
        if part.get("mounted"):
            raise Refused("in-use", part["node"])
        align = align_of(disk)
        start = align_up(part["start"], align)
        end = align_down(part["start"] + part["sectors"], align)
        result["delete"] = {"node": part["node"], "number": part["number"]}
        result["add"] = _layout(disk, start, end - start, make_esp)
        return result

    # shrink: the page only offered it inside these limits; check them again
    option, refusal = _shrink_option(disk, part) if part.get("fstype") == "ntfs" else (None, None)
    if refusal:
        raise Refused(refusal["finding"], part["node"])
    if option is None or part.get("mounted"):
        raise Refused("cannot-shrink", part["node"])
    keep = answer.get("keep")
    if not isinstance(keep, int) or keep < option["keepMin"] or keep > option["keepMax"]:
        raise Refused("keep-out-of-range", part["node"])
    align = align_of(disk)
    keep_sectors = align_down(keep // disk["sector"], align)
    result["shrink"] = {"node": part["node"], "number": part["number"],
                        "start": part["start"], "old_sectors": part["sectors"],
                        "sectors": keep_sectors, "bytes": keep_sectors * disk["sector"]}
    start = align_up(part["start"] + keep_sectors, align)
    room = _room_after(disk, part)
    end = align_down(min(part["start"] + part["sectors"] + room, disk["last"] + 1), align)
    result["add"] = _layout(disk, start, end - start, make_esp)
    return result


def table_script(result, sector_size=None):
    """The lines sfdisk reads for the partitions this plan adds."""
    lines = []
    for new in result["add"]:
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
