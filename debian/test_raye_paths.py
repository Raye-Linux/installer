# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for debian/raye_paths.py and for the paths list it reads."""
import importlib.util
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
spec = importlib.util.spec_from_file_location("raye_paths", HERE / "raye_paths.py")
rp = importlib.util.module_from_spec(spec)
sys.modules["raye_paths"] = rp
spec.loader.exec_module(rp)

CONTROL = """\
Source: demo
Build-Depends: debhelper-compat (= 13)

Package: one
Architecture: any
Depends: calamares (>= 3.3.14), raye-style | raye-theme,
         kdialog, ${misc:Depends}
Description: first

Package: two
Architecture: all
Description: second
"""

VARS = {"DEB_HOST_MULTIARCH": "x86_64-linux-gnu"}


def write(path, text="x", mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)
    return path


def repo(tmp_path, paths_text):
    write(tmp_path / "debian/control", CONTROL)
    write(tmp_path / "debian/raye-paths", paths_text)
    return tmp_path


def make_plan(root, strict=False):
    return rp.plan(root, strict=strict, variables=VARS)


# --------------------------------------------------------------- parsing

def test_parse_skips_comments_and_blank_lines():
    entries = rp.parse("# a comment\n\none  usr/bin/a   # trailing\n", VARS)
    assert [(e.package, e.source, e.dest, e.optional) for e in entries] == [
        ("one", "usr/bin/a", "usr/bin/a", False)]


def test_parse_optional_marker_and_build_tree_source():
    (entry,) = rp.parse("one ?debian/tmp/usr/bin/raye-setup\n", VARS)
    assert entry.optional
    assert entry.source == "debian/tmp/usr/bin/raye-setup"
    assert entry.dest == "usr/bin/raye-setup"
    assert entry.from_build


def test_parse_destination_and_multiarch():
    (entry,) = rp.parse("two qml/org/raye/setup usr/lib/${DEB_HOST_MULTIARCH}/qt6/qml/org/raye/setup\n", VARS)
    assert entry.dest == "usr/lib/x86_64-linux-gnu/qt6/qml/org/raye/setup"


@pytest.mark.parametrize("line", [
    "one",
    "one a b c",
    "one /etc/passwd",
    "one etc/../../x",
    "one etc/x /usr/x",
    "one etc/x usr/${NOPE}/x",
    "one etc/x .",
    "one etc/./x",
    "one ?",
])
def test_parse_rejects_bad_lines_with_their_number(line):
    with pytest.raises(rp.PathsError, match="line 2"):
        rp.parse("# header\n" + line + "\n", VARS)


def test_read_control_lists_packages_and_depends():
    packages = rp.read_control(CONTROL)
    assert list(packages) == ["one", "two"]
    assert packages["one"] == {"calamares", "raye-style", "raye-theme", "kdialog", "${misc:Depends}"}
    assert packages["two"] == set()


# --------------------------------------------------------------- planning

def test_missing_required_source_is_an_error(tmp_path):
    root = repo(tmp_path, "one usr/bin/gone\n")
    result = make_plan(root)
    assert any("usr/bin/gone" in e and "missing" in e for e in result.errors)


def test_missing_optional_source_is_only_a_note(tmp_path):
    root = repo(tmp_path, "one ?usr/libexec/later\n")
    result = make_plan(root)
    assert result.errors == []
    assert any("usr/libexec/later" in n for n in result.notes)
    assert result.copies == []


def test_strict_turns_a_missing_optional_source_into_an_error(tmp_path):
    root = repo(tmp_path, "one ?usr/libexec/later\n")
    assert any("usr/libexec/later" in e for e in make_plan(root, strict=True).errors)


def test_unknown_package_is_an_error(tmp_path):
    root = repo(tmp_path, "three etc/x\n")
    write(root / "etc/x")
    assert any("three" in e for e in make_plan(root).errors)


def test_folder_source_takes_every_file_but_bytecode(tmp_path):
    root = repo(tmp_path, "one usr/lib/calamares/modules/job\n")
    write(root / "usr/lib/calamares/modules/job/main.py")
    write(root / "usr/lib/calamares/modules/job/module.desc")
    write(root / "usr/lib/calamares/modules/job/__pycache__/main.cpython-313.pyc")
    write(root / "usr/lib/calamares/modules/job/stray.pyc")
    result = make_plan(root)
    assert result.errors == []
    assert sorted(dest for _, dest, _ in result.copies) == [
        "usr/lib/calamares/modules/job/main.py",
        "usr/lib/calamares/modules/job/module.desc",
    ]


