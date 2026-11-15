# SPDX-License-Identifier: GPL-3.0-or-later
"""Reads the disks into the shape rayedisk_core works on. Read only.

Used twice: by raye-disks for the page, and by the job right before it
writes, so the plan is made against the disk as it is now.
"""
import hashlib
import json
import os
import re
import subprocess

from rayedisk_core import ESP_TYPE, bytes_of_ntfsresize

LIVE_MOUNTS = {"/cdrom", "/run/live/medium", "/isodevice"}
# lsblk calls these "disk" too; zram is the live session's own memory
NOT_DISKS = ("/dev/zram", "/dev/ram", "/dev/loop")


def run_text(argv, timeout=60):
    """(exit code, stdout) of a command that only reads."""
    try:
        done = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              stdin=subprocess.DEVNULL, timeout=timeout, text=True, errors="replace")
        return done.returncode, done.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def number_of(node):
    found = re.search(r"(\d+)$", node)
    return int(found.group(1)) if found else 0


def table_of(node, run=run_text):
    """sfdisk's view of a disk's table, None when sfdisk gave none.

    None is both "no table" and "could not read it": read_disk tells them apart.
    """
    code, text = run(["sfdisk", "--json", node])
    if code != 0 or not text.strip():
        return None
    try:
        return json.loads(text).get("partitiontable") or None
    except (ValueError, AttributeError):
        return None


def signatures_of(node, run=run_text):
    """What wipefs finds on the disk itself, [] for nothing, None when it could not look."""
    code, text = run(["wipefs", "--no-act", "--json", node])
    if code != 0:
        return None
    if not text.strip():
        return []
    try:
        return [str(s.get("type") or "") for s in json.loads(text).get("signatures", [])]
    except (ValueError, AttributeError):
        return None


# What says which disk this is. Nothing the install itself changes (the
# table's id, a filesystem's UUID): this is checked again between writes.
HARDWARE_KEYS = ("ID_SERIAL", "ID_SERIAL_SHORT", "ID_WWN_WITH_EXTENSION", "ID_WWN", "ID_PATH", "ID_MODEL")


def hardware_of(node, run=run_text):
    """Serial, WWN, where it is plugged in and its size, "" when that can't be read."""
    code, text = run(["udevadm", "info", "--query=property", "--name=" + node])
    if code != 0 or not text.strip():
        return ""
    props = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            props[key.strip()] = value.strip()
    code, size = run(["blockdev", "--getsize64", node])
    if code != 0 or not size.strip().isdigit():
        return ""
    return ";".join([f"{key}={props.get(key, '')}" for key in HARDWARE_KEYS] + ["size=" + size.strip()])


def fingerprint(node, size, signature, run=run_text, hardware="", uuid=""):
    """The disk as the page saw it: which hardware, and what is on it."""
    code, text = run(["sfdisk", "--dump", node])
    if code != 0:
        text = f"none {size} {signature or ''} {uuid or ''}"
    return hashlib.sha256((hardware + "\n" + text).encode()).hexdigest()


def preflight_findings(run=run_text):
    """raye-preflight's lines, {device: [findings]}, None when it did not run."""
    code, text = run(["/usr/libexec/raye-preflight"], timeout=120)
    if code != 0:
        return None
    found = {}
    for line in text.splitlines():
        words = line.split()
        if len(words) == 2:
            found.setdefault(words[1], []).append(words[0])
    return found


def os_names(run=run_text):
    """What os-prober recognises, {device: name}. Slow, the page only."""
    code, text = run(["os-prober"], timeout=120)
    names = {}
    for line in text.splitlines():
        fields = line.split(":")
        if len(fields) >= 3:
            names[fields[0].split("@")[0]] = fields[1]
    return names


def ntfs_minimum(node, run=run_text):
    """What ntfsresize says this volume could shrink to, None when it refuses."""
    code, text = run(["ntfsresize", "--info", "--no-progress-bar", node], timeout=300)
    return bytes_of_ntfsresize(text) if code == 0 else None


def is_windows(node, run=run_text):
    code, _ = run(["ntfsls", "--force", "--path", "/Windows/System32", node])
    return code == 0


def _mounts(device):
    return [m for m in device.get("mountpoints") or [] if m]


def _below(device):
    """Everything lsblk shows under a device, at any depth."""
    for child in device.get("children") or []:
        yield child
        yield from _below(child)


