# SPDX-License-Identifier: GPL-3.0-or-later
"""The person's own folders on the system Raye replaces: found, counted,
copied, read back.

Raye keeps the six folders Windows shows under "This PC" (Desktop,
Documents, Downloads, Music, Pictures, Videos) of every account of the
other system. Two ways, chosen by rayedisk_core:

 - "home": the other Linux keeps /home on a partition of its own. That
   partition is never written by the disk job. It becomes Raye's /home and
   each folder is moved (renamed, same filesystem) into the new account.
 - "stage": the folders are on the volume Raye replaces. They are copied
   to a partition made for them before that volume goes, and copied again
   into the new account before that partition goes.

A copy counts once every file has been read back from the disk with the
same size and SHA-256. Nothing is deleted on the strength of anything less.
"""
import errno
import hashlib
import os
import stat

KINDS = ("desktop", "documents", "downloads", "music", "pictures", "videos")
XDG_KEYS = {"desktop": "XDG_DESKTOP_DIR", "documents": "XDG_DOCUMENTS_DIR",
            "downloads": "XDG_DOWNLOAD_DIR", "music": "XDG_MUSIC_DIR",
            "pictures": "XDG_PICTURES_DIR", "videos": "XDG_VIDEOS_DIR"}
ENGLISH = {"desktop": "Desktop", "documents": "Documents", "downloads": "Downloads",
           "music": "Music", "pictures": "Pictures", "videos": "Videos"}
# the names xdg-user-dirs gives them in each language Raye speaks
FOLDERS = {"en": ENGLISH,
           "fr": {"desktop": "Bureau", "documents": "Documents", "downloads": "Téléchargements",
                  "music": "Musique", "pictures": "Images", "videos": "Vidéos"}}
# Windows keeps the English names on disk in every language
WINDOWS_SKIP = {"default", "default user", "public", "all users", "defaultuser0",
                "defaultuser100000", "wdagutilityaccount", "defaultapppool"}

# where an account's own files are, and what is not a person's account
FIRST_UID, LAST_UID = 1000, 60000
SMALL_FILE = 64 * 1024
CHUNK = 4 * 1024 * 1024


class CopyFailed(Exception):
    """What could not be copied or did not read back the same."""


def read_small(path, limit=SMALL_FILE):
    """A small text file, never through a link; "" when it isn't there."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return ""
    with os.fdopen(fd, "rb") as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            return ""
        return f.read(limit).decode("utf-8", "replace")


def parse_passwd(text):
    """[(name, uid, gid, home)] of the people's accounts in /etc/passwd."""
    found = []
    for line in text.splitlines():
        fields = line.split(":")
        if len(fields) < 7 or not fields[2].isdigit() or not fields[3].isdigit():
            continue
        uid = int(fields[2])
        if FIRST_UID <= uid < LAST_UID and fields[5].startswith("/home/"):
            found.append((fields[0], uid, int(fields[3]), fields[5]))
    return found


def parse_fstab(text):
    """[(spec, mount point, fstype, options)], comments left out."""
    found = []
    for line in text.splitlines():
        words = line.split()
        if len(words) >= 3 and not words[0].startswith("#"):
            found.append((words[0], words[1], words[2], words[3] if len(words) > 3 else "defaults"))
    return found


def fstab_entry(entries, mount_point):
    for entry in entries:
        if entry[1].rstrip("/") == mount_point.rstrip("/") or (mount_point == "/" and entry[1] == "/"):
            return entry
    return None


def subvolume_of(options):
    """The subvol= of a btrfs mount, without its leading slash; "" for none."""
    for option in options.split(","):
        key, sep, value = option.partition("=")
        if sep and key == "subvol":
            return value.strip("/")
    return ""


def os_name(text):
    """PRETTY_NAME of an os-release, else NAME, else ""."""
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            fields[key.strip()] = value.strip().strip("\"'")
    return fields.get("PRETTY_NAME") or fields.get("NAME") or ""


def _clean(relative):
    """A path below a home, as a list of names, None when it leaves it."""
    names = [n for n in relative.split("/") if n not in ("", ".")]
    if not names or any(n == ".." for n in names):
        return None
    return names


