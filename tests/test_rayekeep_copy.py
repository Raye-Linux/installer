# SPDX-License-Identifier: GPL-3.0-or-later
"""Copying and moving the kept folders, on real files under tmp_path."""
import hashlib
import os
import pathlib
import sys

import pytest

FOLDER = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedisk"
sys.path.insert(0, str(FOLDER))
import rayedisk_finish as finish  # noqa: E402
import rayedisk_keep as keep  # noqa: E402


def tree(base):
    """{relative path: sha256} of every file, links as "-> target"."""
    found = {}
    for here, dirs, files in os.walk(base):
        for name in files + [d for d in dirs if os.path.islink(os.path.join(here, d))]:
            path = os.path.join(here, name)
            rel = os.path.relpath(path, base)
            if os.path.islink(path):
                found[rel] = "-> " + os.readlink(path)
            else:
                found[rel] = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    return found


@pytest.fixture
def owner():
    if os.geteuid() != 0:
        pytest.skip("changing owners needs root")
    return (4321, 4321)


def sample(base):
    (base / "2023/trip").mkdir(parents=True)
    (base / "2023/trip/a.jpg").write_bytes(os.urandom(300_000))
    (base / "notes.txt").write_text("hello")
    (base / "empty.bin").write_bytes(b"")
    (base / "Évènement ✓.pdf").write_bytes(os.urandom(5000))
    os.symlink("notes.txt", base / "link-to-notes")
    os.utime(base / "notes.txt", (1_600_000_000, 1_600_000_000))
    return base


def test_every_file_arrives_the_same(tmp_path):
    source = sample(tmp_path / "src")
    copier = keep.Copier()
    copier.copy_tree(str(source), str(tmp_path / "dst/Documents"))
    assert tree(source) == tree(tmp_path / "dst/Documents")
    assert copier.report()["files"] == 4 and copier.report()["failed"] == 0
    assert copier.report()["links"] == 1
    assert int(os.stat(tmp_path / "dst/Documents/notes.txt").st_mtime) == 1_600_000_000


def test_windows_links_are_left_out(tmp_path):
    source = sample(tmp_path / "src")
    copier = keep.Copier(links="skip", mode_mask=0o644)
    copier.copy_tree(str(source), str(tmp_path / "dst"))
    assert not os.path.lexists(tmp_path / "dst/link-to-notes")
    assert copier.report()["skipped"] == 1
    assert os.stat(tmp_path / "dst/notes.txt").st_mode & 0o777 == 0o644


