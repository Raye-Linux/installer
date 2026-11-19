# SPDX-License-Identifier: GPL-3.0-or-later
"""The second half of "replace and keep my files", once the account exists.

rayedisk did the first half: the old system is gone and its folders are
either on its own /home partition (now Raye's /home) or on the staging
partition. Here they go into the new account.

 - home:  each folder is moved in (a rename). Nothing is copied or deleted.
 - stage: each folder is copied in and read back. Only when every file is
          there does the staging partition go, and Raye's volume grows
          over its room. Otherwise it stays: it is then the only copy.
"""
import os
import time

import rayedisk_extras as extras
import rayedisk_keep as keep
from rayedisk_apply import CommandFailed, Writer, staged_number
from rayedisk_core import Refused, check_written


def keep_storage(plan_made, made):
    """What the rayekeep job needs to finish moving the files, or None."""
    kept = plan_made.get("keep")
    if not kept:
        return None
    root = next((p for p in made if p["mountPoint"] == "/"), {})
    added = next((a for a in plan_made["add"] if a["role"] == "root"), {})
    stage = plan_made.get("stage") or {}
    users = [{"name": u["name"], "home": u["home"], "uid": u.get("uid", -1),
              "folders": [{"kind": f["kind"], "path": f["path"], "files": f["files"], "bytes": f["bytes"]}
                          for f in u["folders"]],
              "wallpaper": u.get("wallpaper") or {}} for u in kept["users"]]
    return {"way": kept["way"], "name": kept.get("name", ""), "system": kept.get("system", "linux"),
            "disk": plan_made["disk"], "hardware": plan_made.get("hardware", ""),
            "label": plan_made.get("label", "gpt"),
            "home": kept.get("home", ""), "stage": kept.get("stage", ""),
            "stageStart": stage.get("start", 0), "stageSectors": stage.get("sectors", 0),
            "root": root.get("device", ""), "rootStart": added.get("start", 0),
            "rootSectors": added.get("sectors", 0), "luks": root.get("luksMapperName", ""),
            "users": users, "apps": list(kept.get("apps") or []),
            "files": kept.get("files", 0), "bytes": kept.get("bytes", 0)}


def account(root, username):
    """(uid, gid, home) of the new account in the installed system."""
    for line in keep.read_small(os.path.join(root, "etc/passwd"), 1024 * 1024).splitlines():
        fields = line.split(":")
        if len(fields) >= 7 and fields[0] == username and fields[2].isdigit() and fields[3].isdigit():
            return int(fields[2]), int(fields[3]), fields[5]
    return None


def make_room_for(root, username):
    """Before the account is made: a folder of the old /home with its name
    gets ".old" so the account starts from Raye's own. Returns the new name."""
    base = os.path.join(root, "home")
    if not username or not os.path.lexists(os.path.join(base, username)):
        return ""
    name, number = username + ".old", 2
    while os.path.lexists(os.path.join(base, name)):
        name, number = "%s.old (%d)" % (username, number), number + 1
    os.rename(os.path.join(base, username), os.path.join(base, name))
    return name


def set_user_dirs(home, lang, owner):
    """The six folders, made, and named in user-dirs.dirs so they stay."""
    copier = keep.Copier(owner=owner)
    for kind in keep.KINDS:
        copier.folder(os.path.join(home, keep.FOLDERS.get(lang, keep.ENGLISH)[kind]))
    config = copier.folder(os.path.join(home, ".config"))
    path = os.path.join(config, "user-dirs.dirs")
    text = keep.user_dirs_text(keep.read_small(path), lang)
    temporary = path + ".raye"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    if owner is not None:
        os.chown(temporary, owner[0], owner[1])
    os.replace(temporary, path)


