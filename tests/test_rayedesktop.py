# SPDX-License-Identifier: GPL-3.0-or-later
"""The desktop picked on Setup's "Choose your desktop" page: KDE Plasma
leaves the new system as the image made it, Hyprland is added to it and
becomes the account's session, with KDE Plasma still there."""
import configparser
import gzip
import importlib.util
import os
import pathlib
import re
import sys
import types

import pytest

MODULE = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedesktop/main.py"
SESSION = "/usr/share/wayland-sessions/raye-hyprland.desktop"
POOL_ENTRY = (
    "Package: raye-hyprland\nVersion: 1.0~beta1\nArchitecture: all\n"
    "Filename: ./raye-hyprland_1.0~beta1_all.deb\n\n"
    "Package: hyprland\nVersion: 0.53.3+ds-4\nArchitecture: amd64\n"
    "Filename: ./hyprland_0.53.3+ds-4_amd64.deb\n\n")


class FakeStorage(dict):
    def value(self, key):
        return self.get(key)


@pytest.fixture
def rd(monkeypatch, tmp_path):
    fake = types.ModuleType("libcalamares")
    fake.utils = types.SimpleNamespace(debug=lambda *a: None, warning=lambda *a: None,
                                       target_env_call=None)
    fake.globalstorage = FakeStorage()
    fake.job = types.SimpleNamespace(configuration={})
    monkeypatch.setitem(sys.modules, "libcalamares", fake)
    spec = importlib.util.spec_from_file_location("rayedesktop", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ANSWERS", str(tmp_path / "answers"))
    monkeypatch.setattr(module, "RESULT", str(tmp_path / "root-only/desktop-result"))
    (tmp_path / "answers").mkdir()
    (tmp_path / "root-only").mkdir()
    return module


@pytest.fixture
def chowns(rd, monkeypatch):
    seen = {}
    monkeypatch.setattr(rd.os, "chown", lambda path, uid, gid: seen.__setitem__(str(path), (uid, gid)))
    return seen


def answer(tmp_path, text):
    (tmp_path / "answers/answer-desktop").write_text(text)


def make_root(tmp_path):
    root = tmp_path / "target"
    (root / "etc").mkdir(parents=True)
    (root / "etc/passwd").write_text(
        "root:x:0:0:root:/root:/bin/bash\n"
        "sddm:x:118:124:Simple Desktop Display Manager:/var/lib/sddm:/bin/false\n"
        "ana:x:1000:1000:Ana,,,:/home/ana:/bin/bash\n")
    (root / "var/lib/sddm").mkdir(parents=True)
    (root / "usr/share/wayland-sessions").mkdir(parents=True)
    (root / "usr/share/wayland-sessions/plasma.desktop").write_text("[Desktop Entry]\nName=Plasma\n")
    return root


def make_pool(tmp_path, entries=POOL_ENTRY, gz=False):
    pool = tmp_path / "cdrom/raye/desktops"
    pool.mkdir(parents=True)
    if gz:
        with gzip.open(pool / "Packages.gz", "wt") as f:
            f.write(entries)
    else:
        (pool / "Packages").write_text(entries)
    return pool


class Target:
    """target_env_call: records each command, and "installs" the package
    when apt-get install is asked for it."""

    def __init__(self, root, codes=None, lands=True):
        self.root = root
        self.calls = []
        self.codes = codes or {}
        self.lands = lands
        self.sources = []

    def __call__(self, cmd, stdin=None, timeout=0):
        self.calls.append(list(cmd))
        for a in cmd:
            if a.startswith("Dir::Etc::SourceList="):
                inside = a.split("=", 1)[1]
                self.sources.append((self.root / inside.lstrip("/")).read_text())
        verb = "install" if "install" in cmd else "update" if "update" in cmd else "other"
        code = self.codes.get(verb, 0)
        if verb == "install" and code == 0 and self.lands:
            (self.root / SESSION.lstrip("/")).write_text("[Desktop Entry]\nName=Hyprland\n")
        return code


def ini(path):
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    parser.read(path)
    return parser


def run(rd, root, target, username="ana", pool=None):
    rd.libcalamares.globalstorage.update(rootMountPoint=str(root), username=username)
    rd.libcalamares.utils.target_env_call = target
    if pool is not None:
        rd.libcalamares.job.configuration["pool"] = str(pool)
    return rd.run()


# --- what the page left ------------------------------------------------------

def test_no_answer_means_plasma(rd):
    assert rd.read_choice() == "plasma"


def test_hyprland_answer(rd, tmp_path):
    answer(tmp_path, "hyprland\n")
    assert rd.read_choice() == "hyprland"


@pytest.mark.parametrize("text", ["Hyprland", "gnome", "hyprland; rm -rf /", "", "plasma"])
def test_anything_else_is_plasma(rd, tmp_path, text):
    answer(tmp_path, text)
    assert rd.read_choice() == "plasma"


def test_job_name_in_both_languages(rd, tmp_path, monkeypatch):
    answer(tmp_path, "hyprland")
    monkeypatch.setattr(rd, "read_lang", lambda: "fr")
    assert rd.pretty_name() == "Ajout de Hyprland"
    monkeypatch.setattr(rd, "read_lang", lambda: "en")
    assert rd.pretty_name() == "Adding Hyprland"


def test_job_name_never_moves_the_progress_line(rd, tmp_path, monkeypatch):
    # the progress line picks its stage from words of the job's name
    # (installStageRules in strings.js): this job sits in the download
    # stage and its name must match none of them
    strings = (MODULE.parents[5] / "etc/calamares/branding/raye/strings.js").read_text()
    rules = strings.split("var installStageRules", 1)[1].split("\n]\n", 1)[0]
    words = [w for block in re.findall(r"words: \[(.*?)\]", rules, re.S)
             for w in re.findall(r'"([^"]+)"', block)]
    assert len(words) > 20
    for choice in ("plasma", "hyprland"):
        answer(tmp_path, choice)
        for lang in ("en", "fr"):
            monkeypatch.setattr(rd, "read_lang", lambda lang=lang: lang)
            name = rd.pretty_name().lower()
            assert not [w for w in words if w in name], name


# --- the pool on the stick ---------------------------------------------------

def test_pool_offers_the_package(rd, tmp_path):
    assert rd.pool_offers(str(make_pool(tmp_path)), "raye-hyprland")


def test_pool_index_may_be_compressed(rd, tmp_path):
    assert rd.pool_offers(str(make_pool(tmp_path, gz=True)), "raye-hyprland")


def test_pool_without_the_package(rd, tmp_path):
    pool = make_pool(tmp_path, entries="Package: raye-hyprland-extras\nVersion: 1\n\n")
    assert not rd.pool_offers(str(pool), "raye-hyprland")


def test_no_pool(rd, tmp_path):
    assert not rd.pool_offers(str(tmp_path / "nothing"), "raye-hyprland")


# --- KDE Plasma: nothing happens ----------------------------------------------

def test_plasma_touches_nothing(rd, tmp_path):
    root = make_root(tmp_path)
    before = sorted(str(p) for p in root.rglob("*"))
    target = Target(root)
    run(rd, root, target, pool=make_pool(tmp_path))
    assert target.calls == []
    assert sorted(str(p) for p in root.rglob("*")) == before
    assert not os.path.exists(rd.RESULT)


# --- Hyprland -------------------------------------------------------------------

def test_hyprland_installs_from_the_stick_and_never_goes_online(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    pool = make_pool(tmp_path)
    answer(tmp_path, "hyprland")
    target = Target(root)
    run(rd, root, target, pool=pool)
    assert len(target.calls) == 2
    update, install = target.calls
    assert "update" in update and "install" in install
    assert install[-1] == "raye-hyprland"
    for cmd in target.calls:
        sources = [a for a in cmd if a.startswith("Dir::Etc::SourceList=")]
        parts = [a for a in cmd if a.startswith("Dir::Etc::SourceParts=")]
        lists = [a for a in cmd if a.startswith("Dir::State::Lists=")]
        assert sources and parts and lists, cmd
    # the only source apt knows of is the pool, as the new system sees it
    assert not (root / "var/tmp/raye-desktop").exists(), "the temporary apt files were left behind"
    assert target.sources == [f"deb [trusted=yes] file:{pool} ./\n"] * 2


def test_hyprland_from_the_network_without_a_pool(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    answer(tmp_path, "hyprland")
    target = Target(root)
    run(rd, root, target, pool=tmp_path / "no-pool")
    assert len(target.calls) == 1
    install = target.calls[0]
    assert "install" in install and install[-1] == "raye-hyprland"
    assert not [a for a in install if a.startswith("Dir::")], "the network install must use the system's sources"


def test_hyprland_becomes_the_session_of_the_new_account(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    answer(tmp_path, "hyprland")
    run(rd, root, Target(root), pool=make_pool(tmp_path))
    state = root / "var/lib/sddm/state.conf"
    last = ini(state)["Last"]
    # SDDM 0.21 compares the absolute path of the session file
    assert last["Session"] == SESSION
    assert last["User"] == "ana"
    # given to sddm before it takes the file's name: the greeter reads it
    assert [owner for path, owner in chowns.items()
            if os.path.dirname(path) == str(state.parent)] == [(118, 124)]
    # KDE Plasma is still there to pick on the sign-in screen
    assert (root / "usr/share/wayland-sessions/plasma.desktop").is_file()


def test_sddm_state_keeps_what_was_in_it(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    (root / "var/lib/sddm/state.conf").write_text("[Last]\nUser=old\nSession=/x.desktop\n\n[Other]\nKey=1\n")
    answer(tmp_path, "hyprland")
    run(rd, root, Target(root), pool=make_pool(tmp_path))
    parsed = ini(root / "var/lib/sddm/state.conf")
    assert parsed["Last"]["Session"] == SESSION
    assert parsed["Last"]["User"] == "ana"
    assert parsed["Other"]["Key"] == "1"


def test_accounts_service_knows_the_session_and_keeps_the_hint(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    users = root / "var/lib/AccountsService/users"
    users.mkdir(parents=True)
    (users / "ana").write_text("[User]\nPasswordHint=cat\n")
    answer(tmp_path, "hyprland")
    run(rd, root, Target(root), pool=make_pool(tmp_path))
    user = ini(users / "ana")["User"]
    assert user["Session"] == "raye-hyprland"
    assert user["SessionType"] == "wayland"
    assert user["PasswordHint"] == "cat"
    assert (users / "ana").stat().st_mode & 0o777 == 0o600


def test_autologin_session_follows_when_the_file_names_one(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    (root / "etc/sddm.conf").write_text("[Autologin]\nSession=plasma\n")
    answer(tmp_path, "hyprland")
    run(rd, root, Target(root), pool=make_pool(tmp_path))
    assert ini(root / "etc/sddm.conf")["Autologin"]["Session"] == "raye-hyprland.desktop"


def test_no_sddm_conf_is_made_up(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    answer(tmp_path, "hyprland")
    run(rd, root, Target(root), pool=make_pool(tmp_path))
    assert not (root / "etc/sddm.conf").exists()


@pytest.mark.parametrize("codes", [{"install": 100}, {"update": 100}])
def test_a_failed_install_keeps_kde_and_says_so(rd, tmp_path, chowns, codes):
    root = make_root(tmp_path)
    answer(tmp_path, "hyprland")
    target = Target(root, codes=codes)
    run(rd, root, target, pool=make_pool(tmp_path))
    assert not (root / "var/lib/sddm/state.conf").exists()
    assert not (root / "var/lib/AccountsService").exists()
    assert pathlib.Path(rd.RESULT).read_text().strip() == "plasma-fallback"
    if "update" in codes:
        assert len(target.calls) == 1, "installed after the pool could not be read"


def test_a_broken_target_never_stops_the_install(rd, tmp_path, chowns, monkeypatch):
    root = make_root(tmp_path)
    answer(tmp_path, "hyprland")

    def no_room(*args, **kwargs):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(rd.os, "makedirs", no_room)
    run(rd, root, Target(root), pool=make_pool(tmp_path))
    assert pathlib.Path(rd.RESULT).read_text().strip() == "plasma-fallback"


def test_an_install_that_brings_no_session_keeps_kde(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    answer(tmp_path, "hyprland")
    run(rd, root, Target(root, lands=False), pool=make_pool(tmp_path))
    assert not (root / "var/lib/sddm/state.conf").exists()
    assert pathlib.Path(rd.RESULT).read_text().strip() == "plasma-fallback"


def test_a_link_in_place_of_the_state_file_is_refused(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    victim = tmp_path / "victim"
    victim.write_text("keep me\n")
    os.symlink(victim, root / "var/lib/sddm/state.conf")
    answer(tmp_path, "hyprland")
    run(rd, root, Target(root), pool=make_pool(tmp_path))
    assert victim.read_text() == "keep me\n"


@pytest.mark.parametrize("name", ["", "Ana", "../etc", "root/x"])
def test_odd_account_names_write_nothing_for_the_account(rd, tmp_path, chowns, name):
    root = make_root(tmp_path)
    answer(tmp_path, "hyprland")
    run(rd, root, Target(root), username=name, pool=make_pool(tmp_path))
    assert not (root / "var/lib/AccountsService").exists()
    assert not (root / "var/lib/sddm/state.conf").exists()


def test_no_sddm_account_leaves_the_state_alone(rd, tmp_path, chowns):
    root = make_root(tmp_path)
    (root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/bash\nana:x:1000:1000::/home/ana:/bin/bash\n")
    answer(tmp_path, "hyprland")
    run(rd, root, Target(root), pool=make_pool(tmp_path))
    assert not (root / "var/lib/sddm/state.conf").exists()
    # the account still gets its session where AccountsService keeps it
    assert ini(root / "var/lib/AccountsService/users/ana")["User"]["Session"] == "raye-hyprland"


def test_no_root_mount_point_does_nothing(rd, tmp_path):
    answer(tmp_path, "hyprland")
    target = Target(tmp_path)
    rd.libcalamares.utils.target_env_call = target
    assert rd.run() is None
    assert target.calls == []
