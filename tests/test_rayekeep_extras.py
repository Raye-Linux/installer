# SPDX-License-Identifier: GPL-3.0-or-later
"""What "Replace and keep my files" brings along besides the six folders:
the wallpaper, saved Wi-Fi networks, the Flatpak apps and the browser
profiles. Real folders under tmp_path stand for the mounted old system."""
import json
import os
import pathlib
import struct
import subprocess
import sys

import pytest

FOLDER = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedisk"
sys.path.insert(0, str(FOLDER))
import rayedisk_extras as extras  # noqa: E402
import rayedisk_keep as keep  # noqa: E402


def write(path, text="x", mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text)
    if mode is not None:
        path.chmod(mode)
    return path


# ------------------------------------------------------------ dconf (GVDB)

def gvdb(values):
    """A dconf database the way dconf writes it: keys hang from their parent
    folder ("/org/", "/org/gnome/"...), values are variants."""
    items = []          # (key bytes, parent, type, value bytes)
    index = {}

    def folder(path):
        if path in index:
            return index[path]
        parent = 0xFFFFFFFF
        cut = path.rstrip("/").rfind("/")
        own = path
        if cut > 0:
            parent = folder(path[:cut + 1])
            own = path[cut + 1:]
        items.append((own.encode(), parent, b"L", b""))
        index[path] = len(items) - 1
        return index[path]

    for key, text in values.items():
        cut = key.rfind("/")
        parent = folder(key[:cut + 1])
        items.append((key[cut + 1:].encode(), parent, b"v", text.encode() + b"\0\0s"))
    header = 24
    table_head = 8 + 4          # bloom count, bucket count, one bucket
    table_len = table_head + 24 * len(items)
    blobs = b""
    offsets = []
    start = header + table_len
    for key, _, _, value in items:
        key_at = start + len(blobs)
        blobs += key
        value_at = start + len(blobs)
        blobs += value
        offsets.append((key_at, value_at, value_at + len(value)))
    table = struct.pack("<II", 0, 1) + struct.pack("<I", 0)
    for (key, parent, kind, value), (key_at, v0, v1) in zip(items, offsets):
        table += struct.pack("<IIIHcxII", 0, parent, key_at, len(key), kind, v0 if value else 0, v1 if value else 0)
    head = b"GVariant" + struct.pack("<II", 0, 0) + struct.pack("<II", header, header + table_len)
    return head + table + blobs


def test_dconf_values_are_read_with_their_folders():
    data = gvdb({"/org/gnome/desktop/background/picture-uri": "'file:///home/alice/Pictures/sea.jpg'",
                 "/org/gnome/desktop/interface/clock-format": "'24h'"})
    found = extras.gvdb_strings(data)
    assert found["/org/gnome/desktop/background/picture-uri"] == "'file:///home/alice/Pictures/sea.jpg'"
    assert found["/org/gnome/desktop/interface/clock-format"] == "'24h'"


@pytest.mark.parametrize("data", [b"", b"GVariant" + b"\0" * 8, b"not a database at all", os.urandom(300)])
def test_dconf_garbage_reads_as_nothing(data):
    assert extras.gvdb_strings(data) == {}


# --------------------------------------------------------------- wallpaper

def old_home(tmp_path, name="alice"):
    return tmp_path / "home" / name


@pytest.mark.parametrize("value", ["file:///home/alice/Pictures/My%20sea.jpg", "/home/alice/Pictures/My sea.jpg"])
def test_plasma_wallpaper(tmp_path, value):
    home = old_home(tmp_path)
    write(home / "Pictures/My sea.jpg", b"\xff\xd8\xff" + b"x" * 100)
    write(home / ".config/plasma-org.kde.plasma.desktop-appletsrc",
          "[Containments][1]\nplugin=org.kde.plasma.folder\n\n"
          "[Containments][1][Wallpaper][org.kde.image][General]\n"
          f"Image={value}\nSlidePaths=/usr/share/wallpapers/\n")
    assert extras.find_wallpaper(str(home), "/home/alice") == "Pictures/My sea.jpg"


def test_gnome_wallpaper_from_dconf(tmp_path):
    home = old_home(tmp_path)
    write(home / ".local/share/backgrounds/2026-01-01-sea.png", b"\x89PNG" + b"x" * 50)
    write(home / ".config/dconf/user", gvdb({
        "/org/gnome/desktop/background/picture-uri": "'file:///home/alice/.local/share/backgrounds/2026-01-01-sea.png'"}))
    assert extras.find_wallpaper(str(home), "/home/alice") == ".local/share/backgrounds/2026-01-01-sea.png"


