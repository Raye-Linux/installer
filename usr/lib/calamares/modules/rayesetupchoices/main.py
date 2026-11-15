#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Carries what the person chose in Raye Setup to the new system.
#
#  - keyboard: /etc/default/keyboard (console, disk password prompt at
#    boot, sign-in screen) and the person's own kxkbrc for the desktop,
#    with the second layout of the keyboard page when there is one.
#  - clock: when Windows is on the disk, the hardware clock keeps local
#    time like Windows does, so Windows' clock is right after Raye ran.
#  - the password hint, for the sign-in screen (AccountsService).
#  - the privacy page's switches, written where Settings keeps them.
#  - the wish to sign in to a Raye account after setup (preview only).
#  - for a language the image does not carry (only English and French
#    do), a one-shot unit that fetches its language support the first time
#    the new system is online. Calamares' packages step tries the language
#    pack during the install already; this covers installs made offline.
#
# /run/raye-setup/choices, when something writes it before Calamares
# starts: key=value lines, lang, locale, layout, variant, region, windows.
# The Setup pages leave their answers next to it, one file each
# (answer-second-layout, answer-password-hint, answer-privacy,
# answer-account): Calamares' GlobalStorage is read-only from QML.
#
# This job has to run after `hwclock` (which sets the clock to UTC), so
# also after `users`, and before `initramfs`.

import os
import re
import tempfile

import libcalamares

CHOICES = "/run/raye-setup/choices"
ANSWERS = "/run/raye-setup"
# Owner's decision (2026-10-30): local time when Windows is found.
RTC_LOCAL_WITH_WINDOWS = True

# xkb layout and variant names: letters, digits, "_" and "-", nothing
# that could end a quoted value or a line.
XKB_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")
USER_NAME = re.compile(r"[a-z_][a-z0-9_.-]{0,31}")
ANSWER_NAME = re.compile(r"[a-z-]{1,32}")
HINT_LENGTH = 120
# the same keys and values Settings writes (settings: backends/indexing.cpp,
# backends/permissions.cpp)
FEEDBACK_BASIC_USAGE = 32
REMEMBER_NOTHING = 2
WINDOWS_BOOT = ("EFI", "Microsoft", "Boot", "bootmgfw.efi")

DEFAULT_KEYBOARD = (
    "# KEYBOARD CONFIGURATION FILE\n"
    "\n"
    "# Consult the keyboard(5) manual page.\n"
    "\n"
    'XKBMODEL="pc105"\n'
    'XKBLAYOUT="{layout}"\n'
    'XKBVARIANT="{variant}"\n'
    'XKBOPTIONS=""\n'
    "\n"
    'BACKSPACE="guess"\n'
)

NAMES = {
    "en": "Setting up the keyboard and clock",
    "fr": "Configuration du clavier et de l'horloge",
}


def pretty_name():
    return NAMES.get(read_choices(CHOICES).get("lang"), NAMES["en"])


def read_choices(path):
    """The choices file as a dict; empty when it is missing or unreadable."""
    choices = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read(64 * 1024).splitlines()
    except OSError:
        return choices
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        choices[key.strip()] = value
    return choices


def read_answer(name):
    """What a Setup page left for the install, "" when nothing."""
    if not ANSWER_NAME.fullmatch(name):
        return ""
    try:
        with open(os.path.join(ANSWERS, "answer-" + name), encoding="utf-8", errors="replace") as f:
            return f.read(4096).strip()
    except OSError:
        return ""


def clean_hint(text):
    """One line of printable text, short enough for the sign-in screen."""
    text = "".join(c if c.isprintable() else " " for c in text)
    return " ".join(text.split())[:HINT_LENGTH]


def parse_privacy(text):
    """{"location": bool, ...} from "location=1 diagnostics=0 history=1"."""
    found = {}
    for word in text.split():
        key, _, value = word.partition("=")
        if key in ("location", "diagnostics", "history") and value in ("0", "1"):
            found[key] = value == "1"
    return found


