# SPDX-License-Identifier: GPL-3.0-or-later
"""What "Replace and keep my files" brings along besides the six folders.

 - the wallpaper, when it is a picture in the person's own folder;
 - the saved Wi-Fi networks (NetworkManager keyfiles, or the netplan files
   NetworkManager writes on systems of Raye's own family);
 - the list of Flatpak apps, installed again from Flathub after the
   first sign-in, the way the Store installs them;
 - the Firefox, Chrome and Chromium profiles: kept folders like the six,
   with the browsers' own lock links taken off afterwards.

Everything here reads the old system; nothing on it is ever written.
"""
import os
import re
import stat
import struct
import uuid as uuidlib
from urllib.parse import unquote, urlparse

import rayedisk_keep as keep

BROWSERS = tuple(keep.PROFILES.items())
# Links the browsers leave while running. Copied from another system they
# say "in use on another computer", and the profile won't open.
BROWSER_LOCKS = {"lock", "SingletonLock", "SingletonCookie", "SingletonSocket"}
PICTURES = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".jxl", ".avif", ".heic", ".svg", ".gif", ".tif", ".tiff")
WALLPAPER_LIMIT = 64 * 1024 * 1024
WINDOWS_WALLPAPER = "AppData/Roaming/Microsoft/Windows/Themes/TranscodedWallpaper"
WINDOWS_WALLPAPER_NAME = {"en": "Windows wallpaper", "fr": "Fond d'écran Windows"}
DCONF_KEYS = ("/org/gnome/desktop/background/picture-uri", "/org/gnome/desktop/background/picture-uri-dark",
              "/org/cinnamon/desktop/background/picture-uri", "/org/mate/desktop/background/picture-filename")
FLATPAK_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*(\.[A-Za-z0-9_-]+){2,}")
CONNECTIONS = "etc/NetworkManager/system-connections"
# keyfile keys that name a file of the old system: such a network can't come along
FILE_KEYS = ("ca-cert", "client-cert", "private-key", "phase2-ca-cert", "phase2-client-cert",
             "phase2-private-key")


# ------------------------------------------------------------------ dconf

def gvdb_strings(data):
    """{key: text} of the string values of a dconf database (GVDB file).

    Text as dconf keeps it: a GVariant string, quotes included. Anything that
    doesn't read as a little-endian GVDB gives {}.
    """
    try:
        if data[:8] != b"GVariant":
            return {}
        start, end = struct.unpack_from("<II", data, 16)
        blooms, buckets = struct.unpack_from("<II", data, start)
        at = start + 8 + 4 * (blooms & 0x07FFFFFF) + 4 * buckets
        items = []
        while at + 24 <= end:
            _, parent, key_at, key_size, kind, v0, v1 = struct.unpack_from("<IIIHcxII", data, at)
            items.append((parent, data[key_at:key_at + key_size].decode("utf-8", "replace"), kind, v0, v1))
            at += 24
    except (struct.error, ValueError):
        return {}

    def full(i, seen=()):
        parent, name = items[i][0], items[i][1]
        if parent == 0xFFFFFFFF or parent >= len(items) or parent in seen:
            return name
        return full(parent, seen + (i,)) + name

    found = {}
    for i, (_, _, kind, v0, v1) in enumerate(items):
        if kind != b"v" or not v0 < v1 <= len(data):
            continue
        value = data[v0:v1]
        cut = value.rfind(b"\0")
        if cut < 0 or value[cut + 1:] != b"s":
            continue
        found[full(i)] = value[:cut].rstrip(b"\0").decode("utf-8", "replace")
    return found


# --------------------------------------------------------------- wallpaper

def _as_path(value):
    value = value.strip().strip("'\"")
    if value.startswith("file://"):
        return unquote(urlparse(value).path)
    return value if value.startswith("/") else ""