def parse_user_dirs(text):
    """{kind: relative path} from a user-dirs.dirs, English for what it doesn't set.

    A folder set to the home itself is turned off: it is left out.
    """
    found = dict(ENGLISH)
    for line in text.splitlines():
        key, sep, value = line.strip().partition("=")
        kind = next((k for k, v in XDG_KEYS.items() if v == key), None)
        if not sep or kind is None:
            continue
        value = value.strip().strip('"')
        if not value.startswith("$HOME"):
            # somewhere outside the home is not the person's folder to move
            found.pop(kind, None)
            continue
        names = _clean(value[len("$HOME"):])
        if names is None:
            found.pop(kind, None)
        else:
            found[kind] = "/".join(names)
    return found


def real_dir(base, relative):
    """base/relative when every step of it is a real folder (no link), else None."""
    names = _clean(relative)
    if names is None:
        return None
    at = base
    for name in names:
        at = os.path.join(at, name)
        try:
            if not stat.S_ISDIR(os.lstat(at).st_mode):
                return None
        except OSError:
            return None
    return at


def measure(path):
    """{files, bytes, links, other, unreadable} of a folder, links not followed."""
    count = {"files": 0, "bytes": 0, "links": 0, "other": 0, "unreadable": 0}
    stack = [path]
    while stack:
        here = stack.pop()
        try:
            entries = list(os.scandir(here))
        except OSError:
            count["unreadable"] += 1
            continue
        for entry in entries:
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError:
                count["unreadable"] += 1
                continue
            if stat.S_ISLNK(info.st_mode):
                count["links"] += 1
            elif stat.S_ISDIR(info.st_mode):
                stack.append(entry.path)
            elif stat.S_ISREG(info.st_mode):
                count["files"] += 1
                count["bytes"] += info.st_size
            else:
                count["other"] += 1
    return count


def _folders(home, dirs):
    """The kept folders of one home that exist and hold something."""
    folders = []
    for kind in KINDS:
        relative = dirs.get(kind)
        where = real_dir(home, relative) if relative else None
        if where is None:
            continue
        size = measure(where)
        if size["files"] or size["links"]:
            folders.append({"kind": kind, "path": relative, "files": size["files"],
                            "bytes": size["bytes"], "unreadable": size["unreadable"]})
    return folders


def linux_users(root, home_base):
    """The accounts of a Linux system and their folders.

    root is where its / is (for /etc/passwd), home_base where its /home is.
    Each user's path is relative to home_base.
    """
    users = []
    for name, uid, gid, home in parse_passwd(read_small(os.path.join(root, "etc/passwd"), 1024 * 1024)):
        relative = home[len("/home/"):]
        where = real_dir(home_base, relative)
        if where is None:
            continue
        dirs = parse_user_dirs(read_small(os.path.join(where, ".config/user-dirs.dirs")))
        folders = _folders(where, dirs)
        if folders:
            users.append({"name": name, "home": relative, "uid": uid, "folders": folders})
    return users


def windows_users(users_dir):
    """The accounts under C:\\Users and their folders."""
    users = []
    try:
        names = sorted(os.listdir(users_dir))
    except OSError:
        return users
    for name in names:
        if name.lower() in WINDOWS_SKIP:
            continue
        where = real_dir(users_dir, name)
        if where is None:
            continue
        folders = _folders(where, ENGLISH)
        if folders:
            users.append({"name": name, "home": name, "folders": folders})
    return users


def totals(users):
    files = sum(f["files"] for u in users for f in u["folders"])
    size = sum(f["bytes"] for u in users for f in u["folders"])
    unreadable = sum(f.get("unreadable", 0) for u in users for f in u["folders"])
    return files, size, unreadable


def destination(lang, kind, user, several):
    """Where one folder lands in the new home, relative to it.

    The account name comes from the other system: one plain name, or "user".
    """
    name = FOLDERS.get(lang, ENGLISH)[kind]
    if not several:
        return name
    user = str(user).replace("/", "_").strip()
    return os.path.join(name, user if user not in ("", ".", "..") else "user")


def user_dirs_text(existing, lang):
    """The new account's user-dirs.dirs with the six folders set.

    Lines it already has for other folders stay. Set, the folders keep
    their names when xdg-user-dirs runs at the first sign-in.
    """
    keep = [line for line in existing.splitlines()
            if line.split("=", 1)[0].strip() not in XDG_KEYS.values()]
    names = FOLDERS.get(lang, ENGLISH)
    keep += ['%s="$HOME/%s"' % (XDG_KEYS[kind], names[kind]) for kind in KINDS]
    return "\n".join(keep) + "\n"


