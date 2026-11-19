# SPDX-License-Identifier: GPL-3.0-or-later
"""Raye Setup's pages: both languages say everything, and settings.conf,
strings.js (the stages of the top bar) and the page files agree."""
import pathlib
import re

REPO = pathlib.Path(__file__).parent.parent
ETC = REPO / "etc/calamares"
BRANDING = ETC / "branding/raye"
STRINGS = (BRANDING / "strings.js").read_text()
LANGUAGE = (BRANDING / "pages/Language.qml").read_text()
PREFLIGHT = (REPO / "usr/libexec/raye-preflight").read_text()


def js_list(name):
    """A top-level `var name = ["a", "b"]` of strings.js."""
    m = re.search(r"^var %s = \[(.*?)\]" % re.escape(name), STRINGS, re.S | re.M)
    assert m, f"strings.js has no {name}"
    return re.findall(r'"([^"]+)"', m.group(1))


def preflight_findings():
    """Every word raye-preflight can print as the first field of a line.

    Two shapes, and both have to be read. A pattern that knows only one of
    them finds a subset and says nothing: the first version of this
    function was anchored at the start of a line and saw ONE word out of
    three, because raye-preflight writes some of them after a && on the
    same line. The second shape is ntfs_finding(), whose case arms echo the
    word alone and whose caller prints it.
    """
    direct = re.findall(r'echo "([a-z-]+) \$', PREFLIGHT)
    block = re.search(r"ntfs_finding\(\) \{(.*?)\n\}", PREFLIGHT, re.S)
    assert block, "raye-preflight no longer classifies NTFS volumes"
    classified = re.findall(r'echo "([a-z-]+)"', block.group(1))
    assert classified, "ntfs_finding() names no finding at all"
    return sorted(set(direct) | set(classified))

# show sequence entry -> the step name strings.js and the page use
STEP_OF = {
    "welcomeq": "language",
    "localeq": "region",
    "keyboardq": "keyboard",
    "notesqml@raye_network": "network",
    "notesqml@raye_disk": "disk",
    "notesqml@raye_device": "device",
    "notesqml@raye_account": "account",
    "usersq": "user",
    "notesqml@raye_privacy": "privacy",
    "notesqml@raye_desktop": "desktop",
    "summaryq": "ready",
    "finishedq": "done",
}


def language_keys(lang):
    block = re.search(r"^    %s: \{\n(.*?)^    \}" % lang, STRINGS, re.S | re.M).group(1)
    return dict(re.findall(r'^\s+(\w+): "((?:[^"\\]|\\.)*)"', block, re.M))


def show_sequence():
    """The views of settings.conf in order, the exec phase as "exec"."""
    steps, part = [], None
    for line in (ETC / "settings.conf").read_text().splitlines():
        if line.startswith("- show:"):
            part = "show"
        elif line.startswith("- exec:"):
            part = "exec"
            steps.append("exec")
        elif not line.startswith("  - "):
            part = None if not line.startswith(" ") else part
        elif part == "show":
            steps.append(line[4:].strip())
    return steps


def page_file(entry):
    module, _, instance = entry.partition("@")
    if module == "notesqml":
        conf = (ETC / "modules" / f"notesqml_{instance}.conf").read_text()
        return BRANDING / (re.search(r"^qmlFilename: (\S+)", conf, re.M).group(1) + ".qml")
    return BRANDING / f"{module}.qml"


def test_both_languages_have_the_same_words():
    en, fr = language_keys("en"), language_keys("fr")
    assert len(en) > 100
    assert set(en) == set(fr)


def test_placeholders_match_between_languages():
    en, fr = language_keys("en"), language_keys("fr")
    for key in en:
        assert sorted(re.findall(r"%\d", en[key])) == sorted(re.findall(r"%\d", fr[key])), key


def test_french_punctuation_does_not_break_at_the_end_of_a_line():
    for key, text in language_keys("fr").items():
        assert " ?" not in text and " :" not in text, key