def clean_layout(layout, variant):
    """(layout, variant) safe to write; layout None when it cannot be used."""
    if not layout or not XKB_NAME.fullmatch(layout):
        return None, ""
    return layout, variant if variant and XKB_NAME.fullmatch(variant) else ""


def atomic_write(path, data, mode):
    """Replace path in one step, never following a link at the end of it."""
    folder = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".raye-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_default_keyboard(root, layout, variant):
    """Set XKBLAYOUT and XKBVARIANT, every other line stays as it was."""
    path = os.path.join(root, "etc", "default", "keyboard")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "rb") as f:
            lines = f.read().splitlines(keepends=True)
    except FileNotFoundError:
        text = DEFAULT_KEYBOARD.format(layout=layout, variant=variant)
        atomic_write(path, text.encode(), 0o644)
        return

    wanted = {b"XKBLAYOUT": f'XKBLAYOUT="{layout}"'.encode(),
              b"XKBVARIANT": f'XKBVARIANT="{variant}"'.encode()}
    done = set()
    out = []
    for line in lines:
        key = line.split(b"=", 1)[0].strip()
        if b"=" in line and key in wanted and not line.lstrip().startswith(b"#"):
            ending = line[len(line.rstrip(b"\r\n")):] or b"\n"
            out.append(wanted[key] + ending)
            done.add(key)
        else:
            out.append(line)
    if out and not out[-1].endswith(b"\n"):
        out[-1] += b"\n"
    for key in (b"XKBLAYOUT", b"XKBVARIANT"):
        if key not in done:
            out.append(wanted[key] + b"\n")
    atomic_write(path, b"".join(out), 0o644)


def account(root, username):
    """(uid, gid, home inside root) from the new system's passwd, or None."""
    try:
        with open(os.path.join(root, "etc", "passwd")) as f:
            for line in f:
                fields = line.rstrip("\n").split(":")
                if len(fields) >= 7 and fields[0] == username:
                    home = os.path.normpath(fields[5])
                    if not home.startswith("/home/") and home != "/root":
                        return None
                    return int(fields[2]), int(fields[3]), os.path.join(root, home.lstrip("/"))
    except (OSError, ValueError):
        pass
    return None


def make_dir(path, owner):
    """mkdir that refuses links; the new folder is given to owner."""
    if os.path.islink(path):
        raise OSError(f"{path} is a link")
    if not os.path.isdir(path):
        os.mkdir(path, 0o755)
        if owner:
            os.chown(path, *owner)


def config_folder(root, username):
    """(~/.config of the new account, its owner), or /etc/skel/.config and
    None when the account is not made yet. None when the name is odd."""
    if not username or not USER_NAME.fullmatch(username):
        return None
    found = account(root, username)
    if found and os.path.isdir(found[2]) and not os.path.islink(found[2]):
        uid, gid, home = found
        owner = (uid, gid)
        config = os.path.join(home, ".config")
    else:
        owner = None
        skel = os.path.join(root, "etc", "skel")
        make_dir(skel, None)
        config = os.path.join(skel, ".config")
    make_dir(config, owner)
    return config, owner


def write_kxkbrc(root, username, layout, variant, second=None):
    """The desktop's keyboard layout for the new account, and the second
    layout after it when there is one.

    When the account is not made yet, the file goes to /etc/skel, which
    the account gets a copy of. Returns the path written, or None.
    """
    where = config_folder(root, username)
    if not where:
        return None
    config, owner = where
    if second and second != layout:
        layout, variant = f"{layout},{second}", f"{variant},"
    text = f"[Layout]\nLayoutList={layout}\nUse=true\nVariantList={variant}\n"

    path = os.path.join(config, "kxkbrc")
    if os.path.islink(path):
        raise OSError(f"{path} is a link")
    atomic_write(path, text.encode(), 0o644)
    if owner:
        os.chown(path, *owner)
    return path


