#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Disk encryption the way Raye does it, for installs with "Encrypt" ticked.
#
#  - a recovery key is added to the disk. It is kept in the person's
#    ~/.local/share/raye/recovery-key (0600) and shown by the first-run
#    welcome at first sign-in, never sent anywhere. A system without the
#    first-run welcome gets a one-time message with the key instead.
#  - when the computer has a TPM 2.0, the disk unlocks on its own at boot,
#    bound to the Secure Boot state only (PCR 7), so kernel and system
#    updates do not set off the recovery prompt.
#  - when the TPM says no (disk moved to another computer, Secure Boot
#    turned off), the boot asks for the disk password, and the recovery
#    key works there too.
#
# On every install, encrypted or not, the comment on top of /etc/crypttab
# is rewritten in Raye's words.

import os
import re
import secrets
import shlex
import subprocess
import tempfile

import libcalamares

TPM = "/dev/tpmrm0"
# PCR 7 is the Secure Boot state. Most chips only turn on the SHA-256
# bank, which clevis does not pick by default; SHA-1 is kept for the old
# ones that have nothing else.
PCR_CONFIGS = ('{"pcr_bank":"sha256","pcr_ids":"7"}',
               '{"pcr_bank":"sha1","pcr_ids":"7"}')
# What Raye puts on top of /etc/crypttab instead of Calamares' comment.
CRYPTTAB_HEADER = (b"# Encrypted disks Raye opens at startup (see crypttab(5)).\n"
                   b"# Written by the Raye installer.\n")
# Where the first-run welcome and Settings read the key, in the home folder.
KEY_FILE = (".local", "share", "raye", "recovery-key")
USER_NAME = re.compile(r"[a-z_][a-z0-9_.-]{0,31}")
# The first-run welcome shows the key; without it, a one-time message does.
FIRST_RUN = ("usr", "bin", "raye-first-run")
NOTICE = "raye-recovery-key.desktop"
# The script the autostart file runs, next to the key. The session starts
# autostart files through systemd's generator, which does not read Exec=
# escapes the way the desktop entry spec says, so the message lives in
# the script and Exec= only names it.
NOTICE_SCRIPT = KEY_FILE[:-1] + ("recovery-key-notice",)
# Characters that make an Exec argument need quotes (desktop entry spec).
EXEC_RESERVED = set(" \t\n\"'\\><~|&;$*?#()`")
# Written by the setup app; only "lang" is read here.
CHOICES = "/run/raye-setup/choices"
TEXT = {
    "en": {"name": "Setting up disk encryption",
           "failed": "Could not add the recovery key",
           "failed_detail": "The disk is encrypted, but adding the recovery key failed.",
           "tpm": "This computer unlocks its disk by itself.",
           "password": "The disk asks for its password when the computer starts.",
           "notice": ("Your disk is encrypted. {unlocked} If it ever cannot be unlocked, "
                      "this recovery key opens it: {key}. Write it down and keep it "
                      "somewhere other than this computer.")},
    "fr": {"name": "Configuration du chiffrement du disque",
           "failed": "Impossible d'ajouter la clé de récupération",
           "failed_detail": "Le disque est chiffré, mais l'ajout de la clé de récupération a échoué.",
           "tpm": "Cet ordinateur déverrouille son disque tout seul.",
           "password": "Le disque demande son mot de passe au démarrage de l’ordinateur.",
           "notice": ("Votre disque est chiffré. {unlocked} S’il ne peut plus être "
                      "déverrouillé, cette clé de récupération l’ouvre : {key}. "
                      "Notez-la et gardez-la ailleurs que sur cet ordinateur.")},
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


def new_recovery_key():
    # eight groups of six digits: easy to read out loud and to type
    return "-".join(f"{secrets.randbelow(10 ** 6):06d}" for _ in range(8))


def add_recovery_key(device, passphrase, key):
    # the new key goes through a file in /run (tmpfs), never on a disk
    path = "/run/raye-recovery-key"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, key.encode())
    finally:
        os.close(fd)
    try:
        subprocess.run(["cryptsetup", "luksAddKey", "--key-file=-", device, path],
                       input=passphrase.encode(), check=True, capture_output=True)
    finally:
        os.unlink(path)