def test_xfce_wallpaper(tmp_path):
    home = old_home(tmp_path)
    write(home / "Images/lac.webp", b"RIFF" + b"x" * 40)
    write(home / ".config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml",
          '<channel name="xfce4-desktop">\n<property name="last-image" type="string" '
          'value="/home/alice/Images/lac.webp"/>\n</channel>\n')
    assert extras.find_wallpaper(str(home), "/home/alice") == "Images/lac.webp"


@pytest.mark.parametrize("value", [
    "file:///usr/share/backgrounds/stock.jpg",      # the old system's own picture: it goes with it
    "file:///home/alice/../../etc/shadow",
    "file:///home/alice/notes.txt",
    "file:///home/alice/missing.jpg",
    "file:///home/bob/Pictures/his.jpg",
])
def test_wallpaper_outside_the_home_or_not_a_picture_is_left(tmp_path, value):
    home = old_home(tmp_path)
    write(home / "notes.txt", "hi")
    write(tmp_path / "home/bob/Pictures/his.jpg", "x")
    write(home / ".config/plasma-org.kde.plasma.desktop-appletsrc",
          f"[Containments][1][Wallpaper][org.kde.image][General]\nImage={value}\n")
    assert extras.find_wallpaper(str(home), "/home/alice") is None


def test_wallpaper_through_a_link_is_left(tmp_path):
    home = old_home(tmp_path)
    write(tmp_path / "elsewhere/x.jpg", "x")
    (home / "Pictures").mkdir(parents=True)
    (home / "Pictures/x.jpg").symlink_to(tmp_path / "elsewhere/x.jpg")
    write(home / ".config/plasma-org.kde.plasma.desktop-appletsrc",
          "[Containments][1][Wallpaper][org.kde.image][General]\nImage=file:///home/alice/Pictures/x.jpg\n")
    assert extras.find_wallpaper(str(home), "/home/alice") is None


def test_windows_wallpaper(tmp_path):
    home = tmp_path / "Users/Ana"
    write(home / "AppData/Roaming/Microsoft/Windows/Themes/TranscodedWallpaper", b"\xff\xd8\xff" + b"y" * 20)
    assert extras.windows_wallpaper(str(home)) == "AppData/Roaming/Microsoft/Windows/Themes/TranscodedWallpaper"
    assert extras.picture_name("TranscodedWallpaper", str(home / extras.WINDOWS_WALLPAPER), "fr") \
        == "Fond d'écran Windows.jpg"
    assert extras.picture_name("TranscodedWallpaper", str(home / extras.WINDOWS_WALLPAPER), "en") \
        == "Windows wallpaper.jpg"
    assert extras.picture_name("sea.png", "", "en") == "sea.png"


# ------------------------------------------------------------------ browsers

def test_browser_profiles_are_kept_folders(tmp_path):
    home = old_home(tmp_path)
    write(home / ".mozilla/firefox/profiles.ini", "[Profile0]\nPath=ab.default-release\nIsRelative=1\n")
    write(home / ".mozilla/firefox/ab.default-release/places.sqlite", "p" * 100)
    write(home / ".config/google-chrome/Default/Bookmarks", "{}")
    (home / ".config/chromium").mkdir(parents=True)          # empty: nothing to keep
    found = extras.browser_folders(str(home))
    assert [(f["kind"], f["path"], f["files"]) for f in found] == [
        ("firefox", ".mozilla/firefox", 2), ("chrome", ".config/google-chrome", 1)]
    assert found[0]["bytes"] == len("[Profile0]\nPath=ab.default-release\nIsRelative=1\n") + 100


def test_profiles_land_where_the_browsers_look():
    assert keep.destination("fr", "firefox", "alice", True) == ".mozilla/firefox"
    assert keep.destination("en", "chrome", "alice", False) == ".config/google-chrome"
    assert keep.destination("fr", "documents", "alice", True) == "Documents/alice"


def test_stale_locks_are_cleared_and_only_them(tmp_path):
    profile = tmp_path / ".mozilla/firefox/ab.default"
    write(profile / "places.sqlite", "p")
    write(profile / ".parentlock", "")
    (profile / "lock").symlink_to("127.0.1.1:+4242")
    chrome = tmp_path / ".config/google-chrome"
    chrome.mkdir(parents=True)
    (chrome / "SingletonLock").symlink_to("oldpc-4242")
    (chrome / "SingletonCookie").symlink_to("123")
    write(chrome / "Default/lock", "a real file a person could have named lock")
    removed = extras.clear_browser_locks(str(tmp_path / ".mozilla/firefox")) + \
        extras.clear_browser_locks(str(chrome))
    assert removed == 3
    assert not os.path.lexists(profile / "lock") and not os.path.lexists(chrome / "SingletonLock")
    assert (profile / "places.sqlite").exists() and (profile / ".parentlock").exists()
    assert (chrome / "Default/lock").exists()


# ------------------------------------------------------------------- Wi-Fi

