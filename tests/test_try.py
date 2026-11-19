# SPDX-License-Identifier: GPL-3.0-or-later
"""Trying Raye from the USB stick: the desktop instead of Setup, with
Install on the desktop and in Start, and nothing kept or written."""
import configparser
import os
import pathlib
import re
import subprocess

import pytest

REPO = pathlib.Path(__file__).parent.parent
HOOK = REPO / "usr/share/initramfs-tools/scripts/casper-bottom/16raye_setup"
SESSION = REPO / "usr/share/wayland-sessions/raye-try.desktop"
HELPER = REPO / "usr/libexec/raye-try-session"
RULE = REPO / "usr/lib/udev/rules.d/90-raye-try.rules"
UPDATE_DROPIN = REPO / "usr/lib/systemd/system/raye-update.service.d/raye-live.conf"
SDDM_AUTOLOGIN = "[Autologin]\nUser=raye\nSession=plasma.desktop\n"
START_PINS = "org.kde.dolphin.desktop,firefox.desktop,org.raye.store.desktop"


def run_hook(tmp_path, cmdline, try_session=True):
    root = tmp_path / "root"
    (root / "etc").mkdir(parents=True)
    (root / "etc/sddm.conf").write_text(SDDM_AUTOLOGIN)
    sessions = root / "usr/share/wayland-sessions"
    sessions.mkdir(parents=True)
    (sessions / "raye-setup.desktop").write_text("[Desktop Entry]\n")
    if try_session:
        (sessions / "raye-try.desktop").write_text("[Desktop Entry]\n")
    (tmp_path / "cmdline").write_text(cmdline + "\n")
    script = HOOK.read_text().replace("/root/", f"{root}/")
    script = script.replace("/proc/cmdline", str(tmp_path / "cmdline"))
    script = script.replace(". /scripts/casper-functions",
                            "log_begin_msg() { :; }; log_end_msg() { :; }")
    subprocess.run(["sh", "-c", script, "16raye_setup"], check=True)
    return (root / "etc/sddm.conf").read_text()


def test_try_entry_starts_the_try_session(tmp_path):
    sddm = run_hook(tmp_path, "boot=casper noprompt nopersistent raye.try quiet splash ---")
    assert sddm == "[Autologin]\nUser=raye\nSession=raye-try.desktop\n"


def test_install_entry_still_starts_setup(tmp_path):
    sddm = run_hook(tmp_path, "boot=casper noprompt quiet splash ---")
    assert "Session=raye-setup.desktop" in sddm


@pytest.mark.parametrize("word", ["raye.trying", "xraye.try", "raye.try=0"])
def test_only_the_bare_word_means_try(tmp_path, word):
    sddm = run_hook(tmp_path, f"boot=casper {word} quiet")
    assert "Session=raye-setup.desktop" in sddm


def test_try_without_its_session_file_keeps_the_desktop(tmp_path):
    # never Setup when the person asked to try: plain Plasma is the fallback
    sddm = run_hook(tmp_path, "boot=casper raye.try", try_session=False)
    assert sddm == SDDM_AUTOLOGIN


def desktop(path):
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read_string(path.read_text(encoding="utf-8"))
    return parser["Desktop Entry"]


def test_try_session_file():
    entry = desktop(SESSION)
    assert entry["Exec"] == "/usr/libexec/raye-try-session"
    assert entry["DesktopNames"] == "KDE"
    assert entry["Name[fr]"] and entry["Comment[fr]"]
    assert os.access(HELPER, os.X_OK)


# ------------------------------------------------------- the session helper

def stub(path, body):
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(0o755)