def test_no_exclamation_marks():
    for lang in ("en", "fr"):
        for key, text in language_keys(lang).items():
            assert "!" not in text, (lang, key)


def test_steps_of_strings_js_follow_the_show_sequence():
    names = re.search(r"var steps = \[(.*?)\]", STRINGS, re.S).group(1)
    steps = re.findall(r'"(\w+)"', names)
    expected = ["installing" if e == "exec" else STEP_OF[e] for e in show_sequence()]
    assert steps == expected


def test_every_step_is_in_one_stage():
    steps = re.findall(r'"(\w+)"', re.search(r"var steps = \[(.*?)\]", STRINGS, re.S).group(1))
    staged = re.findall(r'"(\w+)"', "".join(re.findall(r"steps: \[(.*?)\]", STRINGS)))
    assert sorted(staged) == sorted(steps)


def test_every_qml_page_exists_and_names_its_step():
    for entry in show_sequence():
        if entry in ("exec", "partition"):
            continue
        wrapper = page_file(entry)
        text = wrapper.read_text()
        assert f'step: "{STEP_OF[entry]}"' in text, wrapper
        page = BRANDING / re.search(r'source: "([^"]+)"', text).group(1)
        assert page.is_file(), page
        assert f'step: "{STEP_OF[entry]}"' in page.read_text(), page


def test_pages_calamares_loads_import_nothing_heavy():
    # Calamares loads every page at start, each in an engine of its own:
    # what it loads must not pull the setup look in (see LazyPage.qml)
    for entry in show_sequence():
        if entry in ("exec", "partition"):
            continue
        imports = re.findall(r"^import (.*)$", page_file(entry).read_text(), re.M)
        assert imports == ['"components"'], (entry, imports)
    lazy = (BRANDING / "components/LazyPage.qml").read_text()
    assert "org.raye" not in lazy


def test_qml_pages_are_found_in_the_branding_folder():
    for entry in show_sequence():
        if entry in ("exec", "partition"):
            continue
        module = entry.partition("@")[0]
        name = f"notesqml_{entry.partition('@')[2]}.conf" if module == "notesqml" else f"{module}.conf"
        assert re.search(r"^qmlSearch: branding$", (ETC / "modules" / name).read_text(), re.M), name


def test_pages_never_write_to_calamares_globalstorage():
    # read-only from QML: a write throws and the page stops half way
    for path in BRANDING.rglob("*.qml"):
        assert not re.search(r"Global\.(insert|remove)\(", path.read_text()), path


def test_branding_puts_the_bars_where_the_pages_expect_them():
    desc = (BRANDING / "branding.desc").read_text()
    assert re.search(r"^sidebar: qml,top$", desc, re.M)
    assert re.search(r"^navigation: qml,bottom$", desc, re.M)
    assert re.search(r"^windowExpanding: fullscreen$", desc, re.M)


def test_calamares_own_cancel_is_off_and_install_is_not_asked_twice():
    conf = (ETC / "settings.conf").read_text()
    assert re.search(r"^disable-cancel: true$", conf, re.M)
    assert re.search(r"^prompt-install: false$", conf, re.M)


def test_setup_choices_job_runs_after_the_clock_and_the_account():
    conf = (ETC / "settings.conf").read_text()
    exec_part = conf.split("- exec:", 1)[1].split("- show:", 1)[0]
    jobs = [line[4:].strip() for line in exec_part.splitlines() if line.startswith("  - ")]
    at = jobs.index("rayesetupchoices")
    assert jobs.index("hwclock") < at
    assert jobs.index("usersq") < at
    assert at < jobs.index("initramfs")


def exec_jobs():
    conf = (ETC / "settings.conf").read_text()
    exec_part = conf.split("- exec:", 1)[1].split("- show:", 1)[0]
    return [line[4:].strip() for line in exec_part.splitlines() if line.startswith("  - ")]


