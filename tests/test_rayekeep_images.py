# SPDX-License-Identifier: GPL-3.0-or-later
""""Replace and keep my files" from start to end, on disk images.

A disk image in tmp_path is put on a loop device with its partitions, an
old system is made on it with real files, and the disk job then shrinks,
stages, copies, deletes and formats it for real; the account step copies
the files in and grows Raye's volume. Every file is compared by SHA-256.

Needs root and loop devices; skipped without them. Nothing outside the
image is ever written.
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

FOLDER = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedisk"
sys.path.insert(0, str(FOLDER))
import rayedisk_apply as apply  # noqa: E402
import rayedisk_core as core  # noqa: E402
import rayedisk_finish as finish  # noqa: E402
import rayedisk_keep as keep  # noqa: E402
import rayedisk_probe as probe  # noqa: E402

GIB = core.GIB
MIB = core.MIB
TOOLS = ("losetup", "sfdisk", "mke2fs", "mkfs.btrfs", "mkfs.vfat", "resize2fs", "blkid", "mount")


def loop_works():
    if os.geteuid() != 0 or any(shutil.which(t) is None for t in TOOLS):
        return False
    return os.path.exists("/dev/loop-control")


pytestmark = pytest.mark.skipif(not loop_works(), reason="needs root and loop devices")


def real(argv, feed=None, tolerate=False):
    done = subprocess.run(argv, input=feed, capture_output=True, text=True, errors="replace",
                          env={**os.environ, "LC_ALL": "C"})
    if done.returncode and not tolerate:
        raise apply.CommandFailed(argv, done.returncode, done.stderr + done.stdout)
    return done.stdout


def probe_run(argv, timeout=60):
    done = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                          env={**os.environ, "LC_ALL": "C"}, timeout=timeout)
    return done.returncode, done.stdout


def hashes(base):
    """{relative path: sha256} of the files under base, links as "-> target"."""
    found = {}
    for here, dirs, files in os.walk(base):
        for name in files + [d for d in dirs if os.path.islink(os.path.join(here, d))]:
            path = os.path.join(here, name)
            rel = os.path.relpath(path, base)
            found[rel] = ("-> " + os.readlink(path) if os.path.islink(path)
                          else hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest())
    return found


@pytest.fixture
def loop(tmp_path, monkeypatch):
    """A 40 GiB sparse disk image on a loop device; detached afterwards."""
    monkeypatch.setattr(apply, "BACKUP_DIR", str(tmp_path / "root-only"))
    os.mkdir(tmp_path / "root-only", 0o700)
    image = tmp_path / "disk.img"
    with open(image, "wb") as f:
        f.truncate(40 * GIB)
    state = {"node": None, "mounts": []}

    def attach(script):
        real(["sfdisk", "-q", str(image)], feed=script)
        state["node"] = real(["losetup", "--partscan", "--show", "--find", str(image)]).strip()
        return state["node"]
    yield attach, state, tmp_path
    for where in reversed(state["mounts"]):
        real(["umount", where], tolerate=True)
    if state["node"]:
        real(["losetup", "--detach", state["node"]], tolerate=True)


def old_linux(tree, home_spec=None, name="Linux Mint 22"):
    """The files of an old Linux root, in a folder mke2fs or mkfs.btrfs can copy."""
    (tree / "etc").mkdir(parents=True)
    (tree / "etc/os-release").write_text(f'NAME="Mint"\nPRETTY_NAME="{name}"\n')
    fstab = "UUID=x / ext4 defaults 0 1\n" + (f"{home_spec} /home ext4 defaults 0 2\n" if home_spec else "")
    (tree / "etc/fstab").write_text(fstab)
    (tree / "etc/passwd").write_text("root:x:0:0::/root:/bin/bash\nalice:x:1000:1000::/home/alice:/bin/bash\n")
    (tree / "usr/bin").mkdir(parents=True)
    (tree / "usr/bin/tool").write_bytes(os.urandom(2 * MIB))


def alice_files(home):
    docs = home / "alice/Documents"
    (docs / "taxes/2024").mkdir(parents=True)
    (docs / "taxes/2024/return.pdf").write_bytes(os.urandom(3 * MIB + 17))
    (docs / "Été à Québec.txt").write_text("bonjour")
    (docs / "empty").write_bytes(b"")
    os.symlink("taxes", docs / "shortcut")
    (home / "alice/Pictures").mkdir()
    for i in range(40):
        (home / f"alice/Pictures/img{i:03}.jpg").write_bytes(os.urandom(50_000 + i))
    (home / "alice/.bashrc").write_text("not kept")
    (home / "alice/Projects").mkdir()
    (home / "alice/Projects/code.py").write_text("not kept either")


def settle(node):
    real(["udevadm", "settle"], tolerate=True)
    real(["partx", "--update", node], tolerate=True)


def read_table(node):
    data = json.loads(real(["sfdisk", "--json", node]))["partitiontable"]
    return {"parts": [{"node": p["node"], "start": p["start"], "sectors": p["size"], "type": p["type"]}
                      for p in data.get("partitions", [])]}


def disk_of(node):
    """The disk as the page reads it, through the probe's own code."""
    text = real(["lsblk", "--json", "--tree=PATH", "--bytes", "--paths", "--output",
                 "PATH,TYPE,SIZE,MODEL,RM,TRAN,FSTYPE,LABEL,UUID,PARTUUID,MOUNTPOINTS,LOG-SEC", node])
    blk = json.loads(text)["blockdevices"][0]
    # the udev database may lag behind mkfs in a chroot: ask blkid directly
    for child in blk.get("children") or []:
        for key, tag in (("fstype", "TYPE"), ("uuid", "UUID"), ("label", "LABEL")):
            child[key] = real(["blkid", "-c", "/dev/null", "-o", "value", "-s", tag, child["path"]],
                              tolerate=True).strip() or None
    disk = probe.read_disk(blk, {}, {}, probe_run, look=False)
    disk["hardware"] = "image"
    disk["unreadable"] = False
    return disk