def set_ini(path, group, key, value, owner):
    """key=value in [group] of a KDE config file; every other line stays."""
    if os.path.islink(path):
        raise OSError(f"{path} is a link")
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []
    header = f"[{group}]"
    entry = f"{key}={value}"
    if header not in lines:
        if lines and lines[-1].strip():
            lines.append("")
        lines += [header, entry]
    else:
        at = lines.index(header) + 1
        end = at
        while end < len(lines) and not lines[end].startswith("["):
            end += 1
        for i in range(at, end):
            if lines[i].split("=", 1)[0].strip() == key:
                lines[i] = entry
                break
        else:
            # after the group's last entry, before the blank line that ends it
            while end > at and not lines[end - 1].strip():
                end -= 1
            lines.insert(end, entry)
    atomic_write(path, ("\n".join(lines) + "\n").encode(), 0o644)
    if owner:
        os.chown(path, *owner)


def write_privacy(root, username, choices):
    """Only what differs from Raye's defaults: location on, usage
    statistics off, activity history on."""
    where = config_folder(root, username)
    if not where:
        return
    config, owner = where
    if choices.get("location") is False:
        set_ini(os.path.join(config, "raye-settingsrc"), "Privacy", "LocationAccess", "false", owner)
    if choices.get("diagnostics") is True:
        set_ini(os.path.join(config, "PlasmaUserFeedback"), "Global", "FeedbackLevel",
                str(FEEDBACK_BASIC_USAGE), owner)
    if choices.get("history") is False:
        set_ini(os.path.join(config, "kactivitymanagerd-pluginsrc"),
                "Plugin-org.kde.ActivityManager.Resources.Scoring", "what-to-remember",
                str(REMEMBER_NOTHING), owner)
        set_ini(os.path.join(config, "kdeglobals"), "RecentDocuments", "UseRecent", "false", owner)


def write_password_hint(root, username, hint):
    """The hint the sign-in screen offers, kept by AccountsService."""
    if not username or not USER_NAME.fullmatch(username) or not hint:
        return
    folder = os.path.join(root, "var", "lib", "AccountsService", "users")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    path = os.path.join(folder, username)
    set_ini(path, "User", "PasswordHint", hint, None)
    os.chmod(path, 0o600)


def write_account_wish(root, username):
    """Sign in to a Raye account after setup: a note for the account
    pages of the new system, nothing is sent from here."""
    where = config_folder(root, username)
    if where:
        config, owner = where
        set_ini(os.path.join(config, "raye-account-setuprc"), "Setup", "SignIn", "pending", owner)


# languages whose support is in the image (language-pack-*, kde, hunspell)
IMAGE_LANGUAGES = ("en", "fr")
LANG_VALUE = re.compile(r"([a-z]{2,3})(?:_([A-Z]{2}))?(?:\.[A-Za-z0-9-]+)?(?:@[a-z]+)?")
LANGUAGE_UNIT = """[Unit]
Description=Language support for the language chosen in Raye Setup
Documentation=man:check-language-support(1)
Wants=network-online.target
After=network-online.target
ConditionPathExists=/var/lib/raye/language-pack-pending

[Service]
Type=oneshot
Nice=10
# systemd would read $name itself: $$ hands a plain $ to the shell
ExecStart=/bin/sh -ec 'code=$$(cat /var/lib/raye/language-pack-pending); \\
    apt-get update -q; \\
    apt-get install -y -q $$(check-language-support -l "$$code"); \\
    rm -f /var/lib/raye/language-pack-pending'
Restart=on-failure
RestartSec=15min

[Install]
WantedBy=multi-user.target
"""


def language_code(lang):
    """What check-language-support calls the language of LANG, or None."""
    match = LANG_VALUE.fullmatch(lang or "")
    if not match:
        return None
    language, country = match.group(1), match.group(2)
    if language == "zh":
        return "zh-hant" if country in ("TW", "HK", "MO") else "zh-hans"
    return language


