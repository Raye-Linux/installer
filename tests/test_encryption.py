# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the disk encryption step, without Calamares or a TPM."""
import importlib.util
import os
import pathlib
import re
import subprocess
import sys
import types

import pytest

MODULE = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayeencryption/main.py"


@pytest.fixture
def enc(monkeypatch):
    monkeypatch.setitem(sys.modules, "libcalamares", types.ModuleType("libcalamares"))
    spec = importlib.util.spec_from_file_location("rayeencryption", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_run(failing_banks, calls):
    def run(argv, **kwargs):
        calls.append(argv[-1])
        if any(f'"pcr_bank":"{bank}"' in argv[-1] for bank in failing_banks):
            raise subprocess.CalledProcessError(1, argv, stderr=b"no such bank")
        return subprocess.CompletedProcess(argv, 0)
    return run


def test_sha256_bank_is_tried_first(enc, monkeypatch):
    calls = []
    monkeypatch.setattr(enc.subprocess, "run", fake_run([], calls))
    used = enc.bind_tpm("/target", "/dev/vda3", "secret")
    assert '"pcr_bank":"sha256"' in used
    assert len(calls) == 1


def test_falls_back_to_sha1_on_old_chips(enc, monkeypatch):
    calls = []
    monkeypatch.setattr(enc.subprocess, "run", fake_run(["sha256"], calls))
    used = enc.bind_tpm("/target", "/dev/vda3", "secret")
    assert '"pcr_bank":"sha1"' in used
    assert len(calls) == 2


def test_raises_when_no_bank_works(enc, monkeypatch):
    calls = []
    monkeypatch.setattr(enc.subprocess, "run", fake_run(["sha256", "sha1"], calls))
    with pytest.raises(subprocess.CalledProcessError):
        enc.bind_tpm("/target", "/dev/vda3", "secret")
    assert len(calls) == 2


def test_passphrase_goes_through_stdin_not_argv(enc, monkeypatch):
    seen = {}

    def run(argv, **kwargs):
        seen["argv"], seen["input"] = argv, kwargs.get("input")
        return subprocess.CompletedProcess(argv, 0)
    monkeypatch.setattr(enc.subprocess, "run", run)
    enc.bind_tpm("/target", "/dev/vda3", "secret")
    assert "secret" not in " ".join(seen["argv"])
    assert seen["input"] == b"secret"


def test_recovery_key_is_eight_groups_of_six_digits(enc):
    key = enc.new_recovery_key()
    groups = key.split("-")
    assert len(groups) == 8
    assert all(len(g) == 6 and g.isdigit() for g in groups)


class FakeStorage(dict):
    def value(self, key):
        return self.get(key)

    def insert(self, key, value):
        self[key] = value

    def remove(self, key):
        self.pop(key, None)


def run_with(enc, monkeypatch, tpm_bound):
    gs = FakeStorage(rootMountPoint="/target", username="ana", autoLoginUser="ana",
                     partitions=[{"luksMapperName": "luks-x", "device": "/dev/vda3",
                                  "luksPassphrase": "secret"}])
    enc.libcalamares.globalstorage = gs
    enc.libcalamares.utils = types.SimpleNamespace(debug=lambda *a: None,
                                                    warning=lambda *a: None)
    monkeypatch.setattr(enc, "add_recovery_key", lambda *a: None)
    monkeypatch.setattr(enc, "save_recovery_key", lambda *a: None)
    monkeypatch.setattr(enc, "leave_notice", lambda *a: None)
    monkeypatch.setattr(enc, "rewrite_crypttab_header", lambda *a: None)
    monkeypatch.setattr(enc.os.path, "exists", lambda path: tpm_bound)
    monkeypatch.setattr(enc, "bind_tpm", lambda *a: '{"pcr_bank":"sha256"}')
    assert enc.run() is None
    return gs


def test_tpm_unlock_turns_automatic_login_off(enc, monkeypatch):
    gs = run_with(enc, monkeypatch, tpm_bound=True)
    assert "autoLoginUser" not in gs


def test_automatic_login_kept_without_tpm(enc, monkeypatch):
    gs = run_with(enc, monkeypatch, tpm_bound=False)
    assert gs["autoLoginUser"] == "ana"


# --- /etc/crypttab header ---------------------------------------------------

# Shaped like the comment block Calamares' fstab job writes (its
# CRYPTTAB_HEADER, read for real in the last test), then entries the way
# print_crypttab_line lays them out, odd spacing and all.
CALAMARES_CRYPTTAB = (
    b"# /etc/crypttab: mappings for encrypted partitions.\n"
    b"#\n"
    b"# Each mapped device will be created in /dev/mapper, so your /etc/fstab\n"
    b"# should use the /dev/mapper/<name> paths for encrypted devices.\n"
    b"#\n"
    b"# See crypttab(5) for the supported syntax.\n"
    b"#\n"
    b"# NOTE: the root (/) partition is opened by the initramfs, before this\n"
    b"#       file is read; encrypted swap the same way, for resume.\n"
    b"#\n"
    b"# <name>               <device>                         <password> <options>\n"
)
ENTRIES = (
    b"luks-0a1b2c3d         UUID=0a1b2c3d-1111-2222-3333-444455556666 /crypto_keyfile.bin luks\n"
    b"luks-swap             UUID=99999999-1111-2222-3333-444455556666 none \n"
    b"\tluks-odd\tUUID=x\tnone\tluks,discard\n"
)
NEW_HEADER = (b"# Encrypted disks Raye opens at startup (see crypttab(5)).\n"
              b"# Written by the Raye installer.\n")


def write_crypttab(tmp_path, data):
    (tmp_path / "etc").mkdir(exist_ok=True)
    path = tmp_path / "etc/crypttab"
    path.write_bytes(data)
    path.chmod(0o600)
    return path


def test_crypttab_header_rewritten_entries_kept_byte_for_byte(enc, tmp_path):
    path = write_crypttab(tmp_path, CALAMARES_CRYPTTAB + ENTRIES)
    enc.rewrite_crypttab_header(str(tmp_path))
    assert path.read_bytes() == NEW_HEADER + ENTRIES
    assert path.stat().st_mode & 0o777 == 0o600


def test_nothing_of_the_old_comment_is_left(enc, tmp_path):
    path = write_crypttab(tmp_path, CALAMARES_CRYPTTAB + ENTRIES)
    enc.rewrite_crypttab_header(str(tmp_path))
    lines = path.read_bytes().splitlines(keepends=True)
    for old in CALAMARES_CRYPTTAB.splitlines(keepends=True):
        assert old not in lines


def test_crypttab_without_entries_gets_only_the_header(enc, tmp_path):
    path = write_crypttab(tmp_path, CALAMARES_CRYPTTAB)
    enc.rewrite_crypttab_header(str(tmp_path))
    assert path.read_bytes() == NEW_HEADER


def test_crypttab_rewrite_twice_is_the_same(enc, tmp_path):
    path = write_crypttab(tmp_path, CALAMARES_CRYPTTAB + ENTRIES)
    enc.rewrite_crypttab_header(str(tmp_path))
    enc.rewrite_crypttab_header(str(tmp_path))
    assert path.read_bytes() == NEW_HEADER + ENTRIES


def test_comments_after_the_first_entry_are_entries_too(enc, tmp_path):
    later = b"luks-a UUID=a none luks\n# keep me\nluks-b UUID=b none luks\n"
    path = write_crypttab(tmp_path, CALAMARES_CRYPTTAB + later)
    enc.rewrite_crypttab_header(str(tmp_path))
    assert path.read_bytes() == NEW_HEADER + later


def test_no_crypttab_nothing_written(enc, tmp_path):
    enc.rewrite_crypttab_header(str(tmp_path))
    assert not (tmp_path / "etc/crypttab").exists()


def test_crypttab_link_is_not_followed(enc, tmp_path):
    (tmp_path / "etc").mkdir()
    victim = tmp_path / "victim"
    victim.write_bytes(b"leave me\n")
    (tmp_path / "etc/crypttab").symlink_to(victim)
    enc.rewrite_crypttab_header(str(tmp_path))
    assert victim.read_bytes() == b"leave me\n"


def test_header_rewritten_on_installs_without_encryption(enc, monkeypatch, tmp_path):
    path = write_crypttab(tmp_path, CALAMARES_CRYPTTAB)
    enc.libcalamares.globalstorage = FakeStorage(rootMountPoint=str(tmp_path), partitions=[])
    enc.libcalamares.utils = types.SimpleNamespace(debug=lambda *a: None,
                                                    warning=lambda *a: None)
    assert enc.run() is None
    assert path.read_bytes() == NEW_HEADER


# --- where the recovery key is kept ------------------------------------------

def make_home(tmp_path):
    (tmp_path / "etc").mkdir(exist_ok=True)
    (tmp_path / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/bash\n"
                                        "ana:x:1000:1000:Ana:/home/ana:/bin/bash\n")
    (tmp_path / "home/ana").mkdir(parents=True)
    return tmp_path / "home/ana"


@pytest.fixture
def chowns(enc, monkeypatch):
    seen = {}
    monkeypatch.setattr(enc.os, "chown", lambda path, uid, gid: seen.__setitem__(str(path), (uid, gid)))
    return seen


KEY = "123456-234567-345678-456789-567890-678901-789012-890123"


def test_recovery_key_kept_where_first_run_reads_it(enc, tmp_path, chowns):
    home = make_home(tmp_path)
    enc.save_recovery_key(str(tmp_path), "ana", KEY)
    path = home / ".local/share/raye/recovery-key"
    assert path.read_text() == KEY + "\n"
    assert path.stat().st_mode & 0o777 == 0o600
    assert (home / ".local/share/raye").stat().st_mode & 0o777 == 0o700
    for part in (".local", ".local/share", ".local/share/raye", ".local/share/raye/recovery-key"):
        assert chowns[str(home / part)] == (1000, 1000)


def with_first_run(root):
    (root / "usr/bin").mkdir(parents=True)
    (root / "usr/bin/raye-first-run").write_text("")


def test_no_key_text_file_and_no_popup_with_the_first_run_welcome(enc, tmp_path, chowns):
    home = make_home(tmp_path)
    with_first_run(tmp_path)
    enc.save_recovery_key(str(tmp_path), "ana", KEY)
    assert enc.leave_notice(str(tmp_path), "ana", KEY, True, "en") is None
    assert not (home / "Raye recovery key.txt").exists()
    assert not (home / ".config").exists()


def test_without_the_first_run_welcome_the_key_is_shown_once(enc, tmp_path, chowns):
    home = make_home(tmp_path)
    path = enc.leave_notice(str(tmp_path), "ana", KEY, False, "en")
    notice = home / ".config/autostart/raye-recovery-key.desktop"
    assert path == str(notice)
    assert notice.read_text().startswith("[Desktop Entry]\nType=Application\n")
    assert notice.stat().st_mode & 0o777 == 0o600
    # the message and the key are in the script the entry runs
    text = (home / ".local/share/raye/recovery-key-notice").read_text()
    assert KEY in text
    assert "asks for its password" in text
    assert (home / ".local/share/raye").stat().st_mode & 0o777 == 0o700
    for part in (".config", ".config/autostart", ".config/autostart/raye-recovery-key.desktop",
                 ".local", ".local/share", ".local/share/raye",
                 ".local/share/raye/recovery-key-notice"):
        assert chowns[str(home / part)] == (1000, 1000)


def test_key_message_in_french(enc):
    for lang in ("en", "fr"):
        for tpm in (True, False):
            assert KEY in enc.notice_text(lang, KEY, tpm)
    assert "déverrouille son disque tout seul" in enc.notice_text("fr", KEY, True)
    assert enc.notice_text("xx", KEY, True) == enc.notice_text("en", KEY, True)


def split_exec(value):
    """Exec= value to argv the way the desktop entry spec reads it."""
    value = re.sub(r"\\(.)", lambda m: {"s": " ", "n": "\n", "t": "\t", "r": "\r"}
                   .get(m.group(1), m.group(1)), value)
    argv, arg, quoted, i, started = [], "", False, 0, False
    while i < len(value):
        c = value[i]
        if quoted and c == "\\":
            i += 1
            arg += value[i]
        elif c == '"':
            quoted, started = not quoted, True
        elif c == " " and not quoted:
            if started or arg:
                argv.append(arg)
            arg, started = "", False
        else:
            arg += c
        i += 1
    if started or arg:
        argv.append(arg)
    return [a.replace("%%", "%") for a in argv]


def test_exec_line_gives_back_every_argument(enc):
    argv = ["/bin/sh", "-c", 'kdialog --msgbox "$1"; exec rm -f -- "$0"', "/home/ana/x y.desktop", "Raye Linux",
            "it's 100% \"fine\" $HOME `id` \\ end", ""]
    assert split_exec(enc.desktop_exec(argv)) == argv
    with pytest.raises(ValueError):
        enc.desktop_exec(["a\nb"])


def test_notice_file_runs_the_message_then_removes_itself(enc, tmp_path, chowns):
    home = make_home(tmp_path)
    path = enc.leave_notice(str(tmp_path), "ana", KEY, True, "fr")
    line = next(l for l in open(path).read().splitlines() if l.startswith("Exec="))
    # The session starts autostart files through systemd's generator, which
    # reads backslashes only once: no "$", quote or backslash in the line.
    assert not set('$"\\\'`').intersection(line)
    script = home / ".local/share/raye/recovery-key-notice"
    # the script as the installed system sees it, not under the target
    assert split_exec(line[len("Exec="):]) == ["/bin/sh", "/home/ana/.local/share/raye/recovery-key-notice"]
    assert script.stat().st_mode & 0o777 == 0o700
    assert chowns[str(script)] == (1000, 1000)
    assert KEY in script.read_text()
    assert "/home/ana/.config/autostart/raye-recovery-key.desktop" in script.read_text()


def test_notice_script_shows_the_text_then_removes_both_files(enc, tmp_path):
    entry, script, seen = tmp_path / "entry.desktop", tmp_path / "it's notice", tmp_path / "seen"
    entry.write_text("x")
    message = enc.notice_text("fr", KEY, True) + " $HOME `id` \"" + "'"
    script.write_text(enc.notice_script("Raye Linux", message, [str(entry), str(script)]))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "kdialog"
    fake.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{seen}"\n')
    fake.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:/usr/bin:/bin")
    subprocess.run(["/bin/sh", str(script)], check=True, env=env)
    assert seen.read_text().splitlines() == ["--title", "Raye Linux", "--icon", "dialog-password",
                                             "--msgbox", *message.splitlines()]
    assert not entry.exists() and not script.exists()


def test_key_message_never_written_through_a_link(enc, tmp_path, chowns):
    home = make_home(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (home / ".config").symlink_to(elsewhere)
    with pytest.raises(OSError):
        enc.leave_notice(str(tmp_path), "ana", KEY, True, "en")
    assert not any(elsewhere.iterdir())


def test_unwritable_crypttab_does_not_fail_the_install(enc, monkeypatch, tmp_path):
    def broken(root):
        raise PermissionError("read-only")
    warnings = []
    monkeypatch.setattr(enc, "rewrite_crypttab_header", broken)
    enc.libcalamares.globalstorage = FakeStorage(rootMountPoint=str(tmp_path), partitions=[])
    enc.libcalamares.utils = types.SimpleNamespace(debug=lambda *a: None,
                                                    warning=warnings.append)
    assert enc.run() is None
    assert warnings and "crypttab" in warnings[0]


def test_recovery_key_never_written_through_a_link(enc, tmp_path, chowns):
    home = make_home(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (home / ".local").symlink_to(elsewhere)
    with pytest.raises(OSError):
        enc.save_recovery_key(str(tmp_path), "ana", KEY)
    assert not any(elsewhere.iterdir())


def test_recovery_key_skipped_without_a_home(enc, tmp_path, chowns):
    (tmp_path / "etc").mkdir()
    (tmp_path / "etc/passwd").write_text("ana:x:1000:1000:Ana:/home/ana:/bin/bash\n")
    assert enc.save_recovery_key(str(tmp_path), "ana", KEY) is None
    assert enc.save_recovery_key(str(tmp_path), "../root", KEY) is None


def test_job_texts_in_french_when_setup_ran_in_french(enc, monkeypatch, tmp_path):
    choices = tmp_path / "choices"
    choices.write_text("lang=fr\nlayout=ca\n")
    monkeypatch.setattr(enc, "CHOICES", str(choices))
    assert enc.pretty_name() == "Configuration du chiffrement du disque"
    choices.write_text("lang=xx\n")
    assert enc.pretty_name() == "Setting up disk encryption"


def calamares_crypttab_header():
    """CRYPTTAB_HEADER of the Calamares on this machine, read without importing it."""
    import ast
    import glob
    for path in glob.glob("/usr/lib/*/calamares/modules/fstab/main.py"):
        for node in ast.parse(pathlib.Path(path).read_text()).body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "CRYPTTAB_HEADER":
                return node.value.value
    return None


def test_the_installed_calamares_header_is_replaced(enc, tmp_path):
    header = calamares_crypttab_header()
    if header is None:
        pytest.skip("Calamares is not installed here")
    # fstab's generate_crypttab: print(CRYPTTAB_HEADER), then the entries
    path = write_crypttab(tmp_path, header.encode() + b"\n" + ENTRIES)
    enc.rewrite_crypttab_header(str(tmp_path))
    assert path.read_bytes() == NEW_HEADER + ENTRIES


def test_the_notice_keeps_itself_when_the_box_never_opened(enc, tmp_path):
    """A notice that could not be shown must still be there next time.

    🚨 The script ran `kdialog ...` and then `exec rm -f` on its own two
    files, whatever kdialog had done. kdialog is NOT a dependency of the
    installed system: it comes in behind raye-windows-apps, and both
    debian/control here and iso/packages/raye-base/debian/control say it
    is on its way out ("the setup app takes over every dialog box, and
    then kdialog goes", "drop kdialog above once SW-11's runner lands").
    The day it goes, this script would have deleted the only message
    about the recovery key without showing it and without a word.

    A kdialog that exits 127, the way a missing one does, stands in here
    so the check behaves the same on a machine that has kdialog and on
    one that does not.
    """
    entry, script = tmp_path / "entry.desktop", tmp_path / "notice"
    entry.write_text("x")
    script.write_text(enc.notice_script("Raye Linux", "the key is in a file", [str(entry), str(script)]))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    missing = bin_dir / "kdialog"
    missing.write_text("#!/bin/sh\nexit 127\n")
    missing.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:/usr/bin:/bin")
    done = subprocess.run(["/bin/sh", str(script)], env=env, capture_output=True)
    assert done.returncode != 0, "the script claims success though nothing was shown"
    assert entry.exists(), "the autostart entry removed itself unseen"
    assert script.exists(), "the notice removed itself unseen"
