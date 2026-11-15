# SPDX-License-Identifier: GPL-3.0-or-later
"""The on-screen keyboard of Setup: the gate that decides whether the
accessibility menu offers one at all.

What KWin really does, read in kwin 6.3.6 (apt-get source kwin, 2026-11-06):

  main_wayland.cpp:174-176  [Wayland] InputMethod of kwinrc is a PATH to a
                            .desktop file; KWin opens it with KDesktopFile
                            and runs its Exec. No file, or no Exec, leaves
                            the command empty and isAvailable() false --
                            nothing ever starts.
  inputmethod.cpp:91        [Wayland] VirtualKeyboardEnabled, default TRUE.
                            setActive(true) returns at once while it is
                            false, so the kwinrc value has to be written
                            out, and the session turns `enabled` on over
                            D-Bus before `active`.
  inputmethod.cpp:188       shouldShowOnActive() is touch or tablet only:
                            on a machine with a mouse the panel never shows
                            by itself, which is why Setup drives it.

⚠️ And the plan's claim that KWin's keyboard cannot serve Xwayland -- which
Calamares is, raye-setup-run sets QT_QPA_PLATFORM=xcb -- does not hold for
6.3.6. inputmethod.cpp carries an explicit fallback for "the application
has no way of communicating with the input method": commitString (l.569)
and keysymReceived (l.539) both end at seat()->notifyKeyboardKey(), real
key events through the Wayland seat, which Xwayland receives and hands to
its X11 clients. Window::setVirtualKeyboardGeometry (window.cpp:3061, the
base class, so X11 windows too) moves the window up so the panel does not
cover the field.

The limit is textToKey (inputmethod.cpp:54): the committed text goes
through QKeySequence::fromString and then needs a keycode IN THE CURRENT
XKB LAYOUT; with none it returns {} and the character is dropped without a
word. A keyboard that silently loses characters in a password field is
worse than no keyboard, which is why this file only guards the gate --
nothing here claims the feature works.

Nothing ships one today: iso/packages/raye-base names keyboard-configuration
and console-setup and no on-screen keyboard, plasma-keyboard is not in
Debian, and it is owned in the theme
repository. So the flag must read 0 and the menu must hide the row.
"""
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).parent.parent
RUN = REPO / "usr/libexec/raye-setup-run"
RUN_TEXT = RUN.read_text()
# without the comments: they are free to name what the script must not do
RUN_CODE = re.sub(r"^\s*#.*$", "", RUN_TEXT, flags=re.M)
KWINRC = (REPO / "usr/share/raye/setup/kwinrc").read_text()
NAVIGATION = (REPO / "etc/calamares/branding/raye/calamares-navigation.qml").read_text()


def shell_function(name):
    """One function of raye-setup-run, by name, up to the } in column 1.

    ⚠️ Not with sed: a range from the opening line to the next } in column
    1 runs past a one-line function and swallows the next one. Pulled line
    by line instead, and the caller gets a syntax error if the shape ever
    changes.
    """
    lines = RUN_TEXT.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(f"{name}() {{"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "}")
    return "\n".join(lines[start:end + 1]) + "\n"


def ask(tmp_path, input_method=None, desktop=None):
    """Run the real gate of raye-setup-run against a fake HOME: `1` when it
    would offer the keyboard, `0` when it would not."""
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True, exist_ok=True)
    body = "[Wayland]\n"
    if input_method is not None:
        body += f"InputMethod[$e]={input_method}\n"
    body += "VirtualKeyboardEnabled=false\n"
    (home / ".config/kwinrc").write_text(body)
    if desktop is not None:
        path = tmp_path / "keyboard.desktop"
        path.write_text(desktop)
    script = (shell_function("osk_desktop") + shell_function("osk_available")
              + 'osk_available && echo 1 || echo 0\n')
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "HOME": str(home)})
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


WORKING = "[Desktop Entry]\nName=Keyboard\nExec=plasma-keyboard\n"


def test_no_kwinrc_at_all_offers_nothing(tmp_path):
    (tmp_path / "home/.config").mkdir(parents=True)
    script = (shell_function("osk_desktop") + shell_function("osk_available")
              + 'osk_available && echo 1 || echo 0\n')
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                               "HOME": str(tmp_path / "home")})
    assert done.stdout.strip() == "0", done.stderr


def test_a_kwinrc_naming_no_input_method_offers_nothing(tmp_path):
    assert ask(tmp_path) == "0"


def test_a_desktop_file_that_is_not_there_offers_nothing(tmp_path):
    """🚨 This is the case the old gate got wrong. It tested
    `-x /usr/bin/plasma-keyboard`, a path KWin never reads: a keyboard
    whose binary is installed and whose desktop file is not would have put
    a row in the accessibility menu that does nothing when pressed.
    """
    assert ask(tmp_path, input_method=str(tmp_path / "keyboard.desktop")) == "0"


def test_a_desktop_file_with_no_exec_offers_nothing(tmp_path):
    """KWin's command would be the empty string, and nothing starts."""
    assert ask(tmp_path, input_method=str(tmp_path / "keyboard.desktop"),
               desktop="[Desktop Entry]\nName=Keyboard\n") == "0"


def test_the_keyboard_kwin_can_start_is_offered(tmp_path):
    assert ask(tmp_path, input_method=str(tmp_path / "keyboard.desktop"),
               desktop=WORKING) == "1"


def test_the_gate_asks_about_no_other_path():
    assert "/usr/bin/plasma-keyboard" not in RUN_CODE, (
        "a second path for the same thing: KWin reads the desktop file of "
        "kwinrc and nothing else"
    )


def test_the_panel_never_comes_up_uninvited():
    """VirtualKeyboardEnabled defaults to TRUE in KWin, so leaving the key
    out is not the same as writing false."""
    assert re.search(r"^VirtualKeyboardEnabled=false$", KWINRC, re.M)
    assert re.search(r"^InputMethod\[\$e\]=/\S+\.desktop$", KWINRC, re.M)


def test_turning_it_on_sets_enabled_before_active():
    """setActive(true) returns at once while m_enabled is false."""
    body = shell_function("osk")
    assert body.index("VirtualKeyboard enabled") < body.index("VirtualKeyboard active"), body


def test_the_menu_hides_the_row_until_the_flag_says_otherwise():
    """Async: Requests.flags answers later, so the default decides what is
    on screen first. False is the only safe default."""
    assert re.search(r"^\s*property bool hasKeyboard: false$", NAVIGATION, re.M)
    row = re.search(r"ListRow \{(?:(?!ListRow).)*?onScreenKeyboard.*?\n(\s*)\}",
                    NAVIGATION, re.S)
    assert row, "the on-screen keyboard row is gone"
    assert "visible: bar.hasKeyboard" in row.group(0), row.group(0)