def free_name(folder, name):
    """name, or "name (2).ext" and so on when folder already has one."""
    if not os.path.lexists(os.path.join(folder, name)):
        return name
    stem, dot, ext = name.rpartition(".")
    if not dot or not stem:
        stem, ext = name, ""
    else:
        ext = "." + ext
    number = 2
    while os.path.lexists(os.path.join(folder, "%s (%d)%s" % (stem, number, ext))):
        number += 1
    return "%s (%d)%s" % (stem, number, ext)


def _hash_of(fd):
    digest = hashlib.sha256()
    size = 0
    while True:
        block = os.read(fd, CHUNK)
        if not block:
            return digest.hexdigest(), size
        digest.update(block)
        size += len(block)


def _drop_cache(fd):
    try:
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    except (AttributeError, OSError):
        pass


class Copier:
    """Copies folders file by file and reads every file back.

    links: "copy" makes the same link, "skip" leaves it out (a Windows
    junction points into C:, which is going). The owner of what is made is
    owner, a (uid, gid) or None to leave it to whoever runs this.
    """

    def __init__(self, owner=None, links="copy", progress=lambda done: None, mode_mask=0o7777):
        self.owner = owner
        self.links = links
        self.progress = progress
        self.mode_mask = mode_mask
        self.files = 0
        self.bytes = 0
        self.copied_links = 0
        self.skipped = 0
        self.failed = []

    def _own(self, path, follow=True):
        if self.owner is not None:
            os.chown(path, self.owner[0], self.owner[1], follow_symlinks=follow)

    def folder(self, target):
        """target, made when missing (and its parents), owned like the rest."""
        made = []
        at = target
        while not os.path.lexists(at):
            made.append(at)
            at = os.path.dirname(at)
        for path in reversed(made):
            os.mkdir(path, 0o755)
            self._own(path)
        if not stat.S_ISDIR(os.lstat(target).st_mode):
            raise CopyFailed(target)
        return target

    def copy_file(self, source, folder, name):
        """One file, read back. Returns where it went."""
        src = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            info = os.fstat(src)
            if not stat.S_ISREG(info.st_mode):
                raise CopyFailed(source)
            target = os.path.join(folder, free_name(folder, name))
            dst = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            digest = hashlib.sha256()
            size = 0
            try:
                while True:
                    block = os.read(src, CHUNK)
                    if not block:
                        break
                    digest.update(block)
                    size += len(block)
                    view = memoryview(block)
                    while view:
                        view = view[os.write(dst, view):]
                os.fsync(dst)
                if self.owner is not None:
                    os.fchown(dst, self.owner[0], self.owner[1])
                os.fchmod(dst, stat.S_IMODE(info.st_mode) & self.mode_mask & 0o777 or 0o644)
            finally:
                os.close(dst)
        finally:
            os.close(src)
        if size != info.st_size:
            raise CopyFailed(source)
        os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns), follow_symlinks=False)
        # read back from the disk, not from what the kernel still remembers
        check = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            _drop_cache(check)
            again, again_size = _hash_of(check)
        finally:
            os.close(check)
        if again != digest.hexdigest() or again_size != size:
            raise CopyFailed(source)
        self.files += 1
        self.bytes += size
        self.progress(self.bytes)
        return target

    def copy_tree(self, source, target):
        """Everything under source into target (made if missing)."""
        self.folder(target)
        try:
            entries = sorted(os.scandir(source), key=lambda e: e.name)
        except OSError:
            self.failed.append(source)
            return
        for entry in entries:
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError:
                self.failed.append(entry.path)
                continue
            try:
                if stat.S_ISDIR(info.st_mode):
                    self.copy_tree(entry.path, os.path.join(target, entry.name))
                elif stat.S_ISREG(info.st_mode):
                    self.copy_file(entry.path, target, entry.name)
                elif stat.S_ISLNK(info.st_mode) and self.links == "copy":
                    link = os.path.join(target, free_name(target, entry.name))
                    os.symlink(os.readlink(entry.path), link)
                    self._own(link, follow=False)
                    self.copied_links += 1
                else:
                    self.skipped += 1
            except (OSError, CopyFailed):
                self.failed.append(entry.path)

    def report(self):
        return {"files": self.files, "bytes": self.bytes, "links": self.copied_links,
                "skipped": self.skipped, "failed": len(self.failed), "examples": self.failed[:10]}