def test_file_left_out_of_the_list_is_an_error(tmp_path):
    root = repo(tmp_path, "one etc/listed\n")
    write(root / "etc/listed")
    write(root / "usr/libexec/forgotten", mode=0o755)
    errors = make_plan(root).errors
    assert any("usr/libexec/forgotten" in e and "raye-paths" in e for e in errors)


def test_sources_and_tests_outside_the_shipped_folders_are_ignored(tmp_path):
    root = repo(tmp_path, "one etc/listed\n")
    write(root / "etc/listed")
    write(root / "app/setup/main.cpp")
    write(root / "tests/test_x.py")
    write(root / "README.md")
    assert make_plan(root).errors == []


def test_build_tree_file_left_out_is_an_error(tmp_path):
    root = repo(tmp_path, "one ?debian/tmp/usr/bin/raye-setup\n")
    write(root / "debian/tmp/usr/bin/raye-setup", mode=0o755)
    write(root / "debian/tmp/usr/share/raye/extra.qm")
    errors = make_plan(root).errors
    assert any("debian/tmp/usr/share/raye/extra.qm" in e for e in errors)


def test_build_tree_file_is_shipped_under_its_installed_path(tmp_path):
    root = repo(tmp_path, "one ?debian/tmp/usr/bin/raye-setup\n")
    write(root / "debian/tmp/usr/bin/raye-setup", mode=0o755)
    result = make_plan(root)
    assert result.errors == []
    assert [(dest, pkg) for _, dest, pkg in result.copies] == [("usr/bin/raye-setup", "one")]


def test_two_entries_on_the_same_destination_are_an_error(tmp_path):
    root = repo(tmp_path, "one etc/a usr/share/x\ntwo etc/b usr/share/x\n")
    write(root / "etc/a")
    write(root / "etc/b")
    assert any("usr/share/x" in e and "twice" in e for e in make_plan(root).errors)


def test_program_without_exec_bit_is_an_error(tmp_path):
    root = repo(tmp_path, "one usr/libexec/raye-thing\none usr/share/initramfs-tools/scripts/casper-bottom/16x\n")
    write(root / "usr/libexec/raye-thing", mode=0o644)
    write(root / "usr/share/initramfs-tools/scripts/casper-bottom/16x", mode=0o644)
    errors = make_plan(root).errors
    assert any("usr/libexec/raye-thing" in e and "executable" in e for e in errors)
    assert any("casper-bottom/16x" in e and "executable" in e for e in errors)


def test_initrd_script_under_etc_needs_its_exec_bit(tmp_path):
    root = repo(tmp_path, "one etc/initramfs-tools/scripts/casper-bottom/13x\n")
    write(root / "etc/initramfs-tools/scripts/casper-bottom/13x", mode=0o644)
    assert any("casper-bottom/13x" in e and "executable" in e for e in make_plan(root).errors)


# --------------------------------------------------------------- installing

def test_install_copies_with_modes_and_symlinks(tmp_path):
    root = repo(tmp_path, "one usr/libexec/raye-thing\ntwo qml/org/raye/setup usr/lib/${DEB_HOST_MULTIARCH}/qt6/qml/org/raye/setup\n")
    write(root / "usr/libexec/raye-thing", "#!/bin/sh\n", mode=0o755)
    write(root / "qml/org/raye/setup/qmldir", "module org.raye.setup\n")
    (root / "qml/org/raye/setup/Alias.qml").symlink_to("qmldir")
    result = make_plan(root)
    assert result.errors == []
    rp.install(result, root)
    prog = root / "debian/one/usr/libexec/raye-thing"
    assert prog.read_text() == "#!/bin/sh\n"
    assert prog.stat().st_mode & stat.S_IXUSR
    qml = root / "debian/two/usr/lib/x86_64-linux-gnu/qt6/qml/org/raye/setup"
    assert (qml / "qmldir").read_text() == "module org.raye.setup\n"
    assert os.readlink(qml / "Alias.qml") == "qmldir"


