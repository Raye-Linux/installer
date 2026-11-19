#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Brings the folders Raye kept from the system it replaced into the new
# account, from what rayedisk left in GlobalStorage (rayeKeep). Two steps,
# one instance each (rayekeep_prepare.conf, rayekeep_copy.conf):
#
#   prepare  before the account is made: on a kept /home, a folder with the
#            account's name is moved aside so the account starts clean
#   copy     after: the folders go in (rayedisk_finish)
#
# Never stops the install: Raye is already in place by now, and the files
# are on the disk either way. The last page says what happened, from
# keep-result in root's own folder.

import json
import os
import subprocess
import sys

import libcalamares

sys.path.insert(0, os.path.join(os.path.dirname(libcalamares.job.working_path), "rayedisk"))
sys.dont_write_bytecode = True

from rayedisk_apply import BACKUP_DIR, CommandFailed, write_private  # noqa: E402
from rayedisk_core import Refused  # noqa: E402
from rayedisk_finish import Finisher, make_room_for  # noqa: E402
from rayedisk_probe import hardware_of, table_of  # noqa: E402

CHOICES = "/run/raye-setup/choices"
RESULT = os.path.join(BACKUP_DIR, "keep-result")

TEXT = {
    "en": {"name": "Bringing your files over"},
    "fr": {"name": "Transfert de vos fichiers"},
}


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


def run_command(argv, feed=None, tolerate=False):
    """A command, its stdout; what is fed to it never reaches the log."""
    libcalamares.utils.debug("rayekeep: " + " ".join(argv))
    done = subprocess.run(argv, input=feed, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, errors="replace", stdin=None if feed is not None else subprocess.DEVNULL)
    if done.returncode != 0 and not tolerate:
        raise CommandFailed(argv, done.returncode, done.stderr)
    return done.stdout


def read_table(node):
    table = table_of(node)
    if table is None:
        raise Refused("table-mismatch", node)
    return {"parts": [{"node": p["node"], "start": int(p["start"]), "sectors": int(p["size"]),
                       "type": str(p.get("type", ""))} for p in table.get("partitions", [])]}


def passphrase_of(gs):
    for part in gs.value("partitions") or []:
        if part.get("mountPoint") == "/" and part.get("luksPassphrase"):
            return part["luksPassphrase"]
    return ""


def run():
    gs = libcalamares.globalstorage
    kept = gs.value("rayeKeep")
    if not kept:
        return None
    root = gs.value("rootMountPoint")
    username = gs.value("username") or ""
    step = libcalamares.job.configuration.get("step", "copy")
    if step == "prepare":
        if kept["way"] == "home":
            try:
                gs.insert("rayeKeepMovedAside", make_room_for(root, username))
            except OSError as error:
                libcalamares.utils.warning(f"rayekeep: {error}")
        return None
    finisher = Finisher(run_command, read_table,
                        note=lambda text: libcalamares.utils.debug("rayekeep: " + text),
                        progress=lambda done: libcalamares.job.setprogress(
                            min(0.95, done / max(1, kept.get("bytes", 1)))),
                        identify=hardware_of)
    try:
        if kept["way"] == "home":
            result = finisher.move_home(kept, root, username, chosen_lang(),
                                        gs.value("rayeKeepMovedAside") or "")
        else:
            result = finisher.bring_home(kept, root, username, chosen_lang(), passphrase_of(gs))
    except (Refused, CommandFailed, OSError) as no:
        libcalamares.utils.warning(f"rayekeep: {no}")
        result = {"way": kept["way"], "name": kept.get("name", ""), "ok": False,
                  "left": kept["way"] == "stage"}
    try:
        write_private(RESULT, json.dumps(result, ensure_ascii=False))
    except Refused as no:
        libcalamares.utils.warning(f"rayekeep: {no}")
    libcalamares.job.setprogress(1.0)
    return None