def writer():
    w = apply.Writer(real, read_table, identify=lambda node: "image")
    return w


def mount(state, node, where, options="rw"):
    os.makedirs(where, exist_ok=True)
    real(["mount", "-o", options, node, str(where)])
    state["mounts"].append(str(where))


def umount(state, where):
    real(["umount", str(where)])
    state["mounts"].remove(str(where))


def make_old_system(attach, state, tmp_path, fstype):
    node = attach("label: gpt\n,512M,U\n,,L\n")
    settle(node)
    real(["mkfs.vfat", "-F", "32", node + "p1"])
    tree = tmp_path / "old"
    if fstype == "ntfs":
        real(["mkntfs", "-Q", "-q", "-F", node + "p2"])
        where = tmp_path / "fill"
        where.mkdir()
        real(["ntfs-3g", node + "p2", str(where)])
        (where / "Windows/System32").mkdir(parents=True)
        (where / "Users/Ann").mkdir(parents=True)
        (where / "Users/Default/Documents").mkdir(parents=True)
        alice_files(where / "Users")
        os.rename(where / "Users/alice", where / "Users/Ann2")
        # what Windows calls a junction is left out of the copy
        before = {k: v for k, v in hashes(where / "Users/Ann2/Documents").items() if not v.startswith("-> ")}
        pictures = hashes(where / "Users/Ann2/Pictures")
        real(["umount", str(where)])
        return node, before, pictures, "Ann2"
    old_linux(tree)
    alice_files(tree / "home")
    before = hashes(tree / "home/alice/Documents")
    pictures = hashes(tree / "home/alice/Pictures")
    if fstype == "btrfs":
        btrfs = tmp_path / "btrfs"
        (btrfs / "@").mkdir(parents=True)
        for name in os.listdir(tree):
            if name != "home":
                os.rename(tree / name, btrfs / "@" / name)
        os.rename(tree / "home", btrfs / "@home")
        (btrfs / "@/etc/fstab").write_text("UUID=x / btrfs subvol=@ 0 0\nUUID=x /home btrfs subvol=@home 0 0\n")
        real(["mkfs.btrfs", "-q", "-f", "--rootdir", str(btrfs), "--subvol", "@", "--subvol", "@home", node + "p2"])
        uuid = real(["blkid", "-c", "/dev/null", "-o", "value", "-s", "UUID", node + "p2"]).strip()
        # the fstab names the volume by its real UUID, as a real install does
        where = tmp_path / "fix"
        mount(state, node + "p2", where, "subvolid=5")
        (where / "@/etc/fstab").write_text(f"UUID={uuid} / btrfs subvol=@ 0 0\nUUID={uuid} /home btrfs subvol=@home 0 0\n")
        umount(state, where)
    else:
        real(["mke2fs", "-q", "-F", "-t", "ext4", "-d", str(tree), node + "p2"])
    return node, before, pictures, "alice"