HOME_WIFI = """[connection]
id=Maison
uuid=6b1c2c1c-6c3f-4a39-9a77-2b7c7ad4f1a1
type=wifi
permissions=user:alice:;
interface-name=wlp2s0

[wifi]
mode=infrastructure
ssid=Maison

[wifi-security]
key-mgmt=wpa-psk
psk=un mot de passe

[ipv4]
method=auto
"""
WIRED = "[connection]\nid=Wired\nuuid=1\ntype=ethernet\n"
EAP = ("[connection]\nid=Work\nuuid=2\ntype=wifi\n\n[wifi]\nssid=Work\n\n[802-1x]\neap=tls;\n"
       "ca-cert=/home/alice/certs/ca.pem\n")
NETPLAN = """network:
  version: 2
  wifis:
    NM-0ba3c7e4-2f6c-4b0b-8a8a-5c7d6e1f2a3b:
      renderer: NetworkManager
      match: {}
      dhcp4: true
      access-points:
        "Cafe du coin":
          hidden: true
          auth:
            key-management: "psk"
            password: "croissant42"
          networkmanager:
            uuid: "0ba3c7e4-2f6c-4b0b-8a8a-5c7d6e1f2a3b"
            name: "Cafe du coin"
            passthrough:
              connection.timestamp: "1700000000"
              connection.permissions: "user:alice:;"
"""


def old_root(tmp_path):
    root = tmp_path / "old"
    conns = root / "etc/NetworkManager/system-connections"
    write(conns / "Maison.nmconnection", HOME_WIFI, 0o600)
    write(conns / "Wired.nmconnection", WIRED, 0o600)
    write(conns / "Work.nmconnection", EAP, 0o600)
    write(root / "etc/netplan/90-NM-0ba3c7e4.yaml", NETPLAN, 0o600)
    write(root / "etc/netplan/01-network-manager-all.yaml", "network:\n  version: 2\n  renderer: NetworkManager\n")
    return root


def test_saved_wifi_networks_are_found(tmp_path):
    found = extras.wifi_connections(str(old_root(tmp_path)))
    assert sorted(c["ssid"] for c in found) == ["Cafe du coin", "Maison"]
    assert extras.wifi_names(str(old_root(tmp_path))) == ["Cafe du coin", "Maison"]


def test_keyfile_loses_the_old_accounts_permission_only(tmp_path):
    home = next(c for c in extras.wifi_connections(str(old_root(tmp_path))) if c["ssid"] == "Maison")
    assert "permissions=" not in home["text"]
    for line in ("psk=un mot de passe", "interface-name=wlp2s0", "uuid=6b1c2c1c-6c3f-4a39-9a77-2b7c7ad4f1a1"):
        assert line in home["text"].splitlines()


def test_netplan_network_becomes_a_keyfile(tmp_path):
    cafe = next(c for c in extras.wifi_connections(str(old_root(tmp_path))) if c["ssid"] == "Cafe du coin")
    text = cafe["text"]
    for line in ("[connection]", "id=Cafe du coin", "uuid=0ba3c7e4-2f6c-4b0b-8a8a-5c7d6e1f2a3b", "type=wifi",
                 "ssid=Cafe du coin", "hidden=true", "key-mgmt=wpa-psk", "psk=croissant42", "timestamp=1700000000"):
        assert line in text.splitlines(), line
    assert "permissions" not in text


def test_wifi_goes_into_the_new_system_root_only(tmp_path):
    connections = extras.wifi_connections(str(old_root(tmp_path)))
    target = tmp_path / "target"
    live = tmp_path / "live"
    write(target / "etc/NetworkManager/system-connections/Other.nmconnection",
          "[connection]\nid=Other\nuuid=9\ntype=wifi\n[wifi]\nssid=Other\n", 0o600)
    # the live session already knows this one; Setup copies its own over
    write(live / "etc/NetworkManager/system-connections/x.nmconnection",
          "[connection]\nid=Maison 1\nuuid=7\ntype=wifi\n[wifi]\nssid=Maison\n", 0o600)
    written = extras.install_wifi(str(target), connections, live=str(live), owner=None)
    assert written == ["Cafe du coin"]
    path = target / "etc/NetworkManager/system-connections/Cafe du coin.nmconnection"
    assert (path.stat().st_mode & 0o777) == 0o600
    assert "psk=croissant42" in path.read_text()


def test_wifi_names_never_leave_the_folder(tmp_path):
    connections = [{"ssid": "x", "uuid": "u", "name": "../../etc/evil", "text": "[connection]\nid=../../etc/evil\n"}]
    target = tmp_path / "target"
    extras.install_wifi(str(target), connections, live=str(tmp_path / "none"), owner=None)
    made = os.listdir(target / "etc/NetworkManager/system-connections")
    assert made == ["evil.nmconnection"]


# ----------------------------------------------------------------- flatpak