def test_install_refuses_to_write_through_a_symlinked_folder(tmp_path):
    # A folder symlink listed first, then used as the prefix of another
    # destination, would take the copy right out of the package.
    outside = tmp_path / "outside"
    outside.mkdir()
    root = repo(tmp_path / "repo",
                "one usr/share/raye/setup\n"
                "one usr/share/raye/other  usr/share/raye/setup/sub\n")
    (root / "usr/share/raye").mkdir(parents=True)
    (root / "usr/share/raye/setup").symlink_to(outside, target_is_directory=True)
    write(root / "usr/share/raye/other/f.txt")
    result = make_plan(root)
    assert result.errors == []
    with pytest.raises(rp.PathsError, match="outside"):
        rp.install(result, root)
    assert not (outside / "sub").exists()


def test_main_install_fails_and_writes_nothing_on_errors(tmp_path, capsys):
    root = repo(tmp_path, "one etc/listed\n")
    write(root / "etc/listed")
    write(root / "etc/forgotten")
    assert rp.main(["install", "--root", str(root)], env=VARS) == 1
    assert not (root / "debian/one").exists()
    assert "etc/forgotten" in capsys.readouterr().err


def test_main_strict_comes_from_the_environment(tmp_path):
    root = repo(tmp_path, "one ?etc/later\n")
    assert rp.main(["check", "--root", str(root)], env=VARS) == 0
    assert rp.main(["check", "--root", str(root)], env={**VARS, "RAYE_PATHS_STRICT": "1"}) == 1


# --------------------------------------------------------------- .deb contents

def test_compare_deb_contents():
    expected = {"usr/bin/raye-install", "etc/calamares/settings.conf"}
    actual = {"usr/bin/raye-install", "usr/share/doc/one/copyright",
              "usr/share/doc/one/changelog.gz", "usr/share/lintian/overrides/one",
              "usr/lib/extra"}
    missing, extra = rp.compare_deb("one", expected, actual)
    assert missing == ["etc/calamares/settings.conf"]
    assert extra == ["usr/lib/extra"]


# --------------------------------------------------------------- the real lists

# Every path the installer design names, with the package that ships it.
SPEC_PATHS = {
    "etc/calamares": "calamares-settings-raye",
    "etc/xdg/plasma-nm": "calamares-settings-raye",
    "etc/xdg/kscreenlockerrc": "calamares-settings-raye",
    "etc/xdg/powerdevilrc": "calamares-settings-raye",
    "usr/bin/raye-install": "calamares-settings-raye",
    "usr/bin/raye-setup": "calamares-settings-raye",
    "usr/libexec/raye-preflight": "calamares-settings-raye",
    "usr/libexec/raye-install-logs": "calamares-settings-raye",
    "usr/libexec/raye-efi-entry": "calamares-settings-raye",
    "usr/libexec/fixconkeys-part1": "calamares-settings-raye",
    "usr/libexec/fixconkeys-part2": "calamares-settings-raye",
    "usr/libexec/raye-setup-session": "calamares-settings-raye",
    "usr/libexec/raye-setup-run": "calamares-settings-raye",
    "usr/libexec/raye-calamares": "calamares-settings-raye",
    "usr/libexec/raye-restart": "calamares-settings-raye",
    "usr/lib/calamares/modules/rayeencryption": "calamares-settings-raye",
    "usr/lib/calamares/modules/rayesetupchoices": "calamares-settings-raye",
    "usr/lib/calamares/modules/rayelanguage": "calamares-settings-raye",
    "usr/lib/systemd/system/raye-live-remove-usb.service": "calamares-settings-raye",
    "usr/lib/tmpfiles.d/raye-setup.conf": "calamares-settings-raye",
    "usr/share/applications/raye-install.desktop": "calamares-settings-raye",
    "usr/share/applications/calamares.desktop": "calamares-settings-raye",
    "usr/share/wayland-sessions/raye-setup.desktop": "calamares-settings-raye",
    "usr/share/initramfs-tools/scripts/casper-bottom/16raye_setup": "calamares-settings-raye",
    "etc/initramfs-tools/scripts/casper-bottom/13swap": "calamares-settings-raye",
    "usr/share/raye/setup": "calamares-settings-raye",
    "usr/lib/x86_64-linux-gnu/qt6/qml/org/raye/setup": "qml6-module-org-raye-setup",
    "usr/bin/raye-first-run": "raye-first-run",
    "etc/xdg/autostart/raye-first-run.desktop": "raye-first-run",
}


@pytest.fixture(scope="module")
def real():
    control = rp.read_control((REPO / "debian/control").read_text())
    entries = rp.parse((REPO / "debian/raye-paths").read_text(), VARS)
    return control, entries