def finish_extras(kept, root, home, lang, owner, loose_picture):
    """After the folders: the browsers' locks off, the wallpaper in place,
    and the first sign-in's one-shot that sets it and brings the apps back.

    loose_picture(index, user) is the file to copy when the wallpaper was
    not in a kept folder. Returns {"wallpaper": bool, "apps": count}."""
    several = len(kept["users"]) > 1
    for kind, path in keep.PROFILES.items():
        where = keep.real_dir(home, path)
        if where and any(f["kind"] == kind for u in kept["users"] for f in u["folders"]):
            try:
                extras.clear_browser_locks(where)
            except OSError:
                pass
    picture = ""
    for index, user in enumerate(kept["users"]):
        if not (user.get("wallpaper") or {}).get("path"):
            continue
        inside = extras.wallpaper_inside(user)
        if inside:
            kind, rest = inside
            spot = os.path.join(home, keep.destination(lang, kind, user["name"], several), rest)
            picture = spot if os.path.isfile(spot) and not os.path.islink(spot) else ""
        else:
            source = loose_picture(index, user)
            if source:
                try:
                    pictures = keep.Copier(owner=owner).folder(
                        os.path.join(home, keep.FOLDERS.get(lang, keep.ENGLISH)["pictures"]))
                    name = extras.picture_name(os.path.basename(source), source, lang)
                    picture = keep.Copier(owner=owner).copy_file(source, pictures, name)
                except (OSError, keep.CopyFailed):
                    picture = ""
        break
    in_target = ("/" + os.path.relpath(picture, root)) if picture else ""
    apps = kept.get("apps") or []
    try:
        extras.leave_welcome_back(root, home, owner, lang, wallpaper=in_target, apps=apps)
    except OSError:
        return {"wallpaper": False, "apps": 0}
    return {"wallpaper": bool(in_target), "apps": len(apps)}


def _result(kept, ok, **more):
    entry = {"way": kept["way"], "name": kept.get("name", ""), "ok": ok}
    entry.update(more)
    return entry