@pytest.fixture
def world(tmp_path):
    """A live account's home, fake KDE tools that log what they are asked,
    and a plasma.desktop whose Exec only says it ran."""
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    log = tmp_path / "log"
    stub(bin_ / "kwriteconfig6", f'echo "kwrite $*" >> {log}')
    stub(bin_ / "kreadconfig6", f'cat {tmp_path}/pins 2>/dev/null')
    stub(bin_ / "xdg-user-dirs-update", f'echo "dirs-update" >> {log}')
    stub(bin_ / "xdg-user-dir", f'echo "{home}/Bureau"')
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    stub(bin_ / "fake-plasma", f'echo "plasma $*" >> {log}')
    (sessions / "plasma.desktop").write_text(
        f"[Desktop Entry]\nExec={bin_}/fake-plasma --wayland\n")
    apps = tmp_path / "apps"
    apps.mkdir()
    (apps / "raye-install.desktop").write_text(
        (REPO / "usr/share/applications/raye-install.desktop").read_text())
    (tmp_path / "pins").write_text(START_PINS + "\n")
    env = dict(os.environ, HOME=str(home), PATH=f"{bin_}:{os.environ['PATH']}",
               XDG_CONFIG_HOME=str(home / ".config"),
               RAYE_SESSIONS=str(sessions), RAYE_APPS=str(apps), LANG="en_US.UTF-8")
    env.pop("LANGUAGE", None)
    return {"tmp": tmp_path, "home": home, "log": log, "env": env, "bin": bin_}


def run_helper(world, *args, **extra):
    env = dict(world["env"], **extra)
    return subprocess.run(["sh", str(HELPER), *args], env=env, check=True,
                          capture_output=True, text=True, timeout=30)


def log_of(world):
    return world["log"].read_text().splitlines() if world["log"].exists() else []


def test_session_puts_install_on_the_desktop_it_really_uses(world):
    run_helper(world)
    icon = world["home"] / "Bureau/raye-install.desktop"
    assert icon.is_file()
    # a launcher Plasma runs without asking whether to trust it
    assert os.access(icon, os.X_OK)
    assert desktop(icon)["Exec"] == "/usr/bin/raye-install"
    assert "dirs-update" in log_of(world)


def test_session_pins_install_first_in_start(world):
    run_helper(world)
    pins = [l for l in log_of(world) if "rayeshellrc" in l]
    assert pins == [f"kwrite --file rayeshellrc --group Start --key Pinned "
                    f"raye-install.desktop,{START_PINS}"]


def test_session_does_not_pin_twice(world):
    (world["tmp"] / "pins").write_text("raye-install.desktop," + START_PINS + "\n")
    run_helper(world)
    assert not [l for l in log_of(world) if "rayeshellrc" in l]


def test_session_never_locks_the_screen(world):
    # the live account has no password anyone knows
    run_helper(world)
    log = log_of(world)
    assert "kwrite --file kscreenlockerrc --group Daemon --key Autolock false" in log
    assert "kwrite --file kscreenlockerrc --group Daemon --key LockOnResume false" in log
    for profile in ("AC", "Battery", "LowBattery"):
        assert (f"kwrite --file powerdevilrc --group {profile} --group Display "
                "--key LockBeforeTurnOffDisplay false") in log


def test_session_shows_the_notice_once_plasma_is_up(world):
    run_helper(world)
    notice = world["home"] / ".config/autostart/raye-try-notice.desktop"
    entry = desktop(notice)
    assert entry["Exec"] == "/usr/libexec/raye-try-session notice"
    assert entry["OnlyShowIn"] == "KDE;"


def test_session_ends_in_plasma(world):
    run_helper(world)
    assert log_of(world)[-1] == "plasma --wayland"


def test_session_starts_plasma_even_when_the_rest_fails(world):
    # no tools at all: the person still gets a desktop
    for name in ("kwriteconfig6", "kreadconfig6", "xdg-user-dirs-update", "xdg-user-dir"):
        stub(world["bin"] / name, "exit 1")
    run_helper(world)
    assert log_of(world)[-1] == "plasma --wayland"


@pytest.fixture
def notify(world):
    """notify-send that records its arguments and answers $ANSWER."""
    calls = world["tmp"] / "notify"
    stub(world["bin"] / "notify-send",
         f'printf "%s\\n" "$@" > {calls}; [ -n "$ANSWER" ] && echo "$ANSWER"; exit 0')
    stub(world["bin"] / "fake-install", f'echo "install" >> {world["log"]}')
    world["env"]["RAYE_INSTALL"] = str(world["bin"] / "fake-install")
    world["env"]["ANSWER"] = ""
    return calls


def test_notice_says_nothing_is_kept_in_english(world, notify):
    run_helper(world, "notice")
    args = notify.read_text().splitlines()
    text = " ".join(args)
    assert "You're trying Raye Linux" in args
    assert "restart" in text and "read-only" in text
    assert "--action=install=Install Raye Linux" in args
    assert "--wait" in args and "--urgency=critical" in args
    assert "!" not in text and "Wine" not in text