def test_real_packages(real):
    control, entries = real
    assert list(control) == ["calamares-settings-raye", "qml6-module-org-raye-setup", "raye-first-run"]
    assert {e.package for e in entries} == set(control)


def test_every_spec_path_is_listed_in_its_package(real):
    _, entries = real
    listed = {e.dest: e.package for e in entries}
    for path, package in SPEC_PATHS.items():
        assert listed.get(path) == package, path


def test_real_tree_plans_without_errors():
    result = rp.plan(REPO, strict=False, variables=VARS)
    assert result.errors == []


def test_live_package_depends(real):
    control, _ = real
    deps = control["calamares-settings-raye"]
    for name in ("calamares", "qml6-module-org-raye-setup", "raye-style",
                 "qml6-module-qtquick-shapes", "qml6-module-qtquick-effects",
                 "kwin-wayland", "systemd"):
        assert name in deps, name


def test_first_run_depends(real):
    control, _ = real
    assert {"qml6-module-org-raye-setup", "qrencode", "accountsservice"} <= control["raye-first-run"]


# Each QML module the app imports, and the package that carries it. The
# binary is one file in /usr/bin with its own QML inside, so nothing else
# warns when an import has no dependency behind it: the app would start,
# fail to load its window and exit 1, at the first sign-in of a new
# machine and nowhere else.
QML_IMPORT_PACKAGES = {
    "QtQuick": "qml6-module-qtquick",
    "QtQuick.Window": "qml6-module-qtquick-window",
    "QtQuick.Dialogs": "qml6-module-qtquick-dialogs",
    "org.raye.setup": "qml6-module-org-raye-setup",
}


def test_the_first_run_resource_carries_every_file_of_its_qml_folder():
    """🚨 A QML file left out of the resource is green everywhere and dead
    in the binary.

    app/firstrun's window is built into the executable through
    qt_add_resources, while tests/ui/tst_firstrun.qml loads the page out
    of the SOURCE folder. So a new file that nobody added to FILES is
    found by every test and missing from the only place it is read at run
    time. Measured 2026-11-06: words.js was written, both suites stayed
    green at 272 and 48, and the built app answered
    "Script qrc:/raye/firstrun/words.js unavailable", failed to load its
    window and exited 1 -- which on a real machine happens once, at the
    first sign-in, and nowhere a person would look.
    """
    cmakelists = (REPO / "app/firstrun/CMakeLists.txt").read_text()
    on_disk = sorted(p.name for p in (REPO / "app/firstrun/qml").iterdir()
                     if p.suffix in (".qml", ".js"))
    assert on_disk, "app/firstrun/qml is empty"
    missing = [name for name in on_disk if f"qml/{name}" not in cmakelists]
    assert missing == [], (
        "app/firstrun/CMakeLists.txt does not put these in the resource, so the "
        f"built app cannot read them: {', '.join(missing)}")


def test_first_run_depends_on_every_qml_module_it_imports(real):
    control, _ = real
    deps = control["raye-first-run"]
    imports = set()
    for path in sorted((REPO / "app/firstrun/qml").glob("*.qml")):
        for line in path.read_text().splitlines():
            if not line.startswith("import "):
                continue
            what = line.split()[1]
            # import "words.js" as W is a file next to the page, not a
            # module, so no package carries it.
            if what.startswith('"'):
                continue
            imports.add(what)
    assert imports, "app/firstrun/qml holds no QML file to read imports from"
    for module in sorted(imports):
        package = QML_IMPORT_PACKAGES.get(module)
        assert package, (
            f"app/firstrun imports {module} and QML_IMPORT_PACKAGES in this file does "
            "not say which package carries it: add it there and to debian/control")
        assert package in deps, f"app/firstrun imports {module}: raye-first-run must depend on {package}"


def text_files_of(package, entries):
    """Every readable text file the package ships from the source tree."""
    for entry in entries:
        if entry.package != package or entry.from_build:
            continue
        source = REPO / entry.source
        files = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
        for path in files:
            try:
                path.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            yield path


def test_kdialog_is_a_dependency_exactly_while_a_live_file_calls_it(real):
    # The setup app replaces every kdialog box; once nothing on the live
    # image runs kdialog, the dependency goes, and not before. Shell
    # scripts and the Python job modules both count.
    control, entries = real
    users = [p.relative_to(REPO) for p in text_files_of("calamares-settings-raye", entries)
             if re.search(r"^[^#]*\bkdialog\b", p.read_text(), re.M)]
    listed = "kdialog" in control["calamares-settings-raye"]
    if users and not listed:
        raise AssertionError(f"these still call kdialog, put it back in Depends: {users}")
    if listed and not users:
        raise AssertionError("nothing calls kdialog any more: drop it from Depends in debian/control")