def _candidates(home):
    plasma = keep.read_small(os.path.join(home, ".config/plasma-org.kde.plasma.desktop-appletsrc"), 1024 * 1024)
    group = ""
    for line in plasma.splitlines():
        if line.startswith("["):
            group = line
        elif line.startswith("Image=") and "[Wallpaper][org.kde.image]" in group:
            yield line[len("Image="):]
    xfce = keep.read_small(os.path.join(home, ".config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"),
                           1024 * 1024)
    for match in re.finditer(r'name="(?:last-image|image-path)"[^>]*\bvalue="([^"]+)"', xfce):
        yield match.group(1).replace("&amp;", "&").replace("&quot;", '"')
    dconf = _read_bytes(os.path.join(home, ".config/dconf/user"), 8 * 1024 * 1024)
    if dconf:
        values = gvdb_strings(dconf)
        for key in DCONF_KEYS:
            if key in values:
                yield values[key]


def _read_bytes(path, limit):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return b""
    with os.fdopen(fd, "rb") as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            return b""
        return f.read(limit)


def _picture_in(home, relative):
    """relative when it is a picture file inside home, reached without a link."""
    names = keep._clean(relative)
    if names is None or not relative.lower().endswith(PICTURES):
        return None
    folder = keep.real_dir(home, "/".join(names[:-1])) if len(names) > 1 else home
    if folder is None:
        return None
    try:
        info = os.lstat(os.path.join(folder, names[-1]))
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= WALLPAPER_LIMIT:
        return None
    return "/".join(names)


def find_wallpaper(home, old_home):
    """The wallpaper of one account, as a path inside its home, or None.

    home is where the folder is now (mounted), old_home what the old
    system called it (/home/alice): the settings name it that way. A
    picture of the system itself goes with the system.
    """
    prefix = old_home.rstrip("/") + "/"
    for value in _candidates(home):
        path = os.path.normpath(_as_path(value))
        if not path.startswith(prefix):
            continue
        found = _picture_in(home, path[len(prefix):])
        if found:
            return found
    return None


def windows_wallpaper(home):
    """The picture Windows shows on the desktop, inside C:\\Users\\<name>."""
    names = WINDOWS_WALLPAPER.split("/")
    folder = keep.real_dir(home, "/".join(names[:-1]))
    if folder is None:
        return None
    try:
        info = os.lstat(os.path.join(folder, names[-1]))
    except OSError:
        return None
    if stat.S_ISREG(info.st_mode) and 0 < info.st_size <= WALLPAPER_LIMIT:
        return WINDOWS_WALLPAPER
    return None


def _kind_of_picture(path):
    head = _read_bytes(path, 16) if path else b""
    if head.startswith(b"\x89PNG"):
        return ".png"
    if head.startswith(b"BM"):
        return ".bmp"
    return ".jpg"


def wallpaper_inside(user):
    """(kind, path below it) when the account's wallpaper is in one of its
    kept folders and travels with it; None when it has to come on its own."""
    paper = (user.get("wallpaper") or {}).get("path") or ""
    for folder in user["folders"]:
        top = folder["path"].rstrip("/") + "/"
        if folder["kind"] in keep.KINDS and paper.startswith(top):
            return folder["kind"], paper[len(top):]
    return None


def picture_name(name, source, lang):
    """The file name the wallpaper gets in Pictures."""
    if name == os.path.basename(WINDOWS_WALLPAPER):
        return WINDOWS_WALLPAPER_NAME.get(lang, WINDOWS_WALLPAPER_NAME["en"]) + _kind_of_picture(source)
    return name


# ------------------------------------------------------------------ browsers

def browser_folders(home):
    """The browser profiles of one account, as kept folders."""
    found = []
    for kind, path in BROWSERS:
        where = keep.real_dir(home, path)
        if where is None:
            continue
        size = keep.measure(where)
        if size["files"]:
            found.append({"kind": kind, "path": path, "files": size["files"], "bytes": size["bytes"],
                          "unreadable": size["unreadable"]})
    return found


def clear_browser_locks(folder):
    """Takes the browsers' lock links off a kept profile. Returns how many."""
    removed = 0
    for here, dirs, files in os.walk(folder):
        for name in files + dirs:
            path = os.path.join(here, name)
            if name in BROWSER_LOCKS and os.path.islink(path):
                os.unlink(path)
                removed += 1
    return removed