@pytest.mark.parametrize("fstype", ["ext4", "btrfs", "ntfs"])
def test_replace_and_keep_from_start_to_end(loop, fstype):
    attach, state, tmp_path = loop
    if fstype == "ntfs" and shutil.which("ntfs-3g") is None:
        pytest.skip("ntfs-3g is not installed")
    node, documents, pictures, user = make_old_system(attach, state, tmp_path, fstype)

    disk = disk_of(node)
    probe.find_files_to_keep([disk], probe_run)
    old = next(p for p in disk["parts"] if p["node"] == node + "p2")
    assert old["keep"]["users"][0]["name"] == user
    assert [f["kind"] for f in old["keep"]["users"][0]["folders"]] == ["documents", "pictures"]
    options, refused = core.options_for(disk)
    assert any(o["mode"] == "keep" and o["way"] == "stage" for o in options), refused

    answer = {"mode": "keep", "disk": node, "id": disk["id"], "partition": node + "p2", "encrypt": False}
    plan = core.plan(disk, "efi", answer, False, [disk])
    made = writer().apply(plan, disk, "")

    # the old volume is gone; Raye's partitions and the copies are there
    table = read_table(node)["parts"]
    starts = {p["start"]: p for p in table}
    assert plan["stage"]["start"] in starts
    assert all(a["start"] in starts for a in plan["add"])
    assert not any(p["start"] == old["start"] and p["sectors"] == old["sectors"] for p in table)
    assert plan["add"][0]["start"] == old["start"]
    stage = starts[plan["stage"]["start"]]["node"]
    where = tmp_path / "look-stage"
    mount(state, stage, where, "ro")
    assert hashes(where / "users/0/documents") == documents
    assert hashes(where / "users/0/pictures") == pictures
    assert json.loads((where / apply.MANIFEST).read_text())["files"] == plan["keep"]["files"]
    umount(state, where)

    # the account step: Raye's root, an account, the files in
    kept = finish.keep_storage(plan, made)
    target = tmp_path / "target"
    root_node = next(m["device"] for m in made if m["mountPoint"] == "/")
    mount(state, root_node, target)
    (target / "etc").mkdir()
    (target / "etc/passwd").write_text("root:x:0:0::/root:/bin/sh\nnew:x:1000:1000::/home/new:/bin/bash\n")
    (target / "home/new").mkdir(parents=True)
    size_before = os.statvfs(target).f_blocks * os.statvfs(target).f_frsize
    result = finish.Finisher(real, read_table, identify=lambda n: "image").bring_home(
        kept, str(target), "new", "fr")
    assert result["ok"] and not result["left"] and result["grown"], result
    several = False
    assert hashes(target / "home/new" / keep.destination("fr", "documents", user, several)) == documents
    assert hashes(target / "home/new/Images") == pictures
    assert not (target / "home/new/Projects").exists()
    # the staging partition went, Raye's volume took its room
    after = {p["start"]: p for p in read_table(node)["parts"]}
    assert plan["stage"]["start"] not in after
    assert after[kept["rootStart"]]["sectors"] == kept["stageStart"] + kept["stageSectors"] - kept["rootStart"]
    assert os.statvfs(target).f_blocks * os.statvfs(target).f_frsize > size_before
    umount(state, target)


