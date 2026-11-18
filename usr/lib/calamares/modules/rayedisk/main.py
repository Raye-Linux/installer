#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Gets the disk ready the way the person chose on Raye's disk page: erased,
# Windows made smaller, free space used, or one partition replaced. Always
# btrfs. Leaves in GlobalStorage what the jobs after it read.
#
# The page leaves its answer in /run/raye-setup/answer-disk, and the disk
# password in /run/raye-setup-root, a folder only root can enter (a page
# can't write to GlobalStorage). The disk is read again here: an answer that
# no longer matches what is on the disk stops the install before anything
# is written.

import json
import os
import stat
import subprocess
import sys

import libcalamares

# Calamares runs this file without its folder on the import path.
sys.path.insert(0, libcalamares.job.working_path)
sys.dont_write_bytecode = True

from rayedisk_apply import CommandFailed, Writer
from rayedisk_core import Refused, plan
from rayedisk_probe import hardware_of, read_machine, table_of

ANSWERS = "/run/raye-setup"
ANSWER = os.path.join(ANSWERS, "answer-disk")
# raye-setup-private makes it 0700 and the file in it 0600, empty
PASSPHRASE = os.path.join("/run/raye-setup-root", "answer-disk-passphrase")
CHOICES = os.path.join(ANSWERS, "choices")
ANSWER_LIMIT = 16 * 1024

TEXT = {
    "en": {"name": "Getting the disk ready",
           "title": "Raye couldn't get the disk ready",
           "untouched": "Nothing on the disk was changed.",
           "no-choice": "No choice was made on the disk page.",
           "no-efi": "Raye couldn't tell how this computer starts (UEFI or BIOS). Restart it from the USB stick and try again.",
           "no-passphrase": "The disk password didn't reach the install. Start Setup again.",
           "live": "This is the disk Raye started from.",
           "in-use": "This disk is in use.",
           "unreadable": "Raye couldn't read this disk.",
           "unsafe-folder": "A folder Raye needs while installing isn't safe to use. Start Setup again.",
           "disk-changed": "The disk changed after you chose how to use it. Start Setup again and choose again.",
           "too-small": "There isn't enough room on this disk for Raye.",
           "old-table": "This disk uses an older layout that can't hold Raye next to another system.",
           "shared-efi": "Another system of the same family starts from this disk, and Raye would replace how it starts.",
           "not-offered": "That partition belongs to another system and can't be used.",
           "cannot-shrink": "That volume can't be made smaller.",
           "keep-out-of-range": "The size chosen for the other system no longer fits. Start Setup again.",
           "table-mismatch": "The disk doesn't read back the way it was written, so Raye stopped before formatting anything.",
           "full-table": "This disk's older layout has no room left for two more partitions.",
           "linux-check": "The other system's volume needs a check. Start it, shut it down normally, then try again.",
           "linux-hibernated": "The other system on this disk is hibernated. Start it and shut it down normally.",
           "linux-unknown": "Raye couldn't read the other system's volume well enough to resize it.",
           "btrfs-multi": "The other system's volume spans several disks, so Raye can't make it smaller.",
           "xfs": "An XFS volume can't be made smaller.",
           "encrypted": "The other system's volume is encrypted, so Raye can't make it smaller.",
           "lvm": "The other system uses LVM volumes, which Raye can't make smaller.",
           "failed": "A disk command failed:"},
    "fr": {"name": "Préparation du disque",
           "title": "Raye n'a pas pu préparer le disque",
           "untouched": "Rien n'a été modifié sur le disque.",
           "no-choice": "Aucun choix n'a été fait sur la page Disque.",
           "no-efi": "Cet ordinateur a démarré dans son ancien mode BIOS. Raye a besoin d'UEFI : activez-le dans les réglages de l'ordinateur et recommencez.",
           "no-passphrase": "Le mot de passe du disque n'est pas arrivé jusqu'à l'installation. Relancez l'installation.",
           "live": "C'est le disque depuis lequel Raye a démarré.",
           "in-use": "Ce disque est utilisé.",
           "unreadable": "Raye n'a pas pu lire ce disque.",
           "unsafe-folder": "Un dossier dont Raye a besoin pendant l'installation n'est pas sûr. Relancez l'installation.",
           "disk-changed": "Le disque a changé après votre choix. Relancez l'installation et choisissez de nouveau.",
           "too-small": "Il n'y a pas assez de place sur ce disque pour Raye.",
           "old-table": "Ce disque utilise une ancienne disposition qui ne peut pas accueillir Raye à côté d'un autre système.",
           "shared-efi": "Un autre système de la même famille démarre depuis ce disque, et Raye remplacerait son démarrage.",
           "not-offered": "Cette partition appartient à un autre système et ne peut pas être utilisée.",
           "cannot-shrink": "Ce volume ne peut pas être réduit.",
           "keep-out-of-range": "La taille choisie pour l'autre système ne convient plus. Relancez l'installation.",
           "table-mismatch": "Le disque ne se relit pas comme il a été écrit : Raye s'est arrêté avant de formater quoi que ce soit.",
           "full-table": "L'ancienne disposition de ce disque n'a plus de place pour deux partitions de plus.",
           "linux-check": "Le volume de l'autre système doit être vérifié. Démarrez-le, éteignez-le normalement, puis réessayez.",
           "linux-hibernated": "L'autre système de ce disque est en veille prolongée. Démarrez-le et éteignez-le normalement.",
           "linux-unknown": "Raye n'a pas pu lire assez bien le volume de l'autre système pour le redimensionner.",
           "btrfs-multi": "Le volume de l'autre système s'étend sur plusieurs disques : Raye ne peut pas le réduire.",
           "xfs": "Un volume XFS ne peut pas être réduit.",
           "encrypted": "Le volume de l'autre système est chiffré : Raye ne peut pas le réduire.",
           "lvm": "L'autre système utilise des volumes LVM, que Raye ne peut pas réduire.",
           "failed": "Une commande de disque a échoué :"},
}
# what the windows findings say comes from the page's own strings; here the
# install only has to say it stopped
for words in TEXT.values():
    for code in ("bitlocker", "hibernated", "ntfs-dirty", "ntfs-check", "ntfs-busy", "ntfs-unknown"):
        words[code] = words["cannot-shrink"]


