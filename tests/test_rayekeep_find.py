# SPDX-License-Identifier: GPL-3.0-or-later
"""Finding the folders of another system: what counts, what is left out.

Real folders under tmp_path stand for the mounted volumes.
"""
import contextlib
import os
import pathlib
import sys

FOLDER = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedisk"
sys.path.insert(0, str(FOLDER))
import rayedisk_keep as keep  # noqa: E402
import rayedisk_probe as probe  # noqa: E402

PASSWD = """root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
alice:x:1000:1000:Alice,,,:/home/alice:/bin/bash
bob:x:1001:1001::/home/bob:/bin/bash
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
"""


def write(path, text="x", size=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if size is None:
        path.write_text(text)
    else:
        path.write_bytes(os.urandom(size))
    return path


def linux_root(top, fstab="", name="Linux Mint 22"):
    write(top / "etc/os-release", f'NAME="Mint"\nPRETTY_NAME="{name}"\n')
    write(top / "etc/fstab", fstab or "UUID=1111 / ext4 defaults 0 1\n")
    write(top / "etc/passwd", PASSWD)


def test_user_dirs_are_read_and_turned_off_ones_left_out():
    dirs = keep.parse_user_dirs('XDG_DOCUMENTS_DIR="$HOME/Docs"\n'
                                'XDG_MUSIC_DIR="$HOME"\n'
                                'XDG_PICTURES_DIR="/media/photos"\n'
                                'XDG_VIDEOS_DIR="$HOME/../etc"\n'
                                'XDG_DOWNLOAD_DIR="$HOME/Téléchargements"\n')
    assert dirs["documents"] == "Docs"
    assert dirs["downloads"] == "Téléchargements"
    assert dirs["desktop"] == "Desktop"
    assert "music" not in dirs and "pictures" not in dirs and "videos" not in dirs


def test_passwd_keeps_only_peoples_accounts():
    assert [u[0] for u in keep.parse_passwd(PASSWD)] == ["alice", "bob"]


def test_linux_users_and_their_folders(tmp_path):
    linux_root(tmp_path)
    write(tmp_path / "home/alice/Documents/cv.odt", size=1000)
    write(tmp_path / "home/alice/Pictures/2024/a.jpg", size=3000)
    write(tmp_path / "home/alice/.bashrc")
    write(tmp_path / "home/bob/.config/user-dirs.dirs", 'XDG_MUSIC_DIR="$HOME/Musique"\n')
    write(tmp_path / "home/bob/Musique/song.ogg", size=500)
    users = keep.linux_users(str(tmp_path), str(tmp_path / "home"))
    assert [u["name"] for u in users] == ["alice", "bob"]
    alice = {f["kind"]: f for f in users[0]["folders"]}
    assert set(alice) == {"documents", "pictures"}
    assert alice["pictures"]["files"] == 1 and alice["pictures"]["bytes"] == 3000
    assert users[1]["folders"][0]["path"] == "Musique"
    assert keep.totals(users)[:2] == (3, 4500)


def test_a_folder_that_is_a_link_is_not_followed(tmp_path):
    linux_root(tmp_path)
    write(tmp_path / "elsewhere/secret.txt")
    (tmp_path / "home/alice").mkdir(parents=True)
    os.symlink(tmp_path / "elsewhere", tmp_path / "home/alice/Documents")
    assert keep.linux_users(str(tmp_path), str(tmp_path / "home")) == []


def test_links_inside_a_folder_are_counted_not_followed(tmp_path):
    write(tmp_path / "big/huge.bin", size=50000)
    write(tmp_path / "Documents/a.txt", "abc")
    os.symlink(tmp_path / "big", tmp_path / "Documents/big")
    size = keep.measure(str(tmp_path / "Documents"))
    assert size == {"files": 1, "bytes": 3, "links": 1, "other": 0, "unreadable": 0}


def test_windows_users_leave_out_the_built_in_ones(tmp_path):
    for name in ("Default", "Public", "All Users", "Ann", "Marc"):
        (tmp_path / "Users" / name).mkdir(parents=True)
    write(tmp_path / "Users/Ann/Desktop/note.txt")
    write(tmp_path / "Users/Ann/Downloads/setup.exe", size=200)
    write(tmp_path / "Users/Public/Documents/shared.txt")
    write(tmp_path / "Users/Default/Documents/x.txt")
    users = keep.windows_users(str(tmp_path / "Users"))
    assert [u["name"] for u in users] == ["Ann"]
    assert [f["kind"] for f in users[0]["folders"]] == ["desktop", "downloads"]


def test_root_of_a_btrfs_volume_is_found_in_its_subvolume(tmp_path):
    linux_root(tmp_path / "@", "UUID=abcd / btrfs subvol=@ 0 0\nUUID=abcd /home btrfs subvol=@home 0 0\n")
    (tmp_path / "@home").mkdir()
    info = keep.look_linux(str(tmp_path), "btrfs", "ABCD")
    assert info["root"] == "@"
    assert info["home"] == {"on": "self", "path": "@home"}


def test_home_on_a_partition_of_its_own_is_named(tmp_path):
    linux_root(tmp_path, "UUID=1111 / ext4 defaults 0 1\nUUID=2222-aa /home ext4 defaults 0 2\n")
    info = keep.look_linux(str(tmp_path), "ext4", "1111")
    assert info["name"] == "Linux Mint 22"
    assert info["home"]["on"] == "other" and info["home"]["spec"] == "UUID=2222-aa"
    part = {"node": "/dev/sda3", "uuid": "2222-AA", "label": "", "partuuid": ""}
    assert keep.resolve_spec("UUID=2222-aa", [part]) is part
    assert keep.resolve_spec("LABEL=home", [part]) is None


def test_not_a_linux_system_has_nothing_to_keep(tmp_path):
    write(tmp_path / "photos/a.jpg")
    assert keep.look_linux(str(tmp_path), "ext4", "1") is None


def test_read_only_mount_options():
    assert keep.mount_argv("/dev/sda2", "ext4", "/m")[3:5] == ["-o", "ro,noload"]
    assert "ro,norecovery" in keep.mount_argv("/dev/sda3", "xfs", "/m")
    assert "ro,subvolid=5" in keep.mount_argv("/dev/sda2", "btrfs", "/m")
    assert keep.mount_argv("/dev/sda3", "ntfs", "/m")[:5] == ["mount", "-t", "ntfs-3g", "-o", "ro"]
    for fstype in ("ext2", "ext3", "ext4", "xfs", "btrfs", "ntfs"):
        assert keep.mount_argv("/dev/x", fstype, "/m")[4].startswith("ro")


def opener_of(folders):
    @contextlib.contextmanager
    def opener(part):
        yield folders.get(part["node"])
    return opener


def part(node, fstype, **more):
    entry = {"node": node, "number": int(node[-1]), "start": 0, "sectors": 1, "type": "x",
             "fstype": fstype, "mounted": False, "findings": [], "uuid": "", "label": ""}
    entry.update(more)
    return entry


def test_probe_finds_the_home_of_another_partition(tmp_path):
    root, home = tmp_path / "root", tmp_path / "home"
    linux_root(root, "UUID=r / ext4 defaults 0 1\nUUID=h /home ext4 defaults 0 2\n")
    write(home / "alice/Videos/clip.mp4", size=10)
    disk = {"node": "/dev/sda", "parts": [part("/dev/sda2", "ext4", uuid="r"), part("/dev/sda3", "ext4", uuid="h")]}
    probe.find_files_to_keep([disk], opener=opener_of({"/dev/sda2": str(root), "/dev/sda3": str(home)}))
    found = disk["parts"][0]["keep"]
    assert found["home"] == "/dev/sda3" and found["users"][0]["name"] == "alice"
    # the home partition is no system of its own
    assert "keep" not in disk["parts"][1]


def test_probe_leaves_volumes_with_findings_or_mounted_alone(tmp_path):
    linux_root(tmp_path)
    write(tmp_path / "home/alice/Documents/a.txt")
    looked = []

    @contextlib.contextmanager
    def opener(p):
        looked.append(p["node"])
        yield str(tmp_path)
    disk = {"node": "/dev/sda", "parts": [part("/dev/sda1", "ext4", findings=["linux-check"]),
                                         part("/dev/sda2", "ext4", mounted=True)]}
    probe.find_files_to_keep([disk], opener=opener)
    assert looked == []


def test_probe_reads_windows_users(tmp_path):
    write(tmp_path / "Users/Ann/Pictures/p.png", size=64)
    disk = {"node": "/dev/sda", "parts": [part("/dev/sda3", "ntfs", os="Windows")]}
    probe.find_files_to_keep([disk], opener=opener_of({"/dev/sda3": str(tmp_path)}))
    found = disk["parts"][0]["keep"]
    assert found["system"] == "windows" and found["base"] == "Users"
    assert found["users"][0]["folders"][0]["kind"] == "pictures"


def test_new_account_folders_are_named_in_its_language():
    assert keep.destination("fr", "downloads", "alice", False) == "Téléchargements"
    assert keep.destination("en", "pictures", "bob", True) == os.path.join("Pictures", "bob")
    text = keep.user_dirs_text('XDG_TEMPLATES_DIR="$HOME/.local/share/templates"\nXDG_DESKTOP_DIR="$HOME/x"\n', "fr")
    assert 'XDG_TEMPLATES_DIR="$HOME/.local/share/templates"' in text
    assert 'XDG_DESKTOP_DIR="$HOME/Bureau"' in text and "$HOME/x" not in text
    assert text.count("XDG_") == 7


def test_an_odd_account_name_stays_inside_the_folder():
    for name in ("../../etc", "..", "", "a/b"):
        where = keep.destination("en", "music", name, True)
        assert where.startswith("Music" + os.sep)
        assert ".." not in where.split(os.sep) and where.count(os.sep) == 1
