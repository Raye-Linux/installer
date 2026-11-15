# SPDX-License-Identifier: GPL-3.0-or-later
"""The USB stick's session: Raye Setup and nothing else."""
import os
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).parent.parent
HOOK = REPO / "usr/share/initramfs-tools/scripts/casper-bottom/16raye_setup"
SDDM_AUTOLOGIN = "[Autologin]\nUser=raye\nSession=plasma.desktop\n"


def run_hook(tmp_path, sddm=SDDM_AUTOLOGIN, session_file=True):
    """The casper hook against a fake /root (the live system as the initrd
    sees it), with casper's logging functions stubbed."""
    root = tmp_path / "root"
    (root / "etc").mkdir(parents=True)
    if sddm is not None:
        (root / "etc/sddm.conf").write_text(sddm)
    if session_file:
        (root / "usr/share/wayland-sessions").mkdir(parents=True)
        (root / "usr/share/wayland-sessions/raye-setup.desktop").write_text("[Desktop Entry]\n")
    script = HOOK.read_text().replace("/root/", f"{root}/")
    script = script.replace(". /scripts/casper-functions",
                            "log_begin_msg() { :; }; log_end_msg() { :; }")
    subprocess.run(["sh", "-c", script, "16raye_setup"], check=True)
    return root


def test_hook_waits_for_casper_autologin():
    out = subprocess.run(["sh", str(HOOK), "prereqs"], capture_output=True, text=True, check=True)
    assert out.stdout.split() == ["15autologin"]


def test_hook_points_autologin_at_setup(tmp_path):
    root = run_hook(tmp_path)
    assert (root / "etc/sddm.conf").read_text() == "[Autologin]\nUser=raye\nSession=raye-setup.desktop\n"


def test_hook_leaves_sddm_alone_without_the_setup_session(tmp_path):
    root = run_hook(tmp_path, session_file=False)
    assert (root / "etc/sddm.conf").read_text() == SDDM_AUTOLOGIN


def test_hook_does_nothing_without_sddm_config(tmp_path):
    root = run_hook(tmp_path, sddm=None)
    assert not (root / "etc/sddm.conf").exists()


def test_session_file_starts_the_setup_session():
    desktop = (REPO / "usr/share/wayland-sessions/raye-setup.desktop").read_text()
    exec_line = re.search(r"^Exec=(\S+)", desktop, re.M).group(1)
    assert exec_line == "/usr/libexec/raye-setup-session"
    assert os.access(REPO / exec_line.lstrip("/"), os.X_OK)


def test_session_runs_kwin_with_setup_and_no_lock_or_shortcuts():
    session = (REPO / "usr/libexec/raye-setup-session").read_text()
    assert "--exit-with-session /usr/libexec/raye-setup-run" in session
    for flag in ("--no-lockscreen", "--no-global-shortcuts"):
        assert flag in session
    assert "idle:sleep:handle-lid-switch" in session
    assert "startplasma" not in session.split("kwin_wayland", 1)[0]


def test_kwin_has_no_corners_or_overview_in_setup():
    kwinrc = (REPO / "usr/share/raye/setup/kwinrc").read_text()
    for corner in ("TopLeft", "TopRight", "BottomLeft", "BottomRight"):
        assert f"{corner}=None" in kwinrc
    assert "overviewEnabled=false" in kwinrc


def test_requests_the_session_obeys_are_a_closed_list():
    run = (REPO / "usr/libexec/raye-setup-run").read_text()
    serve = run.split("serve() {", 1)[1].split("\n}\n", 1)[0]
    words = re.findall(r"^\s{12}(\w+)\)", serve, re.M)
    assert words == ["keyboard", "osk", "reader", "disks", "power"]
    assert "restart) sudo -n systemctl --no-wall reboot" in serve
    assert "poweroff) sudo -n systemctl --no-wall poweroff" in serve


def test_scripts_parse():
    for name in ("raye-setup-session", "raye-setup-run"):
        path = REPO / "usr/libexec" / name
        shell = "bash" if path.read_text().startswith("#!/bin/bash") else "sh"
        subprocess.run([shell, "-n", str(path)], check=True)


def test_restart_and_power_off_say_nothing_on_the_console():
    # systemd's "The system will reboot now!" lands on the screen for a second
    run = (REPO / "usr/libexec/raye-setup-run").read_text()
    assert "systemctl --no-wall reboot" in run
    assert "systemctl --no-wall poweroff" in run
    conf = (REPO / "etc/calamares/modules/finishedq.conf").read_text()
    assert 'restartNowCommand: "systemctl -i --no-wall reboot"' in conf
