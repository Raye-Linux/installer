# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the step that carries the setup app's choices to the new system."""
import importlib.util
import os
import pathlib
import sys
import types

import pytest

MODULE = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayesetupchoices/main.py"

STOCK_KEYBOARD = (
    b"# KEYBOARD CONFIGURATION FILE\n"
    b"\n"
    b"# Consult the keyboard(5) manual page.\n"
    b"\n"
    b'XKBMODEL="pc105"\n'
    b'XKBLAYOUT="us"\n'
    b'XKBVARIANT=""\n'
    b'XKBOPTIONS="compose:ralt"\n'
    b"\n"
    b'BACKSPACE="guess"\n'
)


@pytest.fixture
def sc(monkeypatch):
    fake = types.ModuleType("libcalamares")
    fake.utils = types.SimpleNamespace(debug=lambda *a: None, warning=lambda *a: None)
    monkeypatch.setitem(sys.modules, "libcalamares", fake)
    spec = importlib.util.spec_from_file_location("rayesetupchoices", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeStorage(dict):
    def value(self, key):
        return self.get(key)


@pytest.fixture
def chowns(sc, monkeypatch):
    seen = {}
    monkeypatch.setattr(sc.os, "chown", lambda path, uid, gid: seen.__setitem__(str(path), (uid, gid)))
    return seen


def make_root(tmp_path, home=True):
    root = tmp_path / "target"
    (root / "etc/default").mkdir(parents=True)
    (root / "etc/passwd").write_text(
        "root:x:0:0:root:/root:/bin/bash\n"
        "ana:x:1000:1000:Ana,,,:/home/ana:/bin/bash\n")
    if home:
        (root / "home/ana").mkdir(parents=True)
    return root


def write_choices(tmp_path, text):
    path = tmp_path / "choices"
    path.write_text(text)
    return str(path)


# --- the choices file ---------------------------------------------------

def test_reads_key_value_lines(sc, tmp_path):
    path = write_choices(tmp_path, "lang=fr\nlocale=fr_CA.UTF-8\nlayout=ca\n"
                                   "variant=fr\nregion=CA\nwindows=yes\n")
    assert sc.read_choices(path) == {"lang": "fr", "locale": "fr_CA.UTF-8", "layout": "ca",
                                     "variant": "fr", "region": "CA", "windows": "yes"}


def test_skips_comments_blank_and_broken_lines(sc, tmp_path):
    path = write_choices(tmp_path, "# written by raye-setup\n\n  layout = fr \nnonsense\n"
                                   'variant="oss"\n')
    assert sc.read_choices(path) == {"layout": "fr", "variant": "oss"}


def test_missing_choices_file_is_empty(sc, tmp_path):
    assert sc.read_choices(str(tmp_path / "nothing")) == {}


def test_layout_names_that_could_break_a_file_are_refused(sc):
    assert sc.clean_layout("ca", "fr") == ("ca", "fr")
    assert sc.clean_layout("us", "") == ("us", "")
    assert sc.clean_layout("de", "nodeadkeys") == ("de", "nodeadkeys")
    assert sc.clean_layout('fr"\nXKBOPTIONS="evil', "") == (None, "")
    assert sc.clean_layout("fr", "a$(reboot)") == ("fr", "")
    assert sc.clean_layout("", "fr") == (None, "")


# --- keyboard files -------------------------------------------------------

def test_default_keyboard_changes_only_layout_and_variant(sc, tmp_path):
    root = make_root(tmp_path)
    (root / "etc/default/keyboard").write_bytes(STOCK_KEYBOARD)
    sc.write_default_keyboard(str(root), "ca", "fr")
    assert (root / "etc/default/keyboard").read_bytes() == STOCK_KEYBOARD.replace(
        b'XKBLAYOUT="us"', b'XKBLAYOUT="ca"').replace(b'XKBVARIANT=""', b'XKBVARIANT="fr"')
    assert os.stat(root / "etc/default/keyboard").st_mode & 0o777 == 0o644


def test_default_keyboard_written_when_missing(sc, tmp_path):
    root = make_root(tmp_path)
    sc.write_default_keyboard(str(root), "fr", "")
    text = (root / "etc/default/keyboard").read_text()
    assert 'XKBLAYOUT="fr"\n' in text
    assert 'XKBVARIANT=""\n' in text
    assert 'XKBMODEL="pc105"\n' in text
    assert 'BACKSPACE="guess"\n' in text


def test_default_keyboard_adds_lines_it_does_not_find(sc, tmp_path):
    root = make_root(tmp_path)
    (root / "etc/default/keyboard").write_text('XKBMODEL="pc105"\n')
    sc.write_default_keyboard(str(root), "fr", "oss")
    assert (root / "etc/default/keyboard").read_text() == (
        'XKBMODEL="pc105"\nXKBLAYOUT="fr"\nXKBVARIANT="oss"\n')


def test_users_kxkbrc(sc, tmp_path, chowns):
    root = make_root(tmp_path)
    path = sc.write_kxkbrc(str(root), "ana", "ca", "fr")
    assert path == str(root / "home/ana/.config/kxkbrc")
    assert (root / "home/ana/.config/kxkbrc").read_text() == (
        "[Layout]\nLayoutList=ca\nUse=true\nVariantList=fr\n")
    assert chowns[str(root / "home/ana/.config")] == (1000, 1000)
    assert chowns[str(root / "home/ana/.config/kxkbrc")] == (1000, 1000)


def test_kxkbrc_goes_to_skel_when_the_account_is_not_made_yet(sc, tmp_path, chowns):
    root = make_root(tmp_path, home=False)
    path = sc.write_kxkbrc(str(root), "ana", "fr", "")
    assert path == str(root / "etc/skel/.config/kxkbrc")
    assert "LayoutList=fr\n" in (root / "etc/skel/.config/kxkbrc").read_text()
    assert not chowns


def test_kxkbrc_never_follows_a_link(sc, tmp_path, chowns):
    root = make_root(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / "home/ana/.config").symlink_to(elsewhere)
    with pytest.raises(OSError):
        sc.write_kxkbrc(str(root), "ana", "fr", "")
    assert not any(elsewhere.iterdir())


def test_odd_user_names_are_refused(sc, tmp_path, chowns):
    root = make_root(tmp_path)
    assert sc.write_kxkbrc(str(root), "../etc", "fr", "") is None
    assert sc.write_kxkbrc(str(root), "", "fr", "") is None


# --- clock when Windows is on the disk -----------------------------------

def test_windows_from_the_choices_file(sc, tmp_path):
    root = make_root(tmp_path)
    assert sc.windows_found({"windows": "yes"}, str(root), "/boot/efi") is True
    assert sc.windows_found({"windows": "no"}, str(root), "/boot/efi") is False


def test_windows_boot_manager_on_the_new_esp_when_the_file_says_nothing(sc, tmp_path):
    root = make_root(tmp_path)
    assert sc.windows_found({}, str(root), "/boot/efi") is False
    boot = root / "boot/efi/EFI/Microsoft/Boot"
    boot.mkdir(parents=True)
    (boot / "bootmgfw.efi").write_bytes(b"MZ")
    assert sc.windows_found({}, str(root), "/boot/efi") is True


def test_rtc_local_writes_adjtime_when_missing(sc, tmp_path):
    root = make_root(tmp_path)
    calls = []
    sc.set_rtc_local(str(root), lambda argv: calls.append(argv) or 0)
    assert calls == [["hwclock", "--systohc", "--localtime"]]
    assert (root / "etc/adjtime").read_text() == "0.0 0 0.0\n0\nLOCAL\n"


def test_rtc_local_keeps_drift_lines(sc, tmp_path):
    root = make_root(tmp_path)
    (root / "etc/adjtime").write_text("0.000000 1761900000 0.000000\n1761900000\nUTC\n")
    sc.set_rtc_local(str(root), lambda argv: 1)   # no RTC: the file is still right
    assert (root / "etc/adjtime").read_text() == (
        "0.000000 1761900000 0.000000\n1761900000\nLOCAL\n")


# --- the whole step --------------------------------------------------------

def run_job(sc, monkeypatch, tmp_path, choices, gs_extra=None, home=True, root=None):
    root = root or make_root(tmp_path, home=home)
    # the pages' answers, if a test wrote any (see answers())
    monkeypatch.setattr(sc, "ANSWERS", str(tmp_path / "run"))
    (root / "etc/default/keyboard").write_bytes(STOCK_KEYBOARD)
    (root / "etc/adjtime").write_text("0.0 0 0.0\n0\nUTC\n")
    if choices is not None:
        monkeypatch.setattr(sc, "CHOICES", write_choices(tmp_path, choices))
    else:
        monkeypatch.setattr(sc, "CHOICES", str(tmp_path / "no-such-file"))
    gs = FakeStorage(rootMountPoint=str(root), username="ana", **(gs_extra or {}))
    calls = []
    sc.libcalamares.globalstorage = gs
    sc.libcalamares.utils = types.SimpleNamespace(
        debug=lambda *a: None, warning=lambda *a: None,
        target_env_call=lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(sc.os, "chown", lambda *a: None)
    assert sc.run() is None
    return root, calls


def test_job_with_windows(sc, monkeypatch, tmp_path):
    root, calls = run_job(sc, monkeypatch, tmp_path,
                          "lang=fr\nlocale=fr_CA.UTF-8\nlayout=ca\nvariant=fr\nwindows=yes\n")
    assert b'XKBLAYOUT="ca"' in (root / "etc/default/keyboard").read_bytes()
    assert "LayoutList=ca\n" in (root / "home/ana/.config/kxkbrc").read_text()
    assert (root / "etc/adjtime").read_text().splitlines()[2] == "LOCAL"
    assert ["hwclock", "--systohc", "--localtime"] in calls


def test_job_without_windows_leaves_the_clock_alone(sc, monkeypatch, tmp_path):
    root, calls = run_job(sc, monkeypatch, tmp_path, "layout=fr\nwindows=no\n")
    assert (root / "etc/adjtime").read_text() == "0.0 0 0.0\n0\nUTC\n"
    assert calls == []


def test_owner_choice_is_one_switch(sc, monkeypatch, tmp_path):
    monkeypatch.setattr(sc, "RTC_LOCAL_WITH_WINDOWS", False)
    root, calls = run_job(sc, monkeypatch, tmp_path, "layout=fr\nwindows=yes\n")
    assert (root / "etc/adjtime").read_text() == "0.0 0 0.0\n0\nUTC\n"
    assert calls == []


def test_job_falls_back_to_the_installer_keyboard_page(sc, monkeypatch, tmp_path):
    root, _ = run_job(sc, monkeypatch, tmp_path, None,
                      {"keyboardLayout": "de", "keyboardVariant": "nodeadkeys"})
    assert b'XKBLAYOUT="de"' in (root / "etc/default/keyboard").read_bytes()
    assert b'XKBVARIANT="nodeadkeys"' in (root / "etc/default/keyboard").read_bytes()


def test_job_with_nothing_to_go_on_changes_nothing(sc, monkeypatch, tmp_path):
    root, calls = run_job(sc, monkeypatch, tmp_path, None)
    assert (root / "etc/default/keyboard").read_bytes() == STOCK_KEYBOARD
    assert not (root / "home/ana/.config/kxkbrc").exists()
    assert calls == []


def test_job_name_follows_the_chosen_language(sc, monkeypatch, tmp_path):
    monkeypatch.setattr(sc, "CHOICES", write_choices(tmp_path, "lang=fr\n"))
    assert sc.pretty_name() == "Configuration du clavier et de l'horloge"
    monkeypatch.setattr(sc, "CHOICES", write_choices(tmp_path, "lang=en\n"))
    assert sc.pretty_name() == "Setting up the keyboard and clock"


# --- what the Setup pages left (/run/raye-setup/answer-*) ----------------

def answers(sc, monkeypatch, tmp_path, **found):
    folder = tmp_path / "run"
    folder.mkdir(exist_ok=True)
    for key, text in found.items():
        (folder / f"answer-{key.replace('_', '-')}").write_text(text)
    monkeypatch.setattr(sc, "ANSWERS", str(folder))


def test_answer_is_read_trimmed_and_missing_is_empty(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path, hostname="  raye-pc \n")
    assert sc.read_answer("hostname") == "raye-pc"
    assert sc.read_answer("privacy") == ""


def test_answer_names_cannot_leave_the_folder(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path)
    (tmp_path / "secret").write_text("x")
    assert sc.read_answer("../secret") == ""


def test_second_layout_goes_to_the_desktop_only(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path, second_layout="ca")
    root, _ = run_job(sc, monkeypatch, tmp_path, None, {"keyboardLayout": "us", "keyboardVariant": ""})
    assert b'XKBLAYOUT="us"' in (root / "etc/default/keyboard").read_bytes()
    text = (root / "home/ana/.config/kxkbrc").read_text()
    assert "LayoutList=us,ca\n" in text
    assert "VariantList=,\n" in text


def test_second_layout_that_could_break_the_file_is_dropped(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path, second_layout="ca\nUse=false")
    root, _ = run_job(sc, monkeypatch, tmp_path, None, {"keyboardLayout": "us", "keyboardVariant": ""})
    assert "LayoutList=us\n" in (root / "home/ana/.config/kxkbrc").read_text()


def test_password_hint_goes_to_accountsservice(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path, password_hint="my cat\x07 Tom\n[User]")
    root, _ = run_job(sc, monkeypatch, tmp_path, None, {"keyboardLayout": "us"})
    path = root / "var/lib/AccountsService/users/ana"
    assert path.read_text() == "[User]\nPasswordHint=my cat Tom [User]\n"
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_password_hint_keeps_what_accountsservice_had(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path, password_hint="blue")
    root = make_root(tmp_path)
    users = root / "var/lib/AccountsService/users"
    users.mkdir(parents=True)
    (users / "ana").write_text("[User]\nIcon=/home/ana/.face\nPasswordHint=old\n")
    sc.write_password_hint(str(root), "ana", "blue")
    assert (users / "ana").read_text() == "[User]\nIcon=/home/ana/.face\nPasswordHint=blue\n"


def test_no_hint_writes_nothing(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path)
    root, _ = run_job(sc, monkeypatch, tmp_path, None, {"keyboardLayout": "us"})
    assert not (root / "var/lib/AccountsService/users/ana").exists()


def test_privacy_defaults_touch_nothing(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path, privacy="location=1 diagnostics=0 history=1")
    root, _ = run_job(sc, monkeypatch, tmp_path, None, {"keyboardLayout": "us"})
    config = root / "home/ana/.config"
    for name in ("raye-settingsrc", "PlasmaUserFeedback", "kactivitymanagerd-pluginsrc", "kdeglobals"):
        assert not (config / name).exists()


def test_privacy_choices_are_written_like_settings_does(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path, privacy="location=0 diagnostics=1 history=0")
    root = make_root(tmp_path)
    (root / "home/ana/.config").mkdir()
    (root / "home/ana/.config/kdeglobals").write_text("[General]\nColorScheme=RayeNight\n")
    root, _ = run_job(sc, monkeypatch, tmp_path, None, {"keyboardLayout": "us"}, root=root)
    config = root / "home/ana/.config"
    assert "[Privacy]\nLocationAccess=false\n" in (config / "raye-settingsrc").read_text()
    assert "[Global]\nFeedbackLevel=32\n" in (config / "PlasmaUserFeedback").read_text()
    assert ("[Plugin-org.kde.ActivityManager.Resources.Scoring]\nwhat-to-remember=2\n"
            in (config / "kactivitymanagerd-pluginsrc").read_text())
    assert (config / "kdeglobals").read_text() == (
        "[General]\nColorScheme=RayeNight\n\n[RecentDocuments]\nUseRecent=false\n")


def test_ini_value_replaced_in_its_group_only(sc, tmp_path):
    path = tmp_path / "rc"
    path.write_text("[A]\nKey=1\n\n[B]\nKey=1\nOther=x\n")
    sc.set_ini(str(path), "B", "Key", "2", None)
    assert path.read_text() == "[A]\nKey=1\n\n[B]\nKey=2\nOther=x\n"


def test_account_wish_is_left_for_after_setup(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path, account="signin")
    root, _ = run_job(sc, monkeypatch, tmp_path, None, {"keyboardLayout": "us"})
    assert (root / "home/ana/.config/raye-account-setuprc").read_text() == "[Setup]\nSignIn=pending\n"


def test_no_account_wish_writes_nothing(sc, monkeypatch, tmp_path):
    answers(sc, monkeypatch, tmp_path, account="later")
    root, _ = run_job(sc, monkeypatch, tmp_path, None, {"keyboardLayout": "us"})
    assert not (root / "home/ana/.config/raye-account-setuprc").exists()


# --- language packs for languages the image does not carry ---------------

def test_language_support_code(sc):
    assert sc.language_code("es_ES.UTF-8") == "es"
    assert sc.language_code("pt_BR.UTF-8") == "pt"
    assert sc.language_code("zh_CN.UTF-8") == "zh-hans"
    assert sc.language_code("zh_TW.UTF-8") == "zh-hant"
    assert sc.language_code("") is None
    assert sc.language_code("es; rm -rf /") is None


def test_image_languages_need_nothing(sc, tmp_path):
    root = make_root(tmp_path)
    for lang in ("en_US.UTF-8", "en_CA.UTF-8", "fr_CA.UTF-8", "fr_FR.UTF-8"):
        assert sc.queue_language_pack(str(root), lang) is False
    assert not (root / "etc/systemd/system/raye-language-pack.service").exists()


def test_other_language_is_queued_for_the_first_online_boot(sc, tmp_path):
    root = make_root(tmp_path)
    assert sc.queue_language_pack(str(root), "es_MX.UTF-8") is True
    assert (root / "var/lib/raye/language-pack-pending").read_text() == "es\n"
    unit = (root / "etc/systemd/system/raye-language-pack.service").read_text()
    assert "check-language-support -l" in unit
    assert "ConditionPathExists=/var/lib/raye/language-pack-pending" in unit
    assert "network-online.target" in unit
    wanted = root / "etc/systemd/system/multi-user.target.wants/raye-language-pack.service"
    assert os.readlink(wanted) == "/etc/systemd/system/raye-language-pack.service"


def test_job_queues_the_language_from_calamares(sc, monkeypatch, tmp_path):
    root, _ = run_job(sc, monkeypatch, tmp_path, None,
                      {"keyboardLayout": "es", "localeConf": {"LANG": "es_ES.UTF-8"}})
    assert (root / "var/lib/raye/language-pack-pending").read_text() == "es\n"


def test_unit_hands_dollars_to_the_shell_not_to_systemd(sc):
    exec_lines = sc.LANGUAGE_UNIT.split("ExecStart=", 1)[1].split("\nRestart", 1)[0]
    assert "$(" not in exec_lines.replace("$$(", "") and '"$code"' not in exec_lines
