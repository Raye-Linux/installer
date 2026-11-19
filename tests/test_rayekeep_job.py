# SPDX-License-Identifier: GPL-3.0-or-later
"""The rayekeep job: its two steps, what it reads and what it leaves.

A made-up GlobalStorage and a target folder under tmp_path.
"""
import importlib.util
import json
import os
import pathlib
import sys
import types

import pytest

MODULES = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules"
sys.path.insert(0, str(MODULES / "rayedisk"))


class Storage(dict):
    def value(self, key):
        return self.get(key)

    def insert(self, key, value):
        self[key] = value


def load(monkeypatch, tmp_path, gs, step):
    lib = types.ModuleType("libcalamares")
    lib.globalstorage = gs
    lib.job = types.SimpleNamespace(setprogress=lambda part: None, working_path=str(MODULES / "rayekeep"),
                                    configuration={"step": step})
    lib.utils = types.SimpleNamespace(debug=lambda text: None, warning=lambda text: None)
    monkeypatch.setitem(sys.modules, "libcalamares", lib)
    spec = importlib.util.spec_from_file_location("rayekeep_main", MODULES / "rayekeep/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    os.mkdir(tmp_path / "root-only", 0o700)
    monkeypatch.setattr(module, "RESULT", str(tmp_path / "root-only/keep-result"))
    monkeypatch.setattr(module, "CHOICES", str(tmp_path / "choices"))
    return module


def home_target(tmp_path):
    root = tmp_path / "target"
    (root / "etc").mkdir(parents=True)
    (root / "etc/passwd").write_text("root:x:0:0::/root:/bin/sh\nalice:x:4321:4321::/home/alice:/bin/bash\n")
    (root / "home/alice/Pictures").mkdir(parents=True)
    (root / "home/alice/Pictures/cat.png").write_bytes(b"png")
    (root / "home/alice/.profile").write_text("old")
    return root


def kept_home():
    return {"way": "home", "name": "Fedora Linux 42", "home": "/dev/sda3", "users": [
        {"name": "alice", "home": "alice", "uid": 1000, "folders": [{"kind": "pictures", "path": "Pictures",
                                                                     "files": 1, "bytes": 3}]}]}


def test_nothing_kept_does_nothing(monkeypatch, tmp_path):
    job = load(monkeypatch, tmp_path, Storage(), "copy")
    assert job.run() is None
    assert not os.path.exists(job.RESULT)


@pytest.mark.skipif(os.geteuid() != 0, reason="giving files to the account needs root")
def test_both_steps_bring_a_kept_home_into_the_account(monkeypatch, tmp_path):
    root = home_target(tmp_path)
    gs = Storage(rayeKeep=kept_home(), rootMountPoint=str(root), username="alice")
    (tmp_path / "choices").write_text("lang=fr\n")
    load(monkeypatch, tmp_path, gs, "prepare").run()
    assert gs["rayeKeepMovedAside"] == "alice.old"
    # what usersq does in between
    (root / "home/alice").mkdir()
    os.makedirs(tmp_path / "second")
    (tmp_path / "second/choices").write_text("lang=fr\n")
    job = load(monkeypatch, tmp_path / "second", gs, "copy")
    assert job.run() is None
    assert (root / "home/alice/Images/cat.png").read_bytes() == b"png"
    assert (root / "home/alice.old/.profile").read_text() == "old"
    result = json.loads(pathlib.Path(job.RESULT).read_text())
    assert result["ok"] and result["name"] == "Fedora Linux 42"
    assert job.pretty_name() == "Transfert de vos fichiers"


def test_a_failure_never_stops_the_install(monkeypatch, tmp_path):
    gs = Storage(rayeKeep=dict(kept_home(), way="stage", stage="/dev/sda3"), rootMountPoint=str(tmp_path),
                 username="nobody-here")
    job = load(monkeypatch, tmp_path, gs, "copy")
    assert job.run() is None
    result = json.loads(pathlib.Path(job.RESULT).read_text())
    assert result == {"way": "stage", "name": "Fedora Linux 42", "ok": False, "files": 0, "failed": 1,
                      "left": True}


def test_the_disk_job_mounts_a_kept_home_and_hands_the_rest_over():
    spec = importlib.util.spec_from_file_location("rayedisk_finish_job", MODULES / "rayedisk/rayedisk_finish.py")
    finish = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(finish)
    plan = {"disk": "/dev/sda", "hardware": "hw", "label": "gpt", "mode": "keep", "stage": None,
            "add": [{"role": "boot", "start": 10, "sectors": 5}, {"role": "root", "start": 15, "sectors": 50}],
            "keep": dict(kept_home(), homeFs="ext4", files=1, bytes=3)}
    made = [{"device": "/dev/sda4", "mountPoint": "/"}, {"device": "/dev/sda3", "mountPoint": "/home"}]
    kept = finish.keep_storage(plan, made)
    assert kept["way"] == "home" and kept["home"] == "/dev/sda3"
    assert kept["root"] == "/dev/sda4" and kept["rootStart"] == 15 and kept["rootSectors"] == 50
    assert kept["users"][0]["folders"][0] == {"kind": "pictures", "path": "Pictures", "files": 1, "bytes": 3}
    assert finish.keep_storage(dict(plan, keep=None), made) is None
