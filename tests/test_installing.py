# SPDX-License-Identifier: GPL-3.0-or-later
"""The page shown while Raye installs (etc/calamares/branding/raye/show.qml).

What Calamares really gives this page, measured on 3.3.14 (2026-11-06):

  io.calamares.ui.Branding        an object
  io.calamares.core.ViewManager   a model: currentStepIndex, the button
                                  labels, isDebugMode, logFilePath -- and
                                  NO percentage
  io.calamares.core.Global        GlobalStorage, read-only from QML

  `strings` over libcalamares*.so finds exactly those three namespaces and
  no fourth. The percentage lives on JobQueue::progress(qreal, QString), a
  C++ signal ExecutionViewStep consumes to fill two widgets of its own,
  named `exec-progress` (a QProgressBar) and `exec-message` (a QLabel) --
  both names are in the library, both are styled in stylesheet.qss, and
  both are drawn by Calamares UNDER this page.

So the true percentage is already on screen and this page adds the stage in
words. A second percentage of our own could only disagree with the first,
and the way an installer loses someone's data is a bar that sits at 99 %
long enough for them to cut the power in the middle of a disk write. The
checks below are what keeps one from being drawn.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).parent.parent
BRANDING = REPO / "etc/calamares/branding/raye"
SHOW = (BRANDING / "show.qml").read_text()
STRINGS = (BRANDING / "strings.js").read_text()
STYLESHEET = (BRANDING / "stylesheet.qss").read_text()
RUN = (REPO / "usr/libexec/raye-setup-run").read_text()

# show.qml with its comments taken out: the checks below are about what the
# page DOES, and the comments are free to discuss what it must not do.
CODE = re.sub(r"^\s*//.*$", "", SHOW, flags=re.M)

# The path show.qml reads the stage out of.
LOG = "file:///root/.cache/calamares/session.log"


def test_the_page_claims_no_stage_before_it_has_read_one():
    """It used to start at installDisk. Anyone whose log could not be read
    -- a moved path, a missing XHR permission -- was told Raye was
    partitioning their disk, and told it for the whole install.
    """
    assert re.search(r'^\s*property string stage: ""$', SHOW, re.M), (
        'the stage must start empty: a stage named before any job line is '
        'read is a claim about the disk nobody checked'
    )
    assert 'S.t(show.lang, "installStarting")' in SHOW
    for lang in ("en", "fr"):
        assert re.search(r'^        installStarting: "', STRINGS, re.M)


def test_the_page_invents_no_percentage():
    """Nothing here may compute a figure. The real one is Calamares'."""
    # a figure needs either a per-cent sign of its own or the arithmetic
    # that makes one. (The one % in the file is the modulo that wraps the
    # slideshow round, which is why this looks for a string literal.)
    assert not re.search(r"""['"][^'"]*%[^'"]*['"]""", CODE), (
        "a per-cent sign in a literal: the only percentage on this screen "
        "is the one Calamares draws"
    )
    for forbidden in ("* 100", "*100", "/ 100", "toFixed", "percent"):
        assert forbidden not in CODE, forbidden
    # an indeterminate ring, never one driven by a value of ours
    ring = re.search(r"ProgressRing \{(.*?)\n(\s*)\}", CODE, re.S)
    assert ring, "the ring is gone"
    assert "value" not in ring.group(1), (
        "ProgressRing carries a value: a ring that fills up is a percentage, "
        "and this page has no honest number to fill it with"
    )
    # the two ways a fabricated bar gets written
    for forbidden in ("Date.now", "elapsed", "new Date", "estimate"):
        assert forbidden not in CODE, forbidden


def test_calamares_own_progress_stays_visible():
    """The stylesheet is where the real percentage could be hidden by
    accident: `max-height: 0px` is how this very file removes the widgets
    it does not want (BootInfoWidget, the slideshow toolbar). Hidden, the
    page would have the stage in words and no figure at all.
    """
    for name in ("#exec-progress", "#exec-message"):
        block = re.search(re.escape(name) + r"\s*\{(.*?)\}", STYLESHEET, re.S)
        assert block, f"{name} is not styled any more"
        for killer in re.findall(r"max-(?:height|width):\s*(\d+)px", block.group(1)):
            assert int(killer) > 0, f"{name} is hidden: {block.group(1)!r}"
    assert re.search(r"#exec-progress\s*\{[^}]*min-height:\s*([1-9]\d*)px",
                     STYLESHEET, re.S), "the bar has no height"