class Finisher(Writer):
    def move_home(self, kept, root, username, lang, moved_aside=""):
        """The home way: every folder moved into the account."""
        found = account(root, username)
        if found is None:
            return _result(kept, False, moved=0, failed=1)
        uid, gid, _ = found
        home = os.path.join(root, "home", username)
        set_user_dirs(home, lang, (uid, gid))
        several = len(kept["users"]) > 1
        moved, failed = 0, []
        for user in kept["users"]:
            name = moved_aside if moved_aside and user["home"] == username else user["home"]
            old = keep.real_dir(os.path.join(root, "home"), name)
            for folder in user["folders"]:
                source = keep.real_dir(old, folder["path"]) if old else None
                target = keep.Copier(owner=(uid, gid)).folder(
                    os.path.join(home, keep.destination(lang, folder["kind"], user["name"], several)))
                if source is None:
                    failed.append(folder["path"])
                    continue
                if os.path.realpath(source) == os.path.realpath(target):
                    continue
                count, missed = keep.move_contents(source, target, (uid, gid))
                moved += count
                failed += missed
        self.note(f"moved {moved} items into {home}, {len(failed)} failed")

        def loose_picture(index, user):
            name = moved_aside if moved_aside and user["home"] == username else user["home"]
            old = keep.real_dir(os.path.join(root, "home"), name)
            names = user["wallpaper"]["path"].split("/")
            folder = keep.real_dir(old, "/".join(names[:-1])) if old else None
            return os.path.join(folder, names[-1]) if folder else ""
        more = finish_extras(kept, root, home, lang, (uid, gid), loose_picture)
        return _result(kept, not failed, moved=moved, failed=len(failed), **more)

    def bring_home(self, kept, root, username, lang, passphrase=""):
        """The stage way: copy, read back, then take the staging partition away."""
        found = account(root, username)
        if found is None:
            return _result(kept, False, files=0, failed=1, left=True)
        uid, gid, _ = found
        home = os.path.join(root, "home", username)
        set_user_dirs(home, lang, (uid, gid))
        several = len(kept["users"]) > 1
        copier = keep.Copier(owner=(uid, gid))
        expected, missing = 0, 0
        self.same_disk(kept)
        with self.mounted(kept["stage"], "ext4", "keep-stage") as stage:
            for index, user in enumerate(kept["users"]):
                for folder in user["folders"]:
                    source = keep.real_dir(stage, os.path.join("users", str(index), folder["kind"]))
                    if source is None:
                        missing += 1
                        continue
                    expected += keep.measure(source)["files"]
                    target = os.path.join(home, keep.destination(lang, folder["kind"], user["name"], several))
                    copier.copy_tree(source, target)
            done = copier.report()

            def loose_picture(index, user):
                folder = keep.real_dir(stage, os.path.join("users", str(index), "wallpaper"))
                name = os.path.basename(user["wallpaper"]["path"])
                return os.path.join(folder, name) if folder and os.path.isfile(os.path.join(folder, name)) else ""
            # before the staging partition goes: the picture may be on it
            more = finish_extras(kept, root, home, lang, (uid, gid), loose_picture)
        self.note(f"copied {done['files']} files into {home}, {done['failed']} failed")
        ok = not missing and not done["failed"] and done["files"] == expected == kept.get("files", expected)
        if not ok:
            return _result(kept, False, files=done["files"], failed=done["failed"] + missing, left=True, **more)
        try:
            grown, left = self.drop_stage_and_grow(kept, root, passphrase), False
        except (Refused, CommandFailed) as no:
            # the files are in the account; the staging partition just stays
            self.note(f"the staging partition stays: {no}")
            grown, left = False, True
        return _result(kept, True, files=done["files"], bytes=done["bytes"], skipped=done["skipped"],
                       left=left, grown=grown, **more)

    def patiently(self, argv, tries=10):
        """A command udev may still be busy against (it probes what was just
        unmounted): tried again for a few seconds."""
        for attempt in range(tries):
            try:
                return self.run(argv)
            except CommandFailed:
                if attempt == tries - 1:
                    raise
                time.sleep(0.5)
                self.run(["udevadm", "settle"], tolerate=True)
        return ""

    def drop_stage_and_grow(self, kept, root, passphrase):
        """The staging partition goes and Raye's own volume takes its room.

        Only the table entry of the staging partition is removed. Growing
        is the last thing done: a failure leaves free space, nothing else.
        """
        disk = kept["disk"]
        before = self.read_table(disk)
        by_start = {p["start"]: p for p in before["parts"]}
        stage = by_start.get(kept["stageStart"])
        root_part = by_start.get(kept["rootStart"])
        if not stage or not root_part or stage["node"] != kept["stage"] or root_part["node"] != kept["root"] \
                or stage["sectors"] != kept["stageSectors"] or root_part["sectors"] != kept["rootSectors"]:
            raise Refused("table-mismatch", disk)
        if self.run(["findmnt", "--noheadings", "--source", stage["node"]], tolerate=True).strip():
            raise Refused("in-use", stage["node"])
        grown = kept["stageStart"] + kept["stageSectors"] - kept["rootStart"]
        change = {"disk": disk, "wipe": False, "add": [],
                  "delete": {"node": stage["node"], "number": staged_number(stage["node"])},
                  "shrink": {"node": root_part["node"], "sectors": grown}}
        self.same_disk(kept)
        common = ["sfdisk", "--lock", "--no-reread", "--no-tell-kernel"]
        self.run(common + ["--delete", disk, str(change["delete"]["number"])])
        self.run(common + ["--wipe", "never", "-N", str(staged_number(root_part["node"])), disk],
                 feed="start=%d, size=%d\n" % (kept["rootStart"], grown))
        check_written(before, self.read_table(disk), change)
        try:
            # Raye's root is mounted: partx --update refuses to touch it,
            # resizepart only changes its end
            self.run(["udevadm", "settle"], tolerate=True)
            self.patiently(["partx", "--delete", "--nr", str(change["delete"]["number"]), disk])
            self.patiently(["resizepart", disk, str(staged_number(root_part["node"])), str(grown)])
            self.run(["udevadm", "settle"], tolerate=True)
            if kept.get("luks"):
                self.run(["cryptsetup", "resize", "--key-file=-", kept["luks"]], feed=passphrase)
            self.run(["btrfs", "filesystem", "resize", "max", root])
        except Exception as failed:  # noqa: BLE001 - growing is a bonus, the files are safe
            self.note(f"Raye's volume did not grow: {failed}")
            return False
        return True