def bind_tpm(root, device, passphrase):
    """Seal the disk key to the TPM, with the first PCR bank that works."""
    error = None
    for config in PCR_CONFIGS:
        try:
            subprocess.run(["chroot", root, "clevis", "luks", "bind", "-y", "-k", "-",
                            "-d", device, "tpm2", config],
                           input=passphrase.encode(), check=True, capture_output=True)
            return config
        except subprocess.CalledProcessError as e:
            error = e
    raise error


def rewrite_crypttab_header(root):
    """Put Raye's words on top of /etc/crypttab.

    Calamares' fstab job writes a comment block that names another
    system's tools. Only that leading block changes: every line from the
    first entry on is kept byte for byte.
    """
    path = os.path.join(root, "etc", "crypttab")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        # none there, or a link: nothing Calamares wrote
        return
    with os.fdopen(fd, "rb") as f:
        mode = os.fstat(f.fileno()).st_mode & 0o7777
        lines = f.read().splitlines(keepends=True)
    first = 0
    while first < len(lines) and (lines[first].startswith(b"#") or not lines[first].strip()):
        first += 1
    data = CRYPTTAB_HEADER + b"".join(lines[first:])
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".crypttab-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def account(root, username):
    """(uid, gid, home inside root) from the new system's passwd, or None."""
    if not username or not USER_NAME.fullmatch(username):
        return None
    try:
        with open(os.path.join(root, "etc", "passwd")) as f:
            for line in f:
                fields = line.rstrip("\n").split(":")
                if len(fields) >= 7 and fields[0] == username:
                    home = os.path.normpath(fields[5])
                    if not home.startswith("/home/"):
                        return None
                    return int(fields[2]), int(fields[3]), os.path.join(root, home.lstrip("/"))
    except (OSError, ValueError):
        pass
    return None


def save_recovery_key(root, username, key):
    """Keep the key, readable by its owner only, for the first-run welcome.

    It shows the key at first sign-in and asks the person to save it
    somewhere else. Returns the path, or None when there is no home.
    """
    found = account(root, username)
    if not found or not os.path.isdir(found[2]) or os.path.islink(found[2]):
        return None
    uid, gid, folder = found
    for i, part in enumerate(KEY_FILE[:-1]):
        folder = os.path.join(folder, part)
        if os.path.islink(folder):
            raise OSError(f"{folder} is a link")
        if not os.path.isdir(folder):
            last = i == len(KEY_FILE) - 2
            os.mkdir(folder, 0o700 if last else 0o755)
            os.chown(folder, uid, gid)
    os.chmod(folder, 0o700)
    path = os.path.join(folder, KEY_FILE[-1])
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, f"{key}\n".encode())
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    os.chown(path, uid, gid)
    return path


def notice_text(lang, key, tpm_bound):
    text = TEXT.get(lang, TEXT["en"])
    return text["notice"].format(unlocked=text["tpm" if tpm_bound else "password"], key=key)


def desktop_exec(argv):
    """An Exec= value that gives back exactly argv (desktop entry spec)."""
    out = []
    for arg in argv:
        if any(ord(c) < 32 for c in arg):
            raise ValueError("control character in a desktop Exec argument")
        arg = arg.replace("%", "%%")
        if EXEC_RESERVED.intersection(arg) or not arg:
            arg = '"' + "".join("\\" + c if c in '"`$\\' else c for c in arg) + '"'
        out.append(arg)
    # the value is a string too: its backslashes are escaped once more
    return " ".join(out).replace("\\", "\\\\")


def notice_script(title, message, remove):
    """Shows the message once, then removes the files in remove.

    ⚠️ Only once it was really shown. kdialog is not a dependency of the
    installed system -- it arrives behind raye-windows-apps, and both
    debian/control here and raye-base's say it is on its way out. The
    script used to run `exec rm -f` whatever kdialog had done, so the day
    kdialog goes the only message about the recovery key would delete
    itself unseen. set -e stops at the box that did not open, and the
    notice is still there at the next sign-in.
    """
    return ("#!/bin/sh\n"
            "# Shows the disk recovery key once, then removes itself -- but\n"
            "# only once it was really shown (see notice_script).\n"
            "set -e\n"
            f"kdialog --title {shlex.quote(title)} --icon dialog-password "
            f"--msgbox {shlex.quote(message)}\n"
            f"exec rm -f -- {' '.join(shlex.quote(f) for f in remove)}\n")


