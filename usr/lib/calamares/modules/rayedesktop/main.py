#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The desktop picked on Setup's "Choose your desktop" page (answer-desktop).
#
#  - KDE Plasma, or no answer: nothing to do, the image is a Plasma system.
#  - Hyprland: raye-hyprland is added to the new system, from the pool on
#    the stick when it carries one (offline), from the network otherwise,
#    and becomes the session the account signs in to: SDDM's last session,
#    AccountsService, and the autologin session when sddm.conf names one.
#    KDE Plasma stays installed and can be picked on the sign-in screen.
#    When Hyprland cannot be added nothing is switched, and the last page
#    says the PC starts with KDE Plasma (desktop-result).
#
# The pool is a flat apt folder (the .debs and their Packages index) at
# /cdrom/raye/desktops; mount.conf binds /cdrom into the new system, so the
# same path works from inside it. Runs after `packages`, which has already
# read the online package lists when the PC is online.

import gzip
import os
import re
import shutil
import tempfile

import libcalamares

ANSWERS = "/run/raye-setup"
CHOICES = "/run/raye-setup/choices"
RESULT = "/run/raye-setup-root/desktop-result"
POOL = "/cdrom/raye/desktops"
PACKAGE = "raye-hyprland"
SESSION_NAME = "raye-hyprland"
SESSION_FILE = "/usr/share/wayland-sessions/raye-hyprland.desktop"
# inside the new system, removed when the job ends
WORK = "/var/tmp/raye-desktop"
USER_NAME = re.compile(r"[a-z_][a-z0-9_.-]{0,31}")
NETWORK_TIMEOUT = 1800
POOL_TIMEOUT = 600

NAMES = {
    "plasma": {"en": "KDE Plasma desktop", "fr": "Bureau KDE Plasma"},
    "hyprland": {"en": "Adding Hyprland", "fr": "Ajout de Hyprland"},
}


def read_lang():
    try:
        with open(CHOICES, encoding="utf-8", errors="replace") as f:
            for line in f.read(64 * 1024).splitlines():
                key, _, value = line.partition("=")
                if key.strip() == "lang":
                    return value.strip().strip("\"'")
    except OSError:
        pass
    return "en"


def read_choice():
    """"hyprland" when the page said so, "plasma" for anything else."""
    try:
        with open(os.path.join(ANSWERS, "answer-desktop"), encoding="utf-8", errors="replace") as f:
            text = f.read(64).strip()
    except OSError:
        return "plasma"
    return "hyprland" if text == "hyprland" else "plasma"


def pretty_name():
    names = NAMES[read_choice()]
    return names.get(read_lang(), names["en"])


def pool_offers(pool, package):
    """True when the pool's Packages index lists the package."""
    wanted = f"Package: {package}"
    for name, opener in (("Packages", open), ("Packages.gz", gzip.open)):
        try:
            with opener(os.path.join(pool, name), "rt", encoding="utf-8", errors="replace") as f:
                return any(line.rstrip() == wanted for line in f)
        except OSError:
            continue
    return False


# target_env_call(command, stdin, timeout): positional, with stdin as a
# string, since the binding takes no None there
def apt(*args, options=()):
    return (["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "-q"]
            + [a for o in options for a in ("-o", o)] + list(args))


def install_from_pool(root, pool, call):
    """apt in the new system with the pool as its only source."""
    work = os.path.join(root, WORK.lstrip("/"))
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(work, "lists", "partial"))
    os.makedirs(os.path.join(work, "parts"))
    with open(os.path.join(work, "sources.list"), "w") as f:
        f.write(f"deb [trusted=yes] file:{pool} ./\n")
    options = (f"Dir::Etc::SourceList={WORK}/sources.list",
               f"Dir::Etc::SourceParts={WORK}/parts",
               f"Dir::State::Lists={WORK}/lists",
               "APT::Get::List-Cleanup=false",
               # no cache built from the pool alone is left for the next apt
               "Dir::Cache::pkgcache=",
               "Dir::Cache::srcpkgcache=")
    try:
        if call(apt("update", options=options), "", POOL_TIMEOUT) != 0:
            return False
        return call(apt("-y", "--no-install-recommends", "install", PACKAGE, options=options),
                    "", POOL_TIMEOUT) == 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def install_from_network(call):
    return call(apt("-y", "--no-install-recommends", "install", PACKAGE), "", NETWORK_TIMEOUT) == 0