def chosen_lang():
    try:
        with open(CHOICES, encoding="utf-8", errors="replace") as f:
            for line in f.read(64 * 1024).splitlines():
                key, _, value = line.partition("=")
                if key.strip() == "lang" and value.strip().strip("\"'") in TEXT:
                    return value.strip().strip("\"'")
    except OSError:
        pass
    return "en"


def pretty_name():
    return TEXT[chosen_lang()]["name"]


def read_answer():
    try:
        with open(ANSWER, encoding="utf-8") as f:
            return json.loads(f.read(ANSWER_LIMIT))
    except (OSError, ValueError):
        return {}


def take_passphrase():
    """The disk password, gone from /run once read, whether it is used or not.

    Never through a link, and only from a file root owns."""
    try:
        fd = os.open(PASSPHRASE, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        fd = None
    text = ""
    if fd is not None:
        with os.fdopen(fd, encoding="utf-8", errors="replace") as f:
            info = os.fstat(f.fileno())
            if stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid():
                text = f.read(4096)
    try:
        os.unlink(PASSPHRASE)
    except OSError:
        pass
    return text


def run_command(argv, feed=None, tolerate=False):
    """A command, its stdout; what is fed to it never reaches the log."""
    libcalamares.utils.debug("rayedisk: " + " ".join(argv))
    done = subprocess.run(argv, input=feed, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, errors="replace", stdin=None if feed is not None else subprocess.DEVNULL)
    if done.returncode != 0 and not tolerate:
        raise CommandFailed(argv, done.returncode, done.stderr)
    return done.stdout


def fill_storage(gs, made, plan_made):
    gs.insert("partitions", made)
    firmware = plan_made.get("firmware", "efi")
    gs.insert("firmwareType", firmware)
    if firmware == "efi":
        gs.insert("efiSystemPartition", "/boot/efi")
        gs.insert("efiSystemPartitionName", "EFI")
    else:
        # the bootloader job puts GRUB at the start of this disk
        gs.insert("bootLoader", {"installPath": plan_made["disk"]})
    gs.insert("armInstall", False)
    gs.insert("reuseHome", False)
    gs.insert("luksFileSystemType", "luks2")
    # the fstab step makes the swap file from this
    install = {"erase": "erase", "shrink": "alongside", "free": "alongside",
               "replace": "replace"}[plan_made["mode"]]
    gs.insert("partitionChoices", {"install": install, "swap": "file"})


def run():
    words = TEXT[chosen_lang()]
    answer = read_answer()
    passphrase = take_passphrase()
    if not answer.get("encrypt"):
        passphrase = ""
    try:
        firmware, disks = read_machine(look=False)
        disk = next((d for d in disks if d["node"] == answer.get("disk")), None)
        if disk is None:
            raise Refused("disk-changed" if answer else "no-choice")
        made_plan = plan(disk, firmware, answer, bool(passphrase))
    except Refused as no:
        libcalamares.utils.warning(f"rayedisk: refused: {no}")
        return (words["title"], words.get(no.code, no.code) + " " + words["untouched"])

    def read_table(node):
        table = table_of(node)
        if table is None:
            # what was just written can't be read back: stop before formatting
            raise Refused("table-mismatch", node)
        return {"parts": [{"node": p["node"], "start": int(p["start"]), "sectors": int(p["size"]),
                           "type": str(p.get("type", ""))} for p in table.get("partitions", [])]}

    writer = Writer(run_command, read_table,
                    note=lambda text: libcalamares.utils.debug("rayedisk: " + text),
                    progress=libcalamares.job.setprogress,
                    identify=hardware_of)
    try:
        made = writer.apply(made_plan, disk, passphrase)
    except Refused as no:
        libcalamares.utils.warning(f"rayedisk: refused: {no}")
        return (words["title"], words.get(no.code, no.code))
    except CommandFailed as failed:
        libcalamares.utils.warning(f"rayedisk: {failed}")
        return (words["title"], f"{words['failed']} {failed}")
    fill_storage(libcalamares.globalstorage, made, made_plan)
    return None