def test_the_stage_rules_live_where_a_test_can_run_them():
    """tests/ui/tst_setup.qml runs them against the job names Calamares
    really writes. It can only do that while they are functions of
    strings.js; a table inside show.qml is unreachable from any runner the
    repository has.
    """
    assert "S.installStageOf(" in SHOW and "S.installStep(" in SHOW
    assert "words:" not in CODE, "the rules table is back inside the page"
    assert "function installStageOf" in STRINGS
    assert "function installStep" in STRINGS


def test_the_details_pane_is_the_log_and_nothing_else():
    assert 'S.t(show.lang, show.detailsOpen ? "hideDetails" : "showDetails")' in SHOW
    assert "readOnly: true" in SHOW, "the log pane must not be editable"
    assert LOG in SHOW


def test_nothing_moves_the_log_out_from_under_the_page():
    """show.qml reads one fixed path. It is the right one only because
    Calamares runs as root with neither HOME nor XDG_CACHE_HOME carried
    over, which puts Qt's cache location at /root/.cache: the day one of
    them is added to --preserve-env the file moves, the read returns
    nothing, and the stage never advances. QML_XHR_ALLOW_FILE_READ is the
    other half -- without it the read is refused.
    """
    preserved = re.search(r"--preserve-env=([A-Za-z0-9_,]+)", RUN)
    assert preserved, "raye-setup-run no longer starts Calamares with sudo"
    carried = preserved.group(1).split(",")
    for variable in ("HOME", "XDG_CACHE_HOME"):
        assert variable not in carried, (
            f"{variable} is carried into Calamares, so Qt's cache location "
            f"is no longer /root/.cache and show.qml reads nothing: either "
            f"drop it or change {LOG}"
        )
    assert "QML_XHR_ALLOW_FILE_READ" in carried, (
        "without it the page cannot read the log, and the stage never moves"
    )


# The pictures are screens of Raye, with Raye's own words on them, so each
# language gets its own set: a French install showing "Pinned" and "Check for
# updates" looks like the translation stopped halfway. One entry per picture
# in show.qml, one folder per language strings.js knows.
SLIDE = re.compile(r'\{ name: "(\w+)", key: "(\w+)" \}')
LANGUAGES = re.findall(r"^    ([a-z]{2}): \{$", STRINGS, re.M)
SLIDES = BRANDING / "slides"


def jpeg_size(path):
    data = path.read_bytes()
    assert data[:2] == b"\xff\xd8", f"{path} is not a JPEG"
    at = 2
    while at < len(data):
        marker, length = data[at + 1], int.from_bytes(data[at + 2:at + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[at + 5:at + 7], "big")
            width = int.from_bytes(data[at + 7:at + 9], "big")
            return width, height
        at += 2 + length
    raise AssertionError(f"{path}: no frame header")


def test_the_slideshow_has_a_tip_for_every_picture():
    slides = SLIDE.findall(CODE)
    assert len(slides) >= 3, slides
    assert sorted(LANGUAGES) == ["en", "fr"], LANGUAGES
    for _, key in slides:
        for lang in LANGUAGES:
            block = re.search(r"^    %s: \{\n(.*?)^    \}" % lang, STRINGS, re.S | re.M).group(1)
            assert re.search(r'^\s+%s: "' % key, block, re.M), (lang, key)


def test_every_language_has_its_own_pictures():
    names = sorted(name for name, _ in SLIDE.findall(CODE))
    assert names, "no picture found in show.qml"
    for lang in LANGUAGES:
        have = sorted(p.stem for p in (SLIDES / lang).glob("*.jpg"))
        assert have == names, (
            f"slides/{lang}/ holds {have}, the slideshow shows {names}: "
            f"an install in that language would show a blank frame"
        )
        for name in names:
            # the frame is 16:9; 960x540 is what every picture was made at
            assert jpeg_size(SLIDES / lang / f"{name}.jpg") == (960, 540), (lang, name)
    folders = sorted(p.name for p in SLIDES.iterdir() if p.is_dir())
    assert folders == sorted(LANGUAGES), f"slides/ has folders {folders}"
    assert not list(SLIDES.glob("*.jpg")), "a picture outside a language folder"


def test_the_picture_follows_the_language():
    # the path is built from show.lang, the same value the tip under it uses
    assert re.search(r'"slides/"\s*\+\s*show\.lang\s*\+\s*"/"', CODE), (
        "show.qml no longer picks the pictures by language"
    )