def test_a_name_already_there_gets_a_number(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/cv.odt").write_text("new")
    (tmp_path / "dst").mkdir()
    (tmp_path / "dst/cv.odt").write_text("old")
    (tmp_path / "dst/cv (2).odt").write_text("older")
    keep.Copier().copy_tree(str(tmp_path / "src"), str(tmp_path / "dst"))
    assert (tmp_path / "dst/cv.odt").read_text() == "old"
    assert (tmp_path / "dst/cv (3).odt").read_text() == "new"


def test_a_file_that_reads_back_wrong_is_a_failure(tmp_path, monkeypatch):
    source = sample(tmp_path / "src")
    real = keep._hash_of
    monkeypatch.setattr(keep, "_hash_of", lambda fd: ("0" * 64, real(fd)[1]))
    copier = keep.Copier()
    copier.copy_tree(str(source), str(tmp_path / "dst"))
    assert copier.report()["failed"] == 4
    assert copier.report()["files"] == 0


def test_a_file_that_cannot_be_read_is_a_failure(tmp_path, monkeypatch):
    source = sample(tmp_path / "src")
    real_open = os.open

    def refusing(path, flags, *args):
        if str(path).endswith("a.jpg") and not flags & os.O_WRONLY:
            raise PermissionError(13, "no")
        return real_open(path, flags, *args)
    monkeypatch.setattr(os, "open", refusing)
    copier = keep.Copier()
    copier.copy_tree(str(source), str(tmp_path / "dst"))
    assert copier.report()["failed"] == 1
    assert any(p.endswith("a.jpg") for p in copier.report()["examples"])


def test_special_files_are_skipped_and_counted(tmp_path):
    (tmp_path / "src").mkdir()
    os.mkfifo(tmp_path / "src/pipe")
    copier = keep.Copier()
    copier.copy_tree(str(tmp_path / "src"), str(tmp_path / "dst"))
    assert copier.report() == {"files": 0, "bytes": 0, "links": 0, "skipped": 1, "failed": 0, "examples": []}


def test_owner_is_set_on_what_is_made(tmp_path, owner):
    source = sample(tmp_path / "src")
    keep.Copier(owner=owner).copy_tree(str(source), str(tmp_path / "home/Documents"))
    for path in [tmp_path / "home", tmp_path / "home/Documents/2023", tmp_path / "home/Documents/notes.txt",
                 tmp_path / "home/Documents/link-to-notes"]:
        assert os.lstat(path).st_uid == owner[0], path


def test_moving_renames_and_never_copies(tmp_path, owner):
    source = sample(tmp_path / "old/Documents")
    inode = os.stat(source / "notes.txt").st_ino
    before = tree(source)
    (tmp_path / "new/Documents").mkdir(parents=True)
    moved, failed = keep.move_contents(str(source), str(tmp_path / "new/Documents"), owner)
    assert failed == [] and moved == 5
    assert tree(tmp_path / "new/Documents") == before
    assert os.stat(tmp_path / "new/Documents/notes.txt").st_ino == inode
    assert not source.exists()
    assert os.lstat(tmp_path / "new/Documents/2023/trip/a.jpg").st_uid == owner[0]


def account_root(tmp_path, username="alice", uid=4321):
    root = tmp_path / "target"
    (root / "etc").mkdir(parents=True)
    (root / "etc/passwd").write_text(f"root:x:0:0::/root:/bin/sh\n{username}:x:{uid}:{uid}::/home/{username}:/bin/bash\n")
    return root


def test_old_home_with_the_new_accounts_name_moves_aside(tmp_path):
    root = account_root(tmp_path)
    (root / "home/alice/.config").mkdir(parents=True)
    (root / "home/alice.old").mkdir()
    assert finish.make_room_for(str(root), "alice") == "alice.old (2)"
    assert (root / "home/alice.old (2)/.config").is_dir()
    assert not (root / "home/alice").exists()
    assert finish.make_room_for(str(root), "bob") == ""


class Quiet(finish.Finisher):
    def __init__(self):
        super().__init__(run=None, read_table=None)


def test_home_way_moves_every_folder_into_the_account(tmp_path, owner):
    root = account_root(tmp_path)
    (root / "home/alice/.config").mkdir(parents=True)
    (root / "home/alice/.config/user-dirs.dirs").write_text('XDG_DOCUMENTS_DIR="$HOME/Docs"\n')
    sample(root / "home/alice/Docs")
    (root / "home/alice/.bashrc").write_text("old shell")
    (root / "home/bob/Musique").mkdir(parents=True)
    (root / "home/bob/Musique/a.ogg").write_text("la")
    kept_before = tree(root / "home/alice/Docs")
    aside = finish.make_room_for(str(root), "alice")
    (root / "home/alice").mkdir()
    kept = {"way": "home", "name": "Linux Mint 22", "users": [
        {"name": "alice", "home": "alice", "folders": [{"kind": "documents", "path": "Docs"}]},
        {"name": "bob", "home": "bob", "folders": [{"kind": "music", "path": "Musique"}]}]}
    result = Quiet().move_home(kept, str(root), "alice", "fr", aside)
    assert result["ok"] and result["moved"] == 6
    assert tree(root / "home/alice/Documents/alice") == kept_before
    assert (root / "home/alice/Musique/bob/a.ogg").read_text() == "la"
    # what was not kept stays where it was
    assert (root / f"home/{aside}/.bashrc").read_text() == "old shell"
    dirs = (root / "home/alice/.config/user-dirs.dirs").read_text()
    assert 'XDG_DOWNLOAD_DIR="$HOME/Téléchargements"' in dirs
    assert all((root / "home/alice" / n).is_dir() for n in keep.FOLDERS["fr"].values())