def test_flatpak_apps_system_and_per_account(tmp_path):
    root = tmp_path / "old"
    for app in ("org.gimp.GIMP", "com.spotify.Client"):
        (root / "var/lib/flatpak/app" / app / "current").mkdir(parents=True)
    (root / "var/lib/flatpak/app/.removed").mkdir(parents=True)
    homes = tmp_path / "homes"
    (homes / "alice/.local/share/flatpak/app/org.videolan.VLC").mkdir(parents=True)
    (homes / "alice/.local/share/flatpak/app/bad name").mkdir(parents=True)
    found = extras.flatpak_apps(str(root), [str(homes / "alice"), str(homes / "nobody")])
    assert found == ["com.spotify.Client", "org.gimp.GIMP", "org.videolan.VLC"]


# ------------------------------------------------------------ first sign-in

def test_welcome_back_script(tmp_path):
    home = tmp_path / "home/ana"
    home.mkdir(parents=True)
    entry = extras.leave_welcome_back(str(tmp_path), str(home), None, "en",
                                      wallpaper="/home/ana/Pictures/sea.jpg",
                                      apps=["org.gimp.GIMP", "org.videolan.VLC", "rm -rf /"])
    assert entry == str(home / ".config/autostart/raye-welcome-back.desktop")
    text = pathlib.Path(entry).read_text()
    assert "Exec=/bin/sh /home/ana/.local/share/raye/welcome-back\n" in text
    data = home / ".local/share/raye"
    assert (data / "kept-wallpaper").read_text() == "/home/ana/Pictures/sea.jpg\n"
    assert (data / "kept-apps").read_text() == "org.gimp.GIMP\norg.videolan.VLC\n"
    script = (data / "welcome-back").read_text()
    subprocess.run(["sh", "-n", str(data / "welcome-back")], check=True)
    assert "plasma-apply-wallpaperimage" in script and "flatpak install" in script
    assert "flathub" in script


def test_nothing_to_bring_writes_nothing(tmp_path):
    home = tmp_path / "home/ana"
    home.mkdir(parents=True)
    assert extras.leave_welcome_back(str(tmp_path), str(home), None, "fr", wallpaper="", apps=[]) is None
    assert not (home / ".config").exists()


def fake_tools(tmp_path, installed=(), fail=()):
    bin_dir = tmp_path / "bin"
    log = tmp_path / "log"
    for name, body in {
        "plasma-apply-wallpaperimage": f'echo "wallpaper $1" >> {log}',
        "nm-online": "exit 0",
        "id": 'echo "ana sudo"',
        "flatpak": (f'echo "flatpak $*" >> {log}\n'
                    f'case "$1 $*" in info*) case " {" ".join(installed)} " in *" $3 "*) exit 0;; esac; exit 1;; esac\n'
                    f'case " {" ".join(fail)} " in *" $6 "*) exit 1;; esac\nexit 0'),
        "notify-send": f'echo "notify $*" >> {log}',
        "sleep": "exit 0",
    }.items():
        write(bin_dir / name, f"#!/bin/sh\n{body}\n", 0o755)
    return bin_dir, log


def test_welcome_back_runs_once_and_says_how_it_went(tmp_path):
    home = tmp_path / "home/ana"
    home.mkdir(parents=True)
    extras.leave_welcome_back(str(home.parent.parent), str(home), None, "en",
                              wallpaper="/pics/sea.jpg", apps=["org.gimp.GIMP", "org.example.Gone"])
    bin_dir, log = fake_tools(tmp_path, fail=("org.example.Gone",))
    script = home / ".local/share/raye/welcome-back"
    env = {"HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin"}
    subprocess.run(["sh", str(script)], env=env, check=True)
    said = log.read_text()
    assert "wallpaper /pics/sea.jpg" in said
    assert "flatpak install --system -y --noninteractive flathub org.gimp.GIMP" in said
    assert "notify" in said and "1" in said.split("notify", 1)[1]
    # done: nothing left to run at the next sign-in
    assert not (home / ".config/autostart/raye-welcome-back.desktop").exists()
    assert not script.exists()


def test_welcome_back_waits_for_the_network(tmp_path):
    home = tmp_path / "home/ana"
    home.mkdir(parents=True)
    extras.leave_welcome_back(str(tmp_path), str(home), None, "en", wallpaper="", apps=["org.gimp.GIMP"])
    bin_dir, log = fake_tools(tmp_path)
    write(bin_dir / "nm-online", "#!/bin/sh\nexit 1\n", 0o755)
    script = home / ".local/share/raye/welcome-back"
    subprocess.run(["sh", str(script)], env={"HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin"}, check=True)
    assert "flatpak install" not in (log.read_text() if log.exists() else "")
    # tried again at the next sign-in
    assert (home / ".config/autostart/raye-welcome-back.desktop").exists() and script.exists()
