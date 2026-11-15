# SPDX-License-Identifier: GPL-3.0-or-later
"""Carries out a plan from rayedisk_core. This is the only file that writes.

The order is what keeps someone's data:

 1. Shrink the filesystem first. A failure leaves a smaller filesystem in a
    partition of the old size, which every system reads without complaint.
    ntfsresize runs a dry pass first and is never given --force: what it
    refuses, it refuses for a reason only Windows can fix.
 2. Write the table, keeping a copy of the old one.
 3. Read the table back and compare, BEFORE anything is formatted.
 4. Format only what the plan just created.

Before each of those steps the hardware is read again: the plan was made for
one disk, and a stick pulled out and another put in takes the same /dev name.
"""
import os
import stat
import time

from rayedisk_core import Refused, check_written, table_script

# Root's alone (raye-setup-private makes it). /run/raye-setup belongs to the
# live account: a name opened there could be a link to any file root can write.
BACKUP_DIR = "/run/raye-setup-root"
SETTLE_SECONDS = 15


class CommandFailed(Exception):
    """A command said no. Never carries what was fed to it: that can be a passphrase."""

    def __init__(self, argv, code, error):
        super().__init__(f"{' '.join(argv[:2])} exited with {code}: {error.strip()[-400:]}")
        self.argv = argv


def backup_name(disk):
    return os.path.join(BACKUP_DIR, "disk-before-" + os.path.basename(disk) + ".sfdisk")


def private_folder(path):
    """A folder only root can enter, made when missing. Refuses one that isn't."""
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    except OSError as error:
        raise Refused("unsafe-folder", path) from error
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise Refused("unsafe-folder", path)
    return path


def write_private(path, text):
    """A new 0600 file: never through a link, never into one that was there."""
    private_folder(os.path.dirname(path))
    try:
        # only root can make or remove names in this folder
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as saved:
            saved.write(text)
    except OSError as error:
        raise Refused("unsafe-folder", path) from error


def ntfs_current_size(text):
    """Bytes in "Current volume size: 34359738368 bytes (34360 MB)", or None."""
    for line in text.splitlines():
        words = line.split()
        if line.startswith("Current volume size:") and len(words) > 3 and words[3].isdigit():
            return int(words[3])
    return None


def read_nodes_exist(nodes):
    return all(os.path.exists(node) for node in nodes)