def test_desktop_job_runs_after_the_account_and_the_package_lists():
    jobs = exec_jobs()
    at = jobs.index("rayedesktop")
    # the account and the sign-in screen's settings exist, and apt has read
    # the online lists when there is a network
    for before in ("usersq", "displaymanager", "packages"):
        assert jobs.index(before) < at, before
    assert at < jobs.index("umount")


def test_desktop_page_comes_right_before_the_summary():
    steps = js_list("steps")
    assert steps.index("desktop") == steps.index("ready") - 1


def test_kde_is_what_the_desktop_page_picks_by_default():
    page = (BRANDING / "pages/Desktop.qml").read_text()
    assert re.search(r'property string choice: "plasma"', page)
    en, fr = language_keys("en"), language_keys("fr")
    assert "recommended" in en["desktopPlasma"] and "recommandé" in fr["desktopPlasma"]


# ------------------------------------------------- the two the image showed


def test_the_language_list_capitalises_through_one_function():
    """Qt hands a language its own name, lower case in French. The list
    capitalises every row, and does it in ONE place: tests/ui/tst_setup.qml
    runs that function for real, and can only do so while it is a function.
    """
    assert "S.languageRow(label, englishLabel)" in LANGUAGE, (
        "the language rows must read S.languageRow(label, englishLabel): capitalising inline "
        "puts the rule where no test can run it"
    )
    for path in BRANDING.rglob("*.qml"):
        assert "charAt(0).toUpperCase()" not in path.read_text(), path


def test_the_warning_card_takes_its_title_from_one_function():
    """The card said "next to Windows" over a line about another Linux
    system (2026-11-02 image). Which findings are Windows' doing is a list
    in strings.js, not a condition written into the page.
    """
    assert "S.t(page.lang, S.beforeKey(page.findings))" in LANGUAGE, LANGUAGE
    assert "beforeTitleDisk" not in LANGUAGE, (
        "the page must not pick the title itself"
    )
    windows = set(js_list("windowsFindings"))
    # a ratchet, like OWED in debian/test_raye_paths.py: a finding joins
    # the Windows title by a deliberate act, never by being added nearby
    assert windows == {"bitlocker", "hibernated", "ntfs-dirty", "ntfs-check"}, (
        "raise or lower this set on purpose: it decides which findings let "
        "the card say Windows"
    )
    assert windows <= set(js_list("diskFindings"))
    # the one the 2026-11-02 image showed: another Linux system on the
    # disk is not Windows' doing and the title must not say it is
    assert "shared-efi" not in windows


def test_every_finding_raye_preflight_prints_has_words_in_both_languages():
    """The card shows the findings it knows and drops the rest. A word
    raye-preflight grows and strings.js has never heard of is therefore
    invisible: the disk nobody understood becomes silence. Found by
    reading both files, 2026-11-06.
    """
    en, fr = language_keys("en"), language_keys("fr")
    found = preflight_findings()
    assert found, "no echo line of raye-preflight was recognised"
    known = js_list("diskFindings")
    for word in found:
        assert word in known, (
            f"raye-preflight prints {word!r} and strings.js diskFindings does "
            "not list it: the language page would drop the line"
        )
        key = re.sub(r"-([a-z])", lambda m: m.group(1).upper(), word)
        assert key in en and key in fr, (key, word)


def test_no_finding_is_listed_that_raye_preflight_never_prints():
    """Dead wording reads like a case that is covered."""
    assert sorted(js_list("diskFindings")) == preflight_findings()


def test_slideshow_does_not_say_updates_wait_for_a_restart():
    # since 0.3 most updates install while the PC is in use
    tips = re.findall(r'tipUpdate: "([^"]*)"', STRINGS)
    assert len(tips) == 2
    assert not any("when you restart" in t or "au redémarrage" in t for t in tips)