# ------------------------------------------------------------------- Wi-Fi

def _sections(text):
    """[(section, [(key, value)])] of a keyfile, order kept."""
    sections = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            sections.append((stripped[1:-1], []))
        elif "=" in line and sections and not stripped.startswith("#"):
            key, _, value = line.partition("=")
            sections[-1][1].append((key.strip(), value))
    return sections


def _get(sections, section, key):
    for name, entries in sections:
        if name == section:
            for k, v in entries:
                if k == key:
                    return v
    return ""


def _ssid_text(value):
    """ssid= as NetworkManager writes it: text, or bytes as "77;65;"."""
    if re.fullmatch(r"(\d{1,3};)+\d{0,3}", value):
        try:
            return bytes(int(b) for b in value.split(";") if b).decode("utf-8", "replace")
        except ValueError:
            return value
    return value.replace("\\s", " ").replace("\\\\", "\\")


def _render(sections):
    out = []
    for name, entries in sections:
        if out:
            out.append("")
        out.append(f"[{name}]")
        out += [f"{k}={v}" for k, v in entries]
    return "\n".join(out) + "\n"


def wifi_from_keyfile(text):
    """{name, ssid, uuid, text} of a saved Wi-Fi network, None for anything else.

    The old accounts' names go (permissions=): the network is the PC's."""
    sections = _sections(text)
    if _get(sections, "connection", "type") not in ("wifi", "802-11-wireless"):
        return None
    if any(k in FILE_KEYS and v and not v.startswith("data:")
           for name, entries in sections if name == "802-1x" for k, v in entries):
        return None
    ssid = _ssid_text(_get(sections, "wifi", "ssid") or _get(sections, "802-11-wireless", "ssid"))
    if not ssid:
        return None
    cleaned = [(name, [(k, v) for k, v in entries if not (name == "connection" and k == "permissions")])
               for name, entries in sections]
    return {"name": _get(sections, "connection", "id") or ssid, "ssid": ssid,
            "uuid": _get(sections, "connection", "uuid"), "text": _render(cleaned)}


def _escape(value):
    value = str(value).replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    return "\\s" + value[1:] if value.startswith(" ") else value


def wifi_from_netplan(text):
    """The Wi-Fi networks of a netplan file NetworkManager wrote, as keyfiles."""
    try:
        import yaml
        data = yaml.safe_load(text)
    except Exception:  # noqa: BLE001 - no yaml module or a file we can't read: nothing
        return []
    wifis = ((data or {}).get("network") or {}).get("wifis") if isinstance(data, dict) else None
    found = []
    for device in (wifis or {}).values():
        if not isinstance(device, dict):
            continue
        for ssid, point in (device.get("access-points") or {}).items():
            point = point if isinstance(point, dict) else {}
            auth = point.get("auth") if isinstance(point.get("auth"), dict) else {}
            manager = point.get("networkmanager") if isinstance(point.get("networkmanager"), dict) else {}
            method = str(auth.get("key-management", "none"))
            if method not in ("none", "psk", "sae") or not str(ssid):
                continue
            sections = [("connection", [("id", _escape(manager.get("name") or ssid)),
                                        ("uuid", str(manager.get("uuid") or uuidlib.uuid4())),
                                        ("type", "wifi")]),
                        ("wifi", [("mode", "infrastructure"), ("ssid", _escape(ssid))])]
            if point.get("hidden"):
                sections[1][1].append(("hidden", "true"))
            if method != "none":
                sections.append(("wifi-security", [("key-mgmt", "wpa-psk" if method == "psk" else "sae"),
                                                   ("psk", _escape(auth.get("password", "")))]))
            sections += [("ipv4", [("method", "auto")]), ("ipv6", [("method", "auto")])]
            for dotted, value in (manager.get("passthrough") or {}).items():
                section, _, key = str(dotted).partition(".")
                if not key or (section, key) == ("connection", "permissions") or key in FILE_KEYS:
                    continue
                group = next((s for s in sections if s[0] == section), None)
                if group is None:
                    group = (section, [])
                    sections.append(group)
                group[1][:] = [(k, v) for k, v in group[1] if k != key] + [(key, _escape(value))]
            found.append(wifi_from_keyfile(_render(sections)))
    return [f for f in found if f]