def test_notice_in_french(world, notify):
    run_helper(world, "notice", LANG="fr_CA.UTF-8")
    args = notify.read_text().splitlines()
    text = " ".join(args)
    assert "Vous essayez Raye Linux" in args
    assert "--action=install=Installer Raye Linux" in args
    # French punctuation keeps its no-break space
    assert " :" not in text and " ?" not in text
    assert " :" in text


def test_notice_button_opens_setup(world, notify):
    run_helper(world, "notice", ANSWER="install")
    assert "install" in log_of(world)


def test_notice_closed_opens_nothing(world, notify):
    run_helper(world, "notice")
    assert "install" not in log_of(world)


def test_helper_parses():
    subprocess.run(["sh", "-n", str(HELPER)], check=True)


# ------------------------------------------- nothing written to the PC's disks

def rule_lines():
    return [l for l in RULE.read_text().splitlines() if l.strip() and not l.startswith("#")]


def test_rule_only_acts_when_trying():
    lines = rule_lines()
    assert lines[0] == 'IMPORT{cmdline}="raye.try"'
    assert lines[1] == 'ENV{raye.try}!="1", GOTO="raye_try_end"'
    assert lines[-1] == 'LABEL="raye_try_end"'


def test_rule_leaves_usb_drives_writable():
    text = "\n".join(rule_lines())
    assert 'ENV{ID_BUS}=="usb", GOTO="raye_try_end"' in text
    assert 'SUBSYSTEM!="block", GOTO="raye_try_end"' in text


def test_rule_mounts_the_pcs_disks_read_only():
    sets = dict(re.findall(r'ENV\{(UDISKS_MOUNT_OPTIONS_\w+)\}="([^"]*)"', RULE.read_text()))
    assert sets["UDISKS_MOUNT_OPTIONS_DEFAULTS"] == "ro"
    allow = sets["UDISKS_MOUNT_OPTIONS_ALLOW"].split(",")
    assert "ro" in allow and "rw" not in allow
    # a read-only ext3/ext4 mount still replays its journal unless told not to
    for fs in ("EXT3", "EXT4"):
        assert "noload" in sets[f"UDISKS_MOUNT_OPTIONS_{fs}_DEFAULTS"].split(",")


def test_live_stick_does_not_fetch_updates_into_memory():
    text = UPDATE_DROPIN.read_text()
    assert "[Unit]" in text
    assert "ConditionKernelCommandLine=!boot=casper" in text


# ----------------------------------------------- Setup opened from the desktop

def test_install_runs_setup_the_way_the_stick_does():
    install = (REPO / "usr/bin/raye-install").read_text()
    assert "exec /usr/libexec/raye-setup-run --desktop" in install


def setup_run():
    return (REPO / "usr/libexec/raye-setup-run").read_text()


def test_setup_from_the_desktop_runs_once_and_leaves_no_rescue():
    run = setup_run()
    assert 'desktop=0' in run and '--desktop) desktop=1' in run
    # the restart loop and the rescue file belong to the setup session
    loop = run.split("while :; do", 1)[1]
    assert '[ "$desktop" = 1 ] && break' in loop
    assert re.search(r'\[ "\$desktop" = 1 \] \|\| touch "\$dir/rescue"', run)


def test_setup_from_the_desktop_tells_the_pages():
    assert 'echo "desktop=$desktop"' in setup_run()


def test_only_one_setup_at_a_time():
    run = setup_run()
    assert re.search(r'flock -n 9 \|\| exit 0', run)


def test_close_is_only_obeyed_from_the_desktop():
    serve = setup_run().split("serve() {", 1)[1].split("\n}\n", 1)[0]
    close = serve.split("close)", 1)[1].split(";;", 1)[0]
    assert '[ "$desktop" = 1 ]' in close
    assert "pkill -TERM -x calamares" in close


def test_quit_box_goes_back_to_the_desktop():
    bar = (REPO / "etc/calamares/branding/raye/calamares-sidebar.qml").read_text()
    assert 'Requests.flags' in bar and 'found.desktop === "1"' in bar
    assert 'Requests.send("close")' in bar
    strings = (REPO / "etc/calamares/branding/raye/strings.js").read_text()
    for key in ("quitTextDesktop", "quitClose"):
        assert strings.count(f"{key}:") == 2, key