class Writer:
    def __init__(self, run, read_table, note=lambda text: None, progress=lambda part: None,
                 identify=lambda disk: ""):
        # run(argv, feed=None) -> stdout, raises CommandFailed
        self.run = run
        # read_table(disk) -> {"parts": [...]} as rayedisk_probe reads them
        self.read_table = read_table
        # identify(disk) -> rayedisk_probe.hardware_of(disk); "" never matches
        self.identify = identify
        self.note = note
        self.progress = progress

    def same_disk(self, plan):
        """Stops unless the disk is still the piece of hardware the plan was made for."""
        expected = plan.get("hardware") or ""
        if not expected or self.identify(plan["disk"]) != expected:
            raise Refused("disk-changed", plan["disk"])

    def unmount(self, nodes):
        # A partition is mounted or it is swap, and either command says no to
        # the other kind. What counts is whether it is still in use afterwards.
        for node in nodes:
            self.run(["swapoff", node], tolerate=True)
            self.run(["umount", "--all-targets", node], tolerate=True)
            still = self.run(["lsblk", "--noheadings", "--output", "MOUNTPOINTS", node], tolerate=True)
            if still.strip():
                raise Refused("in-use", node)

    def shrink_filesystem(self, shrink):
        node, size = shrink["node"], str(shrink["bytes"])
        self.note(f"checking {node} before shrinking it")
        self.run(["ntfs-3g.probe", "--readwrite", node])
        self.run(["ntfsresize", "--no-progress-bar", "--no-action", "--size", size, node])
        self.note(f"shrinking the filesystem on {node} to {size} bytes")
        # it asks "Are you sure"; the dry pass above already said it can
        self.run(["ntfsresize", "--no-progress-bar", "--size", size, node], feed="y\n")
        # A shrink schedules a check for Windows' next start, so ntfsresize
        # now refuses this volume unless told to go on. --info only reads: it
        # is the one place --force goes. The partition shrinks to this size
        # next, so a filesystem still bigger than that stops everything here.
        text = self.run(["ntfsresize", "--no-progress-bar", "--info", "--force", node])
        current = ntfs_current_size(text)
        if current is None or current > shrink["bytes"]:
            raise Refused("table-mismatch", node)

    def write_table(self, plan):
        disk = plan["disk"]
        self.note(f"writing the partition table of {disk}")
        common = ["sfdisk", "--lock", "--no-reread", "--no-tell-kernel"]
        if plan["wipe"]:
            script = "label: gpt\n" + table_script(plan)
            self.run(common + ["--wipe", "always", "--wipe-partitions", "always", disk], feed=script)
            return
        if plan["shrink"]:
            shrink = plan["shrink"]
            self.run(common + ["--wipe", "never", "-N", str(shrink["number"]), disk],
                     feed="start=%d, size=%d\n" % (shrink["start"], shrink["sectors"]))
        if plan["delete"]:
            self.run(common + ["--delete", disk, str(plan["delete"]["number"])])
        self.run(common + ["--wipe", "never", "--wipe-partitions", "always", "--append", disk],
                 feed=table_script(plan))

    def tell_kernel(self, plan):
        disk = plan["disk"]
        try:
            self.run(["blockdev", "--rereadpt", disk])
        except CommandFailed:
            # a partition of this disk stays in use (installing beside
            # another system): tell the kernel one change at a time
            if plan["delete"]:
                self.run(["partx", "--delete", "--nr", str(plan["delete"]["number"]), disk], tolerate=True)
            self.run(["partx", "--update", disk])
            try:
                self.run(["partx", "--add", disk])
            except CommandFailed:
                pass
        self.run(["udevadm", "settle"])

    def wait_for(self, nodes):
        waited = 0
        while not read_nodes_exist(nodes):
            if waited >= SETTLE_SECONDS:
                raise Refused("table-mismatch", " ".join(nodes))
            time.sleep(1)
            waited += 1
            self.run(["udevadm", "settle"])

    def uuid(self, node, tag="UUID"):
        # no --probe: that mode has no PARTUUID. No cache: it would remember
        # the filesystem that was here before.
        return self.run(["blkid", "--cache-file", "/dev/null", "--output", "value",
                         "--match-tag", tag, node]).strip()

    def format_all(self, plan, nodes, passphrase):
        """Make the filesystems. Returns the partitions, as Calamares' jobs read them."""
        made = []
        if "esp" in nodes:
            self.run(["mkfs.vfat", "-F", "32", "-n", "EFI", nodes["esp"]])
            made.append(self._entry(nodes["esp"], "/boot/efi", "fat32", "EFI", True))
        elif plan["reuse_esp"]:
            made.append(self._entry(plan["reuse_esp"], "/boot/efi", "fat32", "", False))
        if "boot" in nodes:
            self.run(["mkfs.ext4", "-F", "-q", "-L", "raye_boot", nodes["boot"]])
            made.append(self._entry(nodes["boot"], "/boot", "ext4", "raye_boot", True))
        made.append(self._root(plan, nodes["root"], passphrase))
        return made

    def _root(self, plan, node, passphrase):
        if not plan["encrypt"]:
            self.run(["mkfs.btrfs", "-f", "-q", "-L", "raye", node])
            return self._entry(node, "/", "btrfs", "raye", True)
        self.run(["cryptsetup", "luksFormat", "--type", "luks2", "--batch-mode",
                  "--key-file=-", node], feed=passphrase)
        luks_uuid = self.uuid(node)
        mapper = "luks-" + luks_uuid
        self.run(["cryptsetup", "open", "--key-file=-", node, mapper], feed=passphrase)
        inner = "/dev/mapper/" + mapper
        self.run(["mkfs.btrfs", "-f", "-q", "-L", "raye", inner])
        entry = self._entry(node, "/", "btrfs", "raye", True)
        entry["uuid"] = self.uuid(inner)
        entry["luksMapperName"] = mapper
        entry["luksUuid"] = luks_uuid
        entry["luksPassphrase"] = passphrase
        return entry

    def _entry(self, node, mount, fs, label, claimed):
        return {"device": node, "partlabel": label, "partuuid": self.uuid(node, "PARTUUID"),
                "mountPoint": mount, "fsName": fs, "fs": fs, "parttype": "", "partattrs": 0,
                "features": {}, "uuid": self.uuid(node), "claimed": claimed}

    def apply(self, plan, before, passphrase):
        """Everything, in order. Returns the partition list for GlobalStorage."""
        disk = plan["disk"]
        private_folder(BACKUP_DIR)
        self.same_disk(plan)
        self.unmount(plan["unmount"])
        write_private(backup_name(disk), self.run(["sfdisk", "--dump", disk], tolerate=True))
        self.progress(0.1)
        if plan["shrink"]:
            self.same_disk(plan)
            self.shrink_filesystem(plan["shrink"])
        self.progress(0.5)
        self.same_disk(plan)
        self.write_table(plan)
        self.tell_kernel(plan)
        nodes = check_written(before, self.read_table(disk), plan)
        self.wait_for(list(nodes.values()))
        self.progress(0.7)
        self.same_disk(plan)
        made = self.format_all(plan, nodes, passphrase)
        self.progress(1.0)
        return made