def _unknown_findings(entry, fstype):
    """What raye-preflight would have had to rule out, when it never ran."""
    if str(entry.get("type", "")).upper() == ESP_TYPE:
        return ["shared-efi"]
    if fstype == "ntfs":
        return ["ntfs-unknown"]
    return []


def read_disk(blk, findings, names, run=run_text, look=True):
    """One disk from lsblk's tree and sfdisk's table.

    What is mounted on the disk and what holds it come from lsblk's whole tree,
    never only from the partitions sfdisk listed: a table sfdisk cannot read
    must not hide the stick Raye started from, or a volume that is open.
    """
    node = blk["path"]
    children = blk.get("children") or []
    below = list(_below(blk))
    holders = sorted({c["type"] for c in below if c.get("type") != "part"})
    live = any(set(_mounts(d)) & LIVE_MOUNTS for d in [blk] + below)
    hardware = hardware_of(node, run)

    table = table_of(node, run)
    unreadable = not hardware
    if table is None:
        # No table, or one sfdisk can't read. Only what wipefs read without
        # error and found nothing but the disk's own filesystem is "none".
        found = signatures_of(node, run)
        own = {blk.get("fstype") or ""}
        if found is None or set(found) - own or any(c.get("type") == "part" for c in children):
            unreadable = True
        table = {}
    listed = {entry["node"] for entry in table.get("partitions", [])}
    if any(c.get("type") == "part" and c["path"] not in listed for c in children):
        # the kernel knows a partition the table doesn't: a mount on it
        # would go unseen
        unreadable = True

    parts_by_node = {c["path"]: c for c in children if c.get("type") == "part"}
    parts = []
    for entry in table.get("partitions", []):
        info = parts_by_node.get(entry["node"], {})
        mounts = _mounts(info)
        found = (findings.get(entry["node"], []) if findings is not None
                 else _unknown_findings(entry, info.get("fstype")))
        part = {"node": entry["node"], "number": number_of(entry["node"]),
                "start": int(entry["start"]), "sectors": int(entry["size"]),
                "type": str(entry.get("type", "")), "name": entry.get("name") or "",
                "fstype": info.get("fstype") or "", "label": info.get("label") or "",
                "mounted": bool(mounts), "findings": found}
        if look:
            if part["fstype"] == "ntfs" and not part["findings"]:
                part["shrink_minimum"] = ntfs_minimum(entry["node"], run)
                if part["shrink_minimum"] and is_windows(entry["node"], run):
                    part["os"] = "Windows"
            if entry["node"] in names and "os" not in part:
                part["os"] = names[entry["node"]]
        elif part["fstype"] == "ntfs" and not part["findings"]:
            part["shrink_minimum"] = ntfs_minimum(entry["node"], run)
        parts.append(part)
    sector = int(table.get("sectorsize") or blk.get("log-sec") or 512)
    size = int(blk.get("size") or 0)
    label = table.get("label", "") or "none"
    return {"node": node, "model": (blk.get("model") or "").strip(), "size": size, "sector": sector,
            "removable": bool(blk.get("rm")), "tran": blk.get("tran") or "",
            "table": label if label in ("gpt", "dos") else "none" if label == "none" else label,
            "first": int(table.get("firstlba") or 2048),
            "last": int(table.get("lastlba") or (size // sector - 34)),
            "parts": parts, "holders": holders, "live": live, "unreadable": unreadable,
            "signature": blk.get("fstype") or "", "hardware": hardware,
            "id": fingerprint(node, size, blk.get("fstype"), run, hardware, blk.get("uuid") or "")}


def read_machine(run=run_text, look=True):
    """(firmware, [disks]). look=False skips the slow os-prober."""
    # --tree: with an --output list and no NAME, lsblk's JSON comes out flat
    code, text = run(["lsblk", "--json", "--tree=PATH", "--bytes", "--paths", "--output",
                      "PATH,TYPE,SIZE,MODEL,RM,TRAN,FSTYPE,LABEL,UUID,MOUNTPOINTS,LOG-SEC"])
    tree = json.loads(text).get("blockdevices", []) if code == 0 and text.strip() else []
    findings = preflight_findings(run)
    names = os_names(run) if look else {}
    disks = [read_disk(blk, findings, names, run, look) for blk in tree
             if blk.get("type") == "disk" and int(blk.get("size") or 0) > 0
             and not blk["path"].startswith(NOT_DISKS)]
    firmware = "efi" if os.path.isdir("/sys/firmware/efi") else "bios"
    return firmware, disks
