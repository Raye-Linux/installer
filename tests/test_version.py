# SPDX-License-Identifier: GPL-3.0-or-later
"""The release this installer announces.

./VERSION holds the release as people read it ("0.5 Beta"). It is a mirror
of iso/VERSION, which is where the number is decided and which names the
image; this test is what keeps the mirror a mirror. The Calamares branding
is the only place in this repo that writes the version out, and every
string built from it is pinned here. The release name ("Alpenglow")
comes from iso/release-names and only follows the long forms.

Runs under pytest with the rest of tests/, and on its own without it:
    python3 -I -B tests/test_version.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent.parent
VERSION = (ROOT / "VERSION").read_text().strip()
BRANDING = ROOT / "etc/calamares/branding/raye/branding.desc"
# a record, not a place the installer reads its name from: each entry says
# what that upload was, so it may name the release (checked below)
CHANGELOG = pathlib.Path("debian/changelog")

PRODUCT = "Raye Linux"
RELEASE = r"\d+(?:\.\d+)+ B[eê]ta(?: \d+)?"
SHORT_PRODUCT = "Raye"
# directories with nothing the installer says out loud
SKIP_DIRS = {".git", "tests", "art", "assets", "__pycache__"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".gz", ".pyc", ".qm"}


def branding_strings():
    """The strings: block of branding.desc, as key -> value."""
    block = re.search(r"^strings:\n(.*?)(?=^\S)", BRANDING.read_text(), re.S | re.M)
    assert block, "branding.desc has no strings: block"
    return dict(re.findall(r"^\s+(\w+):\s+(.*?)\s*$", block.group(1), re.M))


def without_comments(text, suffix):
    """A comment that *explains* an older version must not fail a test that
    exists to protect the documentation. So comments go first."""
    if suffix in (".qml", ".js", ".cpp", ".h", ".qss"):
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        return re.sub(r"(?m)(^|\s)//.*$", "", text)
    if suffix == ".md":
        return ""  # prose: checked by test_markdown_names_only_this_release
    return re.sub(r"(?m)(^|\s)#.*$", "", text)


def test_version_is_the_beta():
    # the shape, so a half-edited VERSION ("0.2", "0.2 beta") is caught
    assert re.fullmatch(r"\d+(?:\.\d+)+ Beta(?: \d+)?", VERSION), VERSION


def release_name():
    """The name iso/release-names gives this release, or None without a
    sibling iso. Read by iso's own parser (tools/release_name.py), which is
    also what wrote branding.desc."""
    tool = ROOT.parent / "iso" / "tools" / "release_name.py"
    if not tool.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("release_name", tool)
    rn = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rn)
    version, name, full = rn.release(tool.parent.parent)
    assert version == VERSION, f"iso/VERSION is {version!r}, ./VERSION is {VERSION!r}"
    return name, full


def test_branding_says_the_release():
    s = branding_strings()
    assert s["productName"] == PRODUCT, s["productName"]
    assert s["shortProductName"] == SHORT_PRODUCT, s["shortProductName"]
    # the release as people read it: VERSION, or VERSION with its name in
    # place of the beta's number ("1.0 Beta 2" named Sundog: "1.0 Beta Sundog")
    number = re.escape(VERSION.split()[0])
    assert re.fullmatch(number + r"(?: Beta)?(?: \d+| [A-Za-z]+)?", s["version"]), s["version"]
    expected = release_name()
    if expected is not None:
        name, full = expected
        assert s["version"] == full, (
            f"branding says {s['version']!r}, iso/release-names makes this release {full!r}")
        if name:
            assert s["version"].endswith(" " + name), s["version"]
    # every line Setup can show says the same release (window title, welcome)
    assert s["shortVersion"] == s["version"], s["shortVersion"]
    assert s["versionedName"] == f"{PRODUCT} {s['version']}", s["versionedName"]
    assert s["shortVersionedName"] == f"{SHORT_PRODUCT} {s['version']}", s["shortVersionedName"]
    # the boot entry is the product, never the version: it outlives the release
    assert s["bootloaderEntryName"] == PRODUCT, s["bootloaderEntryName"]


def test_nothing_else_spells_the_release_out():
    """branding.desc is the one place, so there is one place to edit."""
    number = re.escape(VERSION.split()[0])
    spelt = re.compile(r"(?:Raye(?: Linux)?[ _-]+)?%s[ _-]+Beta" % number, re.I)
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if (not path.is_file() or path == BRANDING or rel.name == "VERSION"
                or rel == CHANGELOG
                or SKIP_DIRS & set(rel.parts) or path.suffix in SKIP_SUFFIXES):
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for line in without_comments(text, path.suffix).splitlines():
            assert not spelt.search(line), f"{rel}: the release is spelt out: {line.strip()}"


def test_changelog_names_only_this_release():
    """The newest entry is the upload this installer is: when it names a
    release, it is this one. Older entries keep the release they were."""
    text = (ROOT / CHANGELOG).read_text()
    newest = text.split("\n -- ", 1)[0]
    for found in re.findall(RELEASE, newest):
        assert found == VERSION, f"debian/changelog names {found!r}, this release is {VERSION!r}"


def test_markdown_names_only_this_release():
    """The documentation explains the rule by quoting the number, so the
    number is in it. Checked rather than skipped: documentation left on an
    older release is how people learn the wrong version. French prose
    writes "Bêta", which is the same release."""
    for page in sorted(ROOT.rglob("*.md")):
        if ".git" in page.parts:
            continue
        for found in re.findall(RELEASE, page.read_text()):
            assert found.replace("Bêta", "Beta") == VERSION, (
                f"{page.relative_to(ROOT)} names {found!r}, this release is {VERSION!r}")

def test_mirrors_the_iso_version():
    """iso/VERSION decides the number; this repo only follows it.

    The image is built with every repo checked out side by side, so this
    compares for real there. A lone clone has no sibling: the check says
    so out loud rather than passing in silence.
    """
    source = ROOT.parent / "iso" / "VERSION"
    if not source.is_file():
        print(f"no sibling {source}: cross-check skipped, ./VERSION not compared")
        return
    assert source.read_text() == (ROOT / "VERSION").read_text(), (
        f"./VERSION is {VERSION!r}, iso/VERSION is {source.read_text().strip()!r}")


def test_calamares_loads_this_branding():
    """The About box only says "Raye Linux 0.5 Beta" if Calamares reads THIS file.

    settings.conf names a branding component, Calamares looks for a folder
    of that name under branding/, and refuses a branding.desc whose
    componentName is not the folder's name. Any of the three drifting and
    the setup falls back to Calamares' own strings: the About box, the
    window title and the bootloader entry would all stop naming Raye, with
    nothing failing and every test above still green -- they prove the file
    says the release, never that the file is the one read.
    """
    named = re.search(r"^branding:\s*(\S+)\s*$", (ROOT / "etc/calamares/settings.conf").read_text(), re.M)
    assert named, "settings.conf names no branding component"
    component = re.search(r"^componentName:\s*(\S+)\s*$", BRANDING.read_text(), re.M)
    assert component, "branding.desc has no componentName"
    folder = BRANDING.parent.name
    assert named.group(1) == folder == component.group(1), (
        f"settings.conf asks for {named.group(1)!r}, the folder is {folder!r}, "
        f"branding.desc calls itself {component.group(1)!r}")


if __name__ == "__main__":  # without pytest
    bad = 0
    for name, case in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            case()
            print(f"ok - {name}")
        except AssertionError as error:
            bad += 1
            print(f"FAIL - {name}: {error}")
    sys.exit(1 if bad else 0)