def queue_language_pack(root, lang):
    """Leave the unit and its note for a language the image lacks.
    True when something was queued."""
    code = language_code(lang)
    if not code or code in IMAGE_LANGUAGES:
        return False
    state = os.path.join(root, "var", "lib", "raye")
    os.makedirs(state, exist_ok=True)
    atomic_write(os.path.join(state, "language-pack-pending"), f"{code}\n".encode(), 0o644)
    units = os.path.join(root, "etc", "systemd", "system")
    wants = os.path.join(units, "multi-user.target.wants")
    os.makedirs(wants, exist_ok=True)
    atomic_write(os.path.join(units, "raye-language-pack.service"), LANGUAGE_UNIT.encode(), 0o644)
    link = os.path.join(wants, "raye-language-pack.service")
    if os.path.lexists(link):
        os.unlink(link)
    os.symlink("/etc/systemd/system/raye-language-pack.service", link)
    return True


def windows_found(choices, root, esp):
    """Windows on this PC: the setup app says so; when it says nothing,
    Windows' boot manager on the new system's EFI partition."""
    answer = choices.get("windows", "").lower()
    if answer in ("yes", "no"):
        return answer == "yes"
    esp = os.path.join(root, (esp or "/boot/efi").lstrip("/"))
    return os.path.isfile(os.path.join(esp, *WINDOWS_BOOT))


def set_rtc_local(root, target_call):
    """Hardware clock in local time, and /etc/adjtime saying so."""
    if target_call(["hwclock", "--systohc", "--localtime"]) != 0:
        # no RTC the system can reach (some VMs): the file is still right
        libcalamares.utils.debug("setupchoices: hwclock --localtime failed")
    path = os.path.join(root, "etc", "adjtime")
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []
    # adjtime(5): drift line, calibration time, then UTC or LOCAL
    lines += ["0.0 0 0.0", "0", "LOCAL"][len(lines):]
    lines[2] = "LOCAL"
    atomic_write(path, ("\n".join(lines) + "\n").encode(), 0o644)


def run():
    gs = libcalamares.globalstorage
    root = gs.value("rootMountPoint")
    if not root:
        return None
    choices = read_choices(CHOICES)
    if not choices:
        libcalamares.utils.warning(f"setupchoices: no choices in {CHOICES}")

    layout, variant = clean_layout(choices.get("layout"), choices.get("variant"))
    if not layout and "layout" not in choices:
        # started without the setup app: Calamares' own keyboard page, if any
        layout, variant = clean_layout(gs.value("keyboardLayout"), gs.value("keyboardVariant"))
    second, _ = clean_layout(read_answer("second-layout"), "")
    username = gs.value("username")
    if layout:
        write_default_keyboard(root, layout, variant)
        try:
            where = write_kxkbrc(root, username, layout, variant, second)
            libcalamares.utils.debug(f"setupchoices: kxkbrc in {where}")
        except OSError as e:
            libcalamares.utils.warning(f"setupchoices: kxkbrc not written: {e}")
    else:
        libcalamares.utils.warning("setupchoices: no usable keyboard layout, left as is")

    if RTC_LOCAL_WITH_WINDOWS and windows_found(choices, root, gs.value("efiSystemPartition")):
        set_rtc_local(root, libcalamares.utils.target_env_call)
        libcalamares.utils.debug("setupchoices: Windows found, clock in local time")

    try:
        locale_conf = gs.value("localeConf") or {}
        if queue_language_pack(root, locale_conf.get("LANG", "")):
            libcalamares.utils.debug("setupchoices: language support queued for the first online boot")
    except OSError as e:
        libcalamares.utils.warning(f"setupchoices: language support not queued: {e}")

    try:
        write_password_hint(root, username, clean_hint(read_answer("password-hint")))
        write_privacy(root, username, parse_privacy(read_answer("privacy")))
        if read_answer("account") == "signin":
            write_account_wish(root, username)
    except OSError as e:
        libcalamares.utils.warning(f"setupchoices: account settings not written: {e}")
    return None