def move_contents(source, target, owner):
    """Moves what is in source into target, on the same filesystem.

    A rename: nothing is copied and nothing is deleted. A name already in
    target gets " (2)". What moves gets owner (uid, gid), links not followed.
    Returns (moved, failed).
    """
    moved, failed = 0, []
    try:
        names = sorted(os.listdir(source))
    except OSError:
        return 0, [source]
    for name in names:
        here = os.path.join(source, name)
        there = os.path.join(target, free_name(target, name))
        try:
            os.rename(here, there)
        except OSError as error:
            # EXDEV: not the same filesystem, never copied behind the person's back
            failed.append(here if error.errno != errno.EXDEV else source)
            continue
        moved += 1
        _own_tree(there, owner, failed)
    if not os.listdir(source):
        try:
            os.rmdir(source)
        except OSError:
            pass
    return moved, failed


def _own_tree(path, owner, failed):
    stack = [path]
    while stack:
        here = stack.pop()
        try:
            os.chown(here, owner[0], owner[1], follow_symlinks=False)
            if stat.S_ISDIR(os.lstat(here).st_mode):
                stack.extend(os.path.join(here, n) for n in os.listdir(here))
        except OSError:
            failed.append(here)


def mount_argv(node, fstype, where):
    """How to look at another system's volume without changing it.

    ext3/ext4 without replaying the journal, xfs without recovery, btrfs at
    its top level (every subvolume is a folder there), NTFS through ntfs-3g.
    """
    if fstype in ("ext3", "ext4"):
        return ["mount", "-t", fstype, "-o", "ro,noload", node, where]
    if fstype == "xfs":
        return ["mount", "-t", "xfs", "-o", "ro,norecovery", node, where]
    if fstype == "btrfs":
        return ["mount", "-t", "btrfs", "-o", "ro,subvolid=5", node, where]
    if fstype == "ntfs":
        return ["mount", "-t", "ntfs-3g", "-o", "ro", node, where]
    return ["mount", "-t", fstype or "auto", "-o", "ro", node, where]


def root_of(top):
    """Where / of a Linux is inside its volume: "" or a subvolume's folder.

    The one holding etc/os-release and etc/fstab, at the top or one down.
    """
    candidates = [""]
    try:
        candidates += sorted(n for n in os.listdir(top) if real_dir(top, n))
    except OSError:
        return None
    for name in candidates:
        here = os.path.join(top, name)
        if os.path.isfile(os.path.join(here, "etc/fstab")) and \
                (os.path.isfile(os.path.join(here, "etc/os-release"))
                 or os.path.isfile(os.path.join(here, "usr/lib/os-release"))):
            return name
    return None


def look_linux(top, fstype, uuid):
    """What a mounted Linux volume holds: its name, and where /home is.

    {"name", "root", "home": {"on": "self", "path"} or {"on": "other",
    "spec", "fstype", "options"}}, None when it isn't a Linux system.
    """
    root = root_of(top)
    if root is None:
        return None
    here = os.path.join(top, root)
    name = os_name(read_small(os.path.join(here, "etc/os-release"))
                   or read_small(os.path.join(here, "usr/lib/os-release")))
    entries = parse_fstab(read_small(os.path.join(here, "etc/fstab")))
    home = fstab_entry(entries, "/home")
    if home is None:
        place = {"on": "self", "path": os.path.join(root, "home") if root else "home"}
    elif _same_volume(home[0], uuid) and fstype == "btrfs":
        place = {"on": "self", "path": subvolume_of(home[3])}
    elif _same_volume(home[0], uuid):
        place = {"on": "self", "path": "home"}
    else:
        place = {"on": "other", "spec": home[0], "fstype": home[2], "options": home[3]}
    return {"name": name, "root": root, "home": place}


def _same_volume(spec, uuid):
    return bool(uuid) and spec.upper() == ("UUID=" + uuid).upper()


def resolve_spec(spec, parts):
    """The partition an fstab spec names, among {"node", "uuid", "label", "partuuid"}."""
    key, sep, value = spec.partition("=")
    value = value.strip("\"'")
    for part in parts:
        if not sep and spec == part["node"]:
            return part
        wanted = {"UUID": "uuid", "LABEL": "label", "PARTUUID": "partuuid"}.get(key.upper())
        if sep and wanted and value and str(part.get(wanted) or "").lower() == value.lower():
            return part
    return None