def test_a_copy_that_fails_deletes_nothing(loop, monkeypatch):
    attach, state, tmp_path = loop
    node, documents, pictures, user = make_old_system(attach, state, tmp_path, "ext4")
    disk = disk_of(node)
    probe.find_files_to_keep([disk], probe_run)
    answer = {"mode": "keep", "disk": node, "id": disk["id"], "partition": node + "p2", "encrypt": False}
    plan = core.plan(disk, "efi", answer, False, [disk])
    real_hash = keep._hash_of
    calls = []

    def one_bad(fd):
        calls.append(fd)
        digest, size = real_hash(fd)
        return ("0" * 64 if len(calls) == 7 else digest), size
    monkeypatch.setattr(keep, "_hash_of", one_bad)
    with pytest.raises(core.Refused) as no:
        writer().apply(plan, disk, "")
    assert no.value.code == "keep-copy"
    # the old volume is still there, smaller, and every file reads the same
    table = read_table(node)["parts"]
    assert [p["node"] for p in table] == [node + "p1", node + "p2"]
    real(["e2fsck", "-f", "-n", node + "p2"])
    where = tmp_path / "check"
    mount(state, node + "p2", where, "ro")
    assert hashes(where / "home/alice/Documents") == documents
    assert hashes(where / "home/alice/Pictures") == pictures
    umount(state, where)


def test_separate_home_is_reused_untouched(loop):
    attach, state, tmp_path = loop
    node = attach("label: gpt\n,512M,U\n,30G,L\n,,L\n")
    state["node"] = node
    settle(node)
    real(["mkfs.vfat", "-F", "32", node + "p1"])
    home = tmp_path / "home-tree"
    home.mkdir()
    alice_files(home)
    real(["mke2fs", "-q", "-F", "-t", "ext4", "-d", str(home), node + "p3"])
    uuid = real(["blkid", "-c", "/dev/null", "-o", "value", "-s", "UUID", node + "p3"]).strip()
    tree = tmp_path / "root-tree"
    old_linux(tree, home_spec=f"UUID={uuid}")
    real(["mke2fs", "-q", "-F", "-t", "ext4", "-d", str(tree), node + "p2"])
    everything = hashes(home)

    disk = disk_of(node)
    probe.find_files_to_keep([disk], probe_run)
    answer = {"mode": "keep", "disk": node, "id": disk["id"], "partition": node + "p2", "encrypt": False}
    plan = core.plan(disk, "efi", answer, False, [disk])
    assert plan["keep"]["way"] == "home" and plan["keep"]["home"] == node + "p3"
    made = writer().apply(plan, disk, "")
    assert all(m["device"] != node + "p3" for m in made)
    assert node + "p3" in [p["node"] for p in read_table(node)["parts"]]

    # Raye's /home is the old one; the account is made, the folders moved in
    target = tmp_path / "target"
    mount(state, next(m["device"] for m in made if m["mountPoint"] == "/"), target)
    mount(state, node + "p3", target / "home")
    (target / "etc").mkdir()
    (target / "etc/passwd").write_text("root:x:0:0::/root:/bin/sh\nalice:x:1000:1000::/home/alice:/bin/bash\n")
    aside = finish.make_room_for(str(target), "alice")
    assert aside == "alice.old"
    (target / "home/alice").mkdir()
    kept = finish.keep_storage(plan, made)
    result = finish.Finisher(real, read_table).move_home(kept, str(target), "alice", "en", aside)
    assert result["ok"], result
    now = hashes(target / "home")
    # every file is still on the partition, the kept ones in the new folders
    assert sorted(v for k, v in now.items() if not k.startswith("lost+found")
                  and not k.startswith("alice/.config")) == sorted(everything.values())
    assert hashes(target / "home/alice/Documents") == hashes(home / "alice/Documents")
    assert (target / "home/alice.old/Projects/code.py").read_text() == "not kept either"
    umount(state, target / "home")
    umount(state, target)
    real(["e2fsck", "-f", "-n", node + "p3"])