def atomic_write(path, data, mode, owner=None):
    """Replace path in one step, never through a link."""
    if os.path.islink(path):
        raise OSError(f"{path} is a link")
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".raye-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, mode)
        if owner:
            os.chown(tmp, *owner)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def set_keys(path, group, values, mode, owner=None):
    """key=value lines in [group] of an ini file; every other line stays."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []
    header = f"[{group}]"
    if header not in lines:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(header)
    at = lines.index(header) + 1
    end = at
    while end < len(lines) and not lines[end].startswith("["):
        end += 1
    for key, value in values.items():
        for i in range(at, end):
            if lines[i].split("=", 1)[0].strip() == key:
                lines[i] = f"{key}={value}"
                break
        else:
            # after the group's last entry, before the blank line that ends it
            last = end
            while last > at and not lines[last - 1].strip():
                last -= 1
            lines.insert(last, f"{key}={value}")
            end += 1
    atomic_write(path, ("\n".join(lines) + "\n").encode(), mode, owner)
    return True


def passwd_entry(root, name):
    """(uid, gid, home) of an account of the new system, or None."""
    try:
        with open(os.path.join(root, "etc", "passwd")) as f:
            for line in f:
                fields = line.rstrip("\n").split(":")
                if len(fields) >= 7 and fields[0] == name:
                    return int(fields[2]), int(fields[3]), fields[5]
    except (OSError, ValueError):
        pass
    return None


def write_sddm_state(root, username):
    """SDDM signs in to the last session, which it remembers by the path of
    the session file (sddm 0.21, SessionModel.cpp), in its home folder."""
    sddm = passwd_entry(root, "sddm")
    if not sddm or not passwd_entry(root, username):
        return False
    home = os.path.join(root, os.path.normpath(sddm[2]).lstrip("/"))
    if os.path.islink(home) or not os.path.isdir(home):
        return False
    return set_keys(os.path.join(home, "state.conf"), "Last",
                    {"Session": SESSION_FILE, "User": username}, 0o644, sddm[:2])


def write_accounts_service(root, username):
    if not passwd_entry(root, username):
        return False
    folder = os.path.join(root, "var", "lib", "AccountsService", "users")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return set_keys(os.path.join(folder, username), "User",
                    {"Session": SESSION_NAME, "SessionType": "wayland"}, 0o600)


def group_has(lines, group, key):
    inside = False
    for line in lines:
        if line.startswith("["):
            inside = line.strip() == f"[{group}]"
        elif inside and line.split("=", 1)[0].strip() == key:
            return True
    return False


def write_autologin_session(root):
    """Only when the file names an autologin session already (the
    displaymanager step writes Plasma's there)."""
    path = os.path.join(root, "etc", "sddm.conf")
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return False
    if not group_has(lines, "Autologin", "Session"):
        return False
    return set_keys(path, "Autologin", {"Session": os.path.basename(SESSION_FILE)}, 0o644)


def leave_result(text):
    try:
        with open(RESULT, "w") as f:
            f.write(text + "\n")
    except OSError as e:
        libcalamares.utils.warning(f"desktop: result not written: {e}")


def run():
    root = libcalamares.globalstorage.value("rootMountPoint")
    if not root or read_choice() != "hyprland":
        return None
    call = libcalamares.utils.target_env_call
    pool = (libcalamares.job.configuration or {}).get("pool", POOL)

    # whatever goes wrong here, the install goes on with KDE Plasma
    where = pool if pool_offers(pool, PACKAGE) else "the network"
    try:
        ok = install_from_pool(root, pool, call) if where == pool else install_from_network(call)
    except OSError as e:
        libcalamares.utils.warning(f"desktop: {e}")
        ok = False
    libcalamares.utils.debug(f"desktop: {PACKAGE} from {where}: {'done' if ok else 'failed'}")

    if not ok or not os.path.isfile(os.path.join(root, SESSION_FILE.lstrip("/"))):
        libcalamares.utils.warning("desktop: Hyprland could not be added, KDE Plasma stays the session")
        leave_result("plasma-fallback")
        return None

    username = libcalamares.globalstorage.value("username") or ""
    if not USER_NAME.fullmatch(username):
        libcalamares.utils.warning(f"desktop: odd account name {username!r}, session left as is")
        return None
    for what, write in (("SDDM", lambda: write_sddm_state(root, username)),
                        ("AccountsService", lambda: write_accounts_service(root, username)),
                        ("autologin", lambda: write_autologin_session(root))):
        try:
            libcalamares.utils.debug(f"desktop: {what}: {'written' if write() else 'left as is'}")
        except OSError as e:
            libcalamares.utils.warning(f"desktop: {what} not written: {e}")
    return None