# Depending on one of these without a version is always wrong: they are
# there before anything is unpacked.
ESSENTIAL = {"base-files", "base-passwd", "bash", "bsdutils", "coreutils", "dash",
             "debianutils", "diffutils", "dpkg", "findutils", "grep", "gzip",
             "hostname", "init-system-helpers", "libc-bin", "login", "mount",
             "ncurses-base", "ncurses-bin", "perl-base", "sed", "sysvinit-utils",
             "tar", "util-linux"}


def test_no_bare_dependency_on_an_essential_package(real):
    control, _ = real
    for package, deps in control.items():
        assert not (deps & ESSENTIAL), (package, sorted(deps & ESSENTIAL))


def test_the_top_level_build_covers_both_apps():
    text = (REPO / "CMakeLists.txt").read_text()
    parts = re.search(r"set\(RAYE_PARTS([^)]*)\)", text).group(1).split()
    assert "app/setup" in parts and "app/firstrun" in parts


def test_rules_installs_through_the_list_and_keeps_dh_missing_quiet():
    # raye_paths.py copies out of debian/tmp behind dh_install's back, so
    # dh_missing would stop the build on every file the apps install.
    text = (REPO / "debian/rules").read_text()
    assert re.search(r"^override_dh_install:\n\tpython3 debian/raye_paths\.py install$",
                     text, re.M)
    assert re.search(r"^override_dh_missing:\n(?!\t)", text, re.M)


def test_calamares_desktop_diversion_matches_maintainer_scripts():
    pre = (REPO / "debian/calamares-settings-raye.preinst").read_text()
    post = (REPO / "debian/calamares-settings-raye.postrm").read_text()
    for text in (pre, post):
        assert "/usr/share/applications/calamares.desktop" in text
        assert "--package calamares-settings-raye" in text
        assert "#DEBHELPER#" in text
    assert "--add" in pre and "--remove" in post


DESKTOP = "usr/share/applications/calamares.desktop"


def run_maintainer_script(name, root, *args):
    """The script as dpkg runs it, on a root of our own."""
    assert str(root), "DPKG_ROOT has to be a root of our own, never the machine"
    text = (REPO / f"debian/calamares-settings-raye.{name}").read_text()
    script = pathlib.Path(root) / f"{name}.sh"
    script.write_text(text.replace("#DEBHELPER#", ""))
    return subprocess.run(["sh", "-e", str(script), *args], check=True,
                          env={"PATH": os.environ.get("PATH", "/usr/sbin:/usr/bin"),
                               "DPKG_ROOT": str(root)},
                          capture_output=True, text=True)


@pytest.mark.skipif(shutil.which("dpkg-divert") is None, reason="needs dpkg-divert")
def test_installing_moves_the_stock_desktop_file_aside_and_removing_brings_it_back(tmp_path):
    write(tmp_path / DESKTOP, "stock\n")
    (tmp_path / "var/lib/dpkg").mkdir(parents=True)

    run_maintainer_script("preinst", tmp_path, "install")
    assert not (tmp_path / DESKTOP).exists()
    assert (tmp_path / f"{DESKTOP}.calamares-data").read_text() == "stock\n"

    # dpkg takes our own file away before postrm; the stock one comes back.
    write(tmp_path / DESKTOP, "raye\n")
    (tmp_path / DESKTOP).unlink()
    run_maintainer_script("postrm", tmp_path, "remove")
    assert not (tmp_path / f"{DESKTOP}.calamares-data").exists()
    assert (tmp_path / DESKTOP).read_text() == "stock\n"


@pytest.mark.skipif(shutil.which("dpkg-divert") is None, reason="needs dpkg-divert")
def test_an_aborted_install_still_gives_the_stock_desktop_file_back(tmp_path):
    # Our file is unpacked, the install then fails: it is still at the real
    # path when postrm runs, and the stock one has nowhere to land.
    write(tmp_path / DESKTOP, "stock\n")
    (tmp_path / "var/lib/dpkg").mkdir(parents=True)
    run_maintainer_script("preinst", tmp_path, "install")
    write(tmp_path / DESKTOP, "raye\n")
    run_maintainer_script("postrm", tmp_path, "abort-install")
    assert (tmp_path / DESKTOP).read_text() == "stock\n"