def write_private(path, text, mode, uid, gid):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, mode)
    try:
        os.write(fd, text.encode())
        os.fchmod(fd, mode)
    finally:
        os.close(fd)
    os.chown(path, uid, gid)


def leave_notice(root, username, key, tpm_bound, lang):
    """Show the key once at first sign-in, on systems without the first-run welcome.

    Returns the path of the autostart file, or None when none is needed.
    """
    if os.path.lexists(os.path.join(root, *FIRST_RUN)):
        return None
    found = account(root, username)
    if not found or not os.path.isdir(found[2]) or os.path.islink(found[2]):
        return None
    uid, gid, home = found
    message = notice_text(lang, key, tpm_bound)
    folders = {}
    for name, parts, last_mode in (("entry", (".config", "autostart"), 0o755),
                                   ("script", NOTICE_SCRIPT[:-1], 0o700)):
        folder = home
        for i, part in enumerate(parts):
            folder = os.path.join(folder, part)
            if os.path.islink(folder):
                raise OSError(f"{folder} is a link")
            if not os.path.isdir(folder):
                os.mkdir(folder, last_mode if i == len(parts) - 1 else 0o755)
                os.chown(folder, uid, gid)
        folders[name] = folder
    path = os.path.join(folders["entry"], NOTICE)
    script = os.path.join(folders["script"], NOTICE_SCRIPT[-1])
    # the same files, as the new system sees them
    in_target = ["/" + os.path.relpath(f, root) for f in (path, script)]
    # both hold the key: owner only
    write_private(script, notice_script("Raye Linux", message, in_target), 0o700, uid, gid)
    entry = ("[Desktop Entry]\nType=Application\nName=Raye recovery key\nNoDisplay=true\n"
             f"Exec={desktop_exec(['/bin/sh', in_target[1]])}\n")
    write_private(path, entry, 0o600, uid, gid)
    return path


def run():
    gs = libcalamares.globalstorage
    root = gs.value("rootMountPoint")
    # Calamares writes /etc/crypttab on every install, encrypted or not
    if root:
        try:
            rewrite_crypttab_header(root)
        except OSError as e:
            # only a comment: never worth failing the install over
            libcalamares.utils.warning(f"encryption: crypttab header left as is: {e}")
    partitions = gs.value("partitions") or []
    encrypted = [p for p in partitions
                 if p.get("luksMapperName") and p.get("luksPassphrase") and p.get("device")]
    if not encrypted:
        return None

    key = new_recovery_key()
    has_tpm = os.path.exists(TPM)
    tpm_bound = False
    for p in encrypted:
        try:
            add_recovery_key(p["device"], p["luksPassphrase"], key)
        except subprocess.CalledProcessError as e:
            libcalamares.utils.warning(f"recovery key on {p['device']}: {e.stderr!r}")
            text = TEXT[chosen_lang()]
            return (text["failed"], text["failed_detail"])
        if has_tpm:
            try:
                bind_tpm(root, p["device"], p["luksPassphrase"])
                tpm_bound = True
            except subprocess.CalledProcessError as e:
                # not fatal: the disk still opens with its password
                libcalamares.utils.warning(f"TPM bind on {p['device']}: {e.stderr!r}")

    if tpm_bound and gs.value("autoLoginUser"):
        # the chip opens the disk on its own: with automatic login on top,
        # a stolen laptop would start straight on its owner's desktop
        gs.remove("autoLoginUser")
        libcalamares.utils.debug("encryption: automatic login turned off, the TPM unlocks the disk")

    try:
        if not save_recovery_key(root, gs.value("username"), key):
            libcalamares.utils.warning("encryption: no home folder to keep the recovery key in")
    except OSError as e:
        libcalamares.utils.warning(f"encryption: recovery key not saved: {e}")
    try:
        if leave_notice(root, gs.value("username"), key, tpm_bound, chosen_lang()):
            libcalamares.utils.debug("encryption: no first-run welcome, key shown at first sign-in")
    except (OSError, ValueError) as e:
        libcalamares.utils.warning(f"encryption: recovery key message not written: {e}")
    libcalamares.utils.debug(f"encryption: recovery key added, TPM bound: {tpm_bound}")
    return None