def _files_in(folder, suffixes=None):
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    return [os.path.join(folder, n) for n in names
            if suffixes is None or n.endswith(suffixes)]


def wifi_connections(root):
    """Every saved Wi-Fi network of a Linux whose / is root."""
    found, seen = [], set()
    for path in _files_in(os.path.join(root, CONNECTIONS)):
        entry = wifi_from_keyfile(keep.read_small(path, 256 * 1024))
        if entry and (entry["uuid"], entry["ssid"]) not in seen:
            seen.add((entry["uuid"], entry["ssid"]))
            found.append(entry)
    for path in _files_in(os.path.join(root, "etc/netplan"), (".yaml", ".yml")):
        for entry in wifi_from_netplan(keep.read_small(path, 256 * 1024)):
            if (entry["uuid"], entry["ssid"]) not in seen:
                seen.add((entry["uuid"], entry["ssid"]))
                found.append(entry)
    return found


def wifi_names(root):
    """What the page may show: the names of the networks, never their keys."""
    return sorted({c["ssid"] for c in wifi_connections(root)})


def _file_name(name):
    name = "".join(c if c.isprintable() and c != "/" else "_" for c in os.path.basename(name or "")).strip(". ")
    return (name or "Wi-Fi")[:100]


def install_wifi(root, connections, live="/", owner=None):
    """The networks into the new system, root's alone. Returns the names written.

    One the new system or the live session already knows (same name or
    same uuid) is left: Setup copies the live session's own over it."""
    folder = os.path.join(root, CONNECTIONS)
    known = wifi_connections(root) + wifi_connections(live)
    ssids = {c["ssid"] for c in known}
    uuids = {c["uuid"] for c in known if c["uuid"]}
    os.makedirs(folder, mode=0o755, exist_ok=True)
    written = []
    for connection in connections:
        if connection["ssid"] in ssids or (connection.get("uuid") and connection["uuid"] in uuids):
            continue
        name = keep.free_name(folder, _file_name(connection["name"]) + ".nmconnection")
        path = os.path.join(folder, name)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(connection["text"])
            f.flush()
            os.fsync(f.fileno())
        if owner is not None:
            os.chown(path, owner[0], owner[1])
        ssids.add(connection["ssid"])
        written.append(connection["ssid"])
    return written


# ----------------------------------------------------------------- flatpak

def flatpak_apps(root, homes):
    """The Flatpak apps of the old system: system-wide and each account's."""
    found = set()
    for folder in [os.path.join(root, "var/lib/flatpak/app")] + \
            [os.path.join(h, ".local/share/flatpak/app") for h in homes]:
        for path in _files_in(folder):
            name = os.path.basename(path)
            if FLATPAK_ID.fullmatch(name) and os.path.isdir(path) and not os.path.islink(path):
                found.add(name)
    return sorted(found)


# ------------------------------------------------------------ first sign-in