@pytest.mark.skipif(shutil.which("dpkg-divert") is None, reason="needs dpkg-divert")
def test_removing_works_when_calamares_data_went_first(tmp_path):
    # Every install ends this way: the installer removes calamares-data and
    # this package together, so the file the diversion points at may be gone.
    write(tmp_path / DESKTOP, "stock\n")
    (tmp_path / "var/lib/dpkg").mkdir(parents=True)
    run_maintainer_script("preinst", tmp_path, "install")
    (tmp_path / f"{DESKTOP}.calamares-data").unlink()
    run_maintainer_script("postrm", tmp_path, "remove")
    assert not (tmp_path / DESKTOP).exists()


@pytest.mark.skipif(shutil.which("dpkg-divert") is None, reason="needs dpkg-divert")
def test_disappearing_leaves_the_file_to_the_package_that_took_it(tmp_path):
    # Another package took our paths over: the diversion goes, the file at
    # that path is now theirs and we must not delete it.
    write(tmp_path / DESKTOP, "stock\n")
    (tmp_path / "var/lib/dpkg").mkdir(parents=True)
    run_maintainer_script("preinst", tmp_path, "install")
    (tmp_path / f"{DESKTOP}.calamares-data").unlink()
    write(tmp_path / DESKTOP, "theirs\n")
    run_maintainer_script("postrm", tmp_path, "disappear", "other", "1.0")
    assert (tmp_path / DESKTOP).read_text() == "theirs\n"


@pytest.mark.skipif(shutil.which("dpkg-divert") is None, reason="needs dpkg-divert")
def test_an_upgrade_keeps_the_diversion(tmp_path):
    write(tmp_path / DESKTOP, "stock\n")
    (tmp_path / "var/lib/dpkg").mkdir(parents=True)
    run_maintainer_script("preinst", tmp_path, "install")
    run_maintainer_script("preinst", tmp_path, "upgrade", "0.1~dev6")
    run_maintainer_script("postrm", tmp_path, "upgrade", "0.1~dev6")
    assert (tmp_path / f"{DESKTOP}.calamares-data").exists()


# ----------------------------------------------------------------------
# The list and the build wiring: what runs, and what the list still owes.

def test_no_optional_marker_on_a_path_that_is_already_there(real):
    """"?" says "the part that brings it is not written yet".

    It only does something when the path is missing, so on a path that IS
    there it is a dead letter -- and worse than nothing: the day that file
    moves or is deleted, the "?" turns the error into a note and the build
    goes on with the file left out of the package. A path that exists must
    be named without the mark, so the list speaks when it goes away. This
    is the same rule as the if(EXISTS) around an add_test() that CMakeLists
    .txt documents: a guard that reads like care and behaves like silence.

    Sources under debian/tmp are exempt: whether they are there says
    whether a build has run in this tree, not what the repository holds.
    """
    _, entries = real
    stale = sorted(f"line {e.line}: {e.source}" for e in entries
                   if e.optional and not e.from_build
                   and ((REPO / e.source).exists() or (REPO / e.source).is_symlink()))
    assert not stale, ("these paths are written: drop the \"?\" so the build stops "
                       "if they ever go away -- " + "; ".join(stale))


def pytest_targets_of_the_build():
    """The paths CMakeLists.txt hands to pytest in add_test(NAME python)."""
    text = (REPO / "CMakeLists.txt").read_text()
    block = re.search(r"add_test\(NAME python\b(.*?)\)", text, re.S)
    assert block, "CMakeLists.txt has no add_test(NAME python ...)"
    words = block.group(1).split()
    assert "pytest" in words, "add_test(NAME python) does not run pytest"
    targets, skip_next = [], False
    for word in words[words.index("pytest") + 1:]:
        if word == "WORKING_DIRECTORY":
            break
        if skip_next:
            skip_next = False
            continue
        if word.startswith("-"):
            # these options take a value of their own, which is not a path
            skip_next = word in ("-p", "-k", "-m", "-o", "--rootdir", "--ignore")
            continue
        targets.append(word)
    assert targets, "add_test(NAME python) gives pytest no path to collect"
    return targets


def test_the_build_runs_every_python_test_of_the_repository():
    """A test the packaging never runs is a test that does not exist.

    debian/rules runs the suite through ctest, and ctest runs what
    CMakeLists.txt registered: a hand-written list of folders. Such a list
    goes out of date in silence -- the launcher keeps collecting a new test
    file while the package build never touches it, and the only way to know
    is to compare. So compare: every test_*.py of this repository must sit
    under one of the paths the build hands to pytest.
    """
    targets = [pathlib.Path(t) for t in pytest_targets_of_the_build()]
    for target in targets:
        assert (REPO / target).exists(), f"CMakeLists.txt gives pytest {target}, which is not there"
    missed = []
    for path in sorted(REPO.rglob("test_*.py")):
        rel = path.relative_to(REPO)
        if ".git" in rel.parts:
            continue
        if not any(rel == t or t in rel.parents for t in targets):
            missed.append(str(rel))
    assert not missed, ("the package build never runs these: add them to "
                        "add_test(NAME python) in CMakeLists.txt -- " + ", ".join(missed))


def test_rules_makes_ctest_fail_when_it_finds_no_test():
    """ctest prints "No tests were found!!!" and exits 0.

    The whole suite can stop being registered -- a renamed folder, a
    find_package that goes missing, BUILD_TESTING flipped -- and the
    package still builds green. Only CTEST_NO_TESTS_ACTION=error turns
    that into a failure, and only if it is EXPORTED: a plain make variable
    is never seen by the ctest dh_auto_test runs.
    """
    text = (REPO / "debian/rules").read_text()
    assert re.search(r"^export[ \t]+CTEST_NO_TESTS_ACTION[ \t]*=[ \t]*error[ \t]*$", text, re.M), (
        "debian/rules must export CTEST_NO_TESTS_ACTION = error")


# The paths debian/raye-paths names with a "?" and that are not written
# yet. RAYE_PATHS_STRICT=1 turns each into an error, but that gate runs
# only on `iso/tools/raye-tests --release` -- that is, on the day the
# owner publishes, which is the worst day to learn the figure. Keeping it
# here puts it in front of whoever runs the ordinary suite, and makes it a
# ratchet: adding a "?" fails, and closing one fails until this number
# follows.
#
# Measured 2026-11-07, and the figure before this line said 11 with the
# comment "app/setup, app/firstrun, neither written". app/firstrun WAS
# written -- app/firstrun/CMakeLists.txt, committed 2026-11-06 13:49,
# installs raye-first-run on line 18. The comment was stale, and worse, the
# ratchet could not have noticed: it asked whether
# debian/tmp/usr/bin/raye-first-run exists, and a BUILD OUTPUT never exists
# outside a package build. Those two entries were therefore owed FOREVER,
# whatever anybody wrote. A ratchet that cannot come down is a number, not
# a ratchet.
#
# It now asks rp.producing_part() for a debian/tmp source: which
# written part of RAYE_PARTS installs it. That is readable with no build at
# all, and it means the day app/setup lands THIS test goes red by itself
# and demands the figure follow -- which is what a ratchet is for.
OWED = 10


def _is_owed(entry) -> bool:
    """Is this "?" entry really an unwritten part?

    For an ordinary source the file itself answers. For a source under
    debian/tmp the file CANNOT answer -- see the comment above OWED -- so
    the part that installs it answers instead.
    """
    if entry.from_build:
        return rp.producing_part(REPO, entry.source) is None
    return not ((REPO / entry.source).exists() or (REPO / entry.source).is_symlink())


def test_the_packaging_list_owes_exactly_what_it_says(real):
    _, entries = real
    owed = sorted(e.source for e in entries if e.optional and _is_owed(e))
    if len(owed) != OWED:
        way = "lower" if len(owed) < OWED else "raise"
        raise AssertionError(
            f"debian/raye-paths owes {len(owed)} paths, OWED says {OWED}: "
            f"{way} OWED in this file, and say so in debian/changelog -- " + ", ".join(owed))


def test_a_question_mark_on_a_part_that_IS_written_is_refused(real):
    """A stale "?" hides the file's disappearance, and the file says so.

    debian/raye-paths' own header: a "?" on a path that is there "does
    nothing but hide its disappearance later". Nothing enforced that until
    2026-11-07, and one had gone stale -- ?debian/tmp/usr/bin/raye-first-run,
    while app/firstrun installed it. Removing the marker is not enough: the
    next one would go unnoticed the same way.
    """
    _, entries = real
    stale = []
    for entry in entries:
        if not entry.optional:
            continue
        if entry.from_build:
            part = rp.producing_part(REPO, entry.source)
            if part is not None:
                stale.append(f"{entry.source} (line {entry.line}): {part} is "
                             f"written and installs it")
        elif (REPO / entry.source).exists() or (REPO / entry.source).is_symlink():
            stale.append(f"{entry.source} (line {entry.line}): the file is there")
    assert not stale, (
        'these "?" markers are stale -- drop the "?" and lower OWED:\n  '
        + "\n  ".join(stale))