WELCOME_BACK = ("autostart", "raye-welcome-back.desktop")
WORDS = {
    "en": {"title": "Your apps are back",
           "back": "Apps from your old system installed again: %s.",
           "missing": "Not in the Store: %s."},
    "fr": {"title": "Vos applis sont de retour",
           "back": "Applis de votre ancien système réinstallées\u00a0: %s.",
           "missing": "Absentes de la boutique\u00a0: %s."},
}
SCRIPT = r"""#!/bin/sh
# After the first sign-in: what Raye kept from the system it replaced,
# besides the files. The wallpaper, then the apps, installed again from
# Flathub the way the Store does. Without a network it waits for the next
# sign-in; once done it takes itself away.
here="$HOME/.local/share/raye"
entry="$HOME/.config/autostart/raye-welcome-back.desktop"
if [ -f "$here/kept-wallpaper" ]; then
    picture=$(head -n 1 "$here/kept-wallpaper")
    if command -v plasma-apply-wallpaperimage >/dev/null; then
        tries=0
        while [ "$tries" -lt 10 ]; do
            plasma-apply-wallpaperimage "$picture" >/dev/null 2>&1 && break
            tries=$((tries + 1))
            sleep 3
        done
    fi
    rm -f "$here/kept-wallpaper"
fi
if [ -s "$here/kept-apps" ] && command -v flatpak >/dev/null; then
    if command -v nm-online >/dev/null && ! nm-online -q -t 600; then
        exit 0
    fi
    # the Store's own way for an administrator, the account's own otherwise
    where=--user
    case " $(id -nG) " in *" sudo "*) where=--system ;; esac
    back=0
    missing=0
    while read -r app; do
        case $app in ""|*[!A-Za-z0-9._-]*) continue ;; esac
        if flatpak info "$where" "$app" >/dev/null 2>&1 ||
            flatpak install "$where" -y --noninteractive flathub "$app" >/dev/null 2>&1; then
            back=$((back + 1))
        else
            missing=$((missing + 1))
        fi
    done < "$here/kept-apps"
    rm -f "$here/kept-apps"
    text=$(printf "$BACK" "$back")
    [ "$missing" -gt 0 ] && text="$text $(printf "$MISSING" "$missing")"
    if [ "$back" -gt 0 ] || [ "$missing" -gt 0 ]; then
        notify-send --app-name=org.raye.store --icon=org.raye.store "$TITLE" "$text" 2>/dev/null
    fi
fi
rm -f "$entry" "$0"
"""


def _sh_quote(text):
    return "'" + text.replace("'", "'\\''") + "'"


def welcome_back_script(lang):
    words = WORDS.get(lang, WORDS["en"])
    head = "".join(f"{key}={_sh_quote(words[name])}\n"
                   for key, name in (("TITLE", "title"), ("BACK", "back"), ("MISSING", "missing")))
    first, rest = SCRIPT.split("\n", 1)
    return first + "\n" + head + rest


def _folder(base, parts, owner):
    folder = base
    for part in parts:
        folder = os.path.join(folder, part)
        if os.path.islink(folder):
            raise OSError(f"{folder} is a link")
        if not os.path.isdir(folder):
            os.mkdir(folder, 0o755)
            if owner is not None:
                os.chown(folder, owner[0], owner[1])
    return folder


def _write(path, text, mode, owner):
    if os.path.lexists(path):
        os.unlink(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    if owner is not None:
        os.chown(path, owner[0], owner[1])


def leave_welcome_back(root, home, owner, lang, wallpaper="", apps=()):
    """The first sign-in's one-shot: wallpaper set, apps installed again.

    wallpaper is the picture's path in the new system. Returns the path of
    the autostart entry, None when there is nothing to do."""
    apps = [a for a in apps if FLATPAK_ID.fullmatch(a)]
    if not wallpaper and not apps:
        return None
    data = _folder(home, (".local", "share", "raye"), owner)
    if wallpaper:
        _write(os.path.join(data, "kept-wallpaper"), wallpaper + "\n", 0o644, owner)
    if apps:
        _write(os.path.join(data, "kept-apps"), "\n".join(apps) + "\n", 0o644, owner)
    script = os.path.join(data, "welcome-back")
    _write(script, welcome_back_script(lang), 0o755, owner)
    autostart = _folder(home, (".config", WELCOME_BACK[0]), owner)
    entry = os.path.join(autostart, WELCOME_BACK[1])
    in_target = "/" + os.path.relpath(script, root)
    _write(entry, "[Desktop Entry]\nType=Application\nName=Raye welcome back\nNoDisplay=true\n"
                  "OnlyShowIn=KDE;\nX-KDE-autostart-phase=2\n"
                  f"Exec=/bin/sh {in_target}\n", 0o644, owner)
    return entry