def test_the_parts_are_read_from_cmake_and_not_copied(real):
    """producing_part() must not carry its own list of the parts.

    A second list of RAYE_PARTS would go stale the day one is added, which
    is the defect the function exists to undo. So the list is read, and
    this proves it is read from the file that owns it.
    """
    parts = rp.cmake_parts(REPO)
    assert parts, "RAYE_PARTS could not be read from CMakeLists.txt"
    text = (REPO / "CMakeLists.txt").read_text()
    for part in parts:
        assert part in text, f"{part} is not named in CMakeLists.txt"
    # and the one that is written must be found through it
    assert "app/firstrun" in parts
    assert rp.producing_part(REPO, "debian/tmp/usr/bin/raye-first-run") == "app/firstrun"


@pytest.mark.skipif(shutil.which("cmake") is None, reason="needs cmake")
def test_the_qml_test_is_named_even_when_it_cannot_run(tmp_path):
    """A check that cannot run must say so, never disappear.

    tests/ui/CMakeLists.txt needs qmltestrunner and org.raye.ui. The
    package build has neither -- iso/build.sh copies ONE repository into a
    wiped build tree, so there is no sibling theme checkout, and raye-style
    is not a Build-Depends. Measured 2026-11-06 on a copy of the source
    with no sibling: ctest listed ONE test instead of two, and the 22 QML
    checks had never run in a package build. Nothing caught it:
    CTEST_NO_TESTS_ACTION=error only fires when NO test is registered at
    all, so the Python test alone kept the build green.

    So the registration is unconditional, and names its reason through
    SKIP_REGULAR_EXPRESSION when a piece is missing. Here the missing
    piece is forced with an RAYE_UI_QML_DIR holding no module.
    """
    build = tmp_path / "build"
    done = subprocess.run(
        ["cmake", "-S", str(REPO), "-B", str(build), f"-DRAYE_UI_QML_DIR={tmp_path / 'no-module'}"],
        capture_output=True, text=True)
    if done.returncode != 0:
        pytest.skip("cmake cannot configure this tree here (Qt6 missing?): "
                    + (done.stderr.strip().splitlines() or ["no output"])[-1])
    registered = (build / "tests/ui/CTestTestfile.cmake").read_text()
    assert "qml-setup" in registered, "qml-setup vanished instead of saying why"
    assert "SKIPPED:" in registered, (
        "qml-setup is registered without a skip: a folder with no org/raye/ui "
        "was taken for a module, and the test can only die on an import error")


def image_build_sets_the_gate(tree):
    """Does the image build turn RAYE_RELEASE on? None when it cannot be told."""
    build = pathlib.Path(tree) / "iso" / "build.sh"
    if not build.is_file():
        return None
    return "RAYE_RELEASE" in build.read_text()


def test_a_build_that_sets_the_gate_is_recognised(tmp_path):
    """The reading above must be able to answer yes, or the check below
    could never go red and would prove nothing."""
    write(tmp_path / "iso/build.sh", "dpkg-buildpackage -b -us -uc\n")
    assert image_build_sets_the_gate(tmp_path) is False
    write(tmp_path / "iso/build.sh", "cmake -S . -B out -DRAYE_RELEASE=ON\n")
    assert image_build_sets_the_gate(tmp_path) is True
    assert image_build_sets_the_gate(tmp_path / "nowhere") is None


def test_the_image_build_leaves_the_release_gate_off():
    """CMakeLists.txt and the README say so, and it was measured on
    2026-11-06: iso/build.sh builds this package with `dpkg-buildpackage
    -b -us -uc` behind `env -i` and passes no -D. The day that changes, the
    package build starts failing on every path debian/raye-paths still owes
    -- in an 8 MB build log, during an image build. Better said here.
    """
    verdict = image_build_sets_the_gate(REPO.parent)
    if verdict is None:
        pytest.skip("no sibling iso repository: this cross-check needs it")
    assert verdict is False, (
        "iso/build.sh now names RAYE_RELEASE: correct the comment in CMakeLists.txt "
        "and the README, and expect the package build to stop on the OWED paths")
