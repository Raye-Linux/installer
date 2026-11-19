# SPDX-License-Identifier: GPL-3.0-or-later
"""Every string Raye Setup shows a person must exist in French.

Setup is the text someone reads BEFORE they have Raye. A word missing
here is the first word of the system, so this file is stricter about the
sweep being real than about any single string.

Adapted from store/tests/test_i18n.py. The shape of the two defects is
that file's; the mechanism is not, and the difference matters:

  raye-store   gettext. po/fr/raye-store.po, i18n() in the source.
  installer    NO gettext at all, and no .po anywhere in the tree.
               Four catalogues of its own, measured 2026-11-06:
                 strings.js            143 keys, words.en / words.fr, read
                                       through S.t(lang, key)
                 rayeencryption        TEXT = {"en": {...}, "fr": {...}}, 6
                 rayesetupchoices      NAME = {"en": ..., "fr": ...}, 1
                 two .desktop files    Name/Comment/GenericName + [fr], 5
               155 visible strings, 155 French, 0 missing.

THE TWO DEFECTS, because neither catches the other.

  (a) A string is MARKED and has no French.
      strings.js key parity and placeholder parity are already held by
      test_branding.py (test_both_languages_have_the_same_words,
      test_placeholders_match_between_languages) -- this file does NOT
      repeat them. What nothing held before this file: the three OTHER
      catalogues. The Python job modules and the .desktop files are
      invisible to that test, and a job name is the one line of Setup
      that shows while the disk is being written.

  (b) A string is VISIBLE and never marked at all.
      No tool reports this one: there is no catalogue to be absent from.
      It is the common defect and the silent one. A literal sitting in a
      slot that renders text is the evidence, so the filter is narrow and
      position is what convicts.

THE FRONTIER -- WHOSE WORDS ARE THESE. Setup is Calamares wearing Raye's
branding, and Calamares ships its own catalogues (calamares.mo,
calamares-python.mo). This file covers ONLY what Raye adds. Asking it to
cover Calamares' strings would make it demand the translation of a third
party's project, and it would be switched off the week after.

  Raye's, and in here:     strings.js, the two Python job catalogues, the
                           .desktop files.
  Calamares', and NOT:     ViewManager.backLabel / .nextLabel (reached
                           through calamares-navigation.qml's calamares()),
                           config.unsatisfiedRequirements[].negatedText,
                           and the pretty names of its own modules
                           (partition, unpackfs, bootloader...).

  The frontier is not a convention this file invented -- the code draws
  it, at calamares-navigation.qml:40. `rayeWords` is true for fr and en
  only; when it is false the bar stops calling t() and calls
  calamares(ViewManager.nextLabel) instead. Raye's words on one side of
  that boolean, Calamares' on the other.

  🚨 And the frontier only holds while Calamares actually loads this
  branding. Three names have to agree -- settings.conf's `branding:`,
  the folder under etc/calamares/branding/, and branding.desc's
  componentName. Any of them drifting and EVERY string falls back to
  Calamares' own with nothing on screen looking broken. That is held by
  test_version.py:112, so it is not repeated here; it is named because a
  reader of this file needs to know the sweep rests on it.

WHAT THIS TEST CANNOT SEE, said plainly rather than left to be assumed:

  * Whether a translation is RIGHT. Only the four NTFS remedies below are
    checked for meaning, because those four are the ones that prevent a
    person destroying their Windows. Everything else could say anything.
  * A key built while the program runs -- t(lang, prefix + suffix). No
    reader of the source can follow it. findingKey() in strings.js maps
    "ntfs-dirty" to ntfsDirty by rule, and test_branding.py covers that
    pairing from the preflight side.
  * Text that arrives from outside: Calamares' own catalogues (above),
    Qt's QLocale::nativeLanguageName for the language and country lists,
    and the time-zone names.
  * app/setup and app/firstrun, which do not exist yet. CMakeLists.txt
    lists them in RAYE_PARTS and skips them; INTERFACE_DIRS already
    names them, so they are swept the day they land.
  * A string marked, translated, and then shown in the wrong place.

🚨 WHY THE FLOORS AND THE NON-EMPTY GUARDS EXIST. A test that walks a
list and asserts something about every item PASSES -- green, silent --
when the list is empty: zero items, zero assertions, nothing said. A
renamed folder, a regex that stops matching, a catalogue cut to its
header: each empties a list, and this whole file would then report
success while protecting nothing. So every collection reasoned about
here is asserted non-empty, against a floor well below what is there
today. The guards are tests of their own, in class Guards.
"""
import ast
import pathlib
import re
import unittest

# --------------------------------------------------------------- CONFIG
ROOT = pathlib.Path(__file__).resolve().parent.parent
BRANDING = ROOT / "etc/calamares/branding/raye"
STRINGS_JS = BRANDING / "strings.js"
# Every folder holding Raye's own interface. app/* is not written yet.
INTERFACE_DIRS = ("etc/calamares/branding/raye", "qml/org/raye/setup",
                  "app/setup", "app/firstrun")
# The Python job modules that carry their own en/fr tables.
JOB_MODULES = ("usr/lib/calamares/modules/rayeencryption/main.py",
               "usr/lib/calamares/modules/rayekeep/main.py",
               "usr/lib/calamares/modules/rayesetupchoices/main.py")
DESKTOP_FILES = ("usr/share/wayland-sessions/raye-setup.desktop",
                 "usr/share/wayland-sessions/raye-try.desktop",
                 "usr/share/applications/raye-install.desktop")
# .desktop keys a person reads, so each needs a [fr].
DESKTOP_KEYS = ("Name", "Comment", "GenericName")

# Today: 143 strings.js keys, 26 interface files, 115 visible slots,
# 7 job-table entries, 5 desktop keys. A floor catches a collapse to
# nothing; it is not meant to be raised each time a string is added.
FLOORS = {"catalogue": 110, "interface_files": 18, "visible_slots": 80,
          "job_strings": 5, "desktop_keys": 4}

# Slots whose value goes on the screen.
VISIBLE_SLOTS = ("text", "title", "description", "detail", "errorText",
                 "placeholderText")

# The ONE visible literal in Setup that is deliberately English, with
# the reason, because an unexplained allowance becomes a hole.
#
# Language.qml shows it under `visible: !page.rayeWords`, and
# rayeWords is `lang === "fr" || code === "en"`. So it appears only when
# the chosen language is neither French nor English -- the case where
# Raye has no words at all and English is the whole of what it can
# offer. Putting it in strings.js would add a French line that can never
# render: when lang is fr, rayeWords is true and the notice is hidden.
ENGLISH_ON_PURPOSE = {"Some of Setup is shown in English."}

# THE FOUR REFUSALS THAT PREVENT A LOST WINDOWS.
# raye-preflight finds a Windows that cannot be shrunk and Setup refuses,
# naming the fix. A remedy that loses a step in one language sends
# somebody to force a resize on a dirty volume. Each entry is the exact
# step that must survive translation, in both languages.
#
# Deliberately NOT a check that the two languages say the same thing --
# they must not. The French names the French Windows labels ("Activer le
# démarrage rapide" is what that checkbox reads in Windows), and a
# translation that kept the English labels would be the real defect.
NTFS_REMEDIES = {
    "hibernated": {
        "en": ("fast startup", "shut down"),
        "fr": ("démarrage rapide", "décochez"),
    },
    "ntfsDirty": {
        # shut down from the Start menu -- and NOT the two things that
        # look like shutting down and leave the volume dirty.
        "en": ("Start menu", "Sleep", "Restart"),
        "fr": ("menu Démarrer", "Veille", "Redémarrer"),
    },
    "ntfsCheck": {
        # the command, the privilege it needs, and twice.
        "en": ("chkdsk /f", "administrator", "twice"),
        "fr": ("chkdsk /f", "administrateur", "deux fois"),
    },
    "ntfsUnknown": {
        "en": ("Erase the disk", "another"),
        "fr": ("Effacez le disque", "autre"),
    },
}

# Raye is a system: masculine in French. Setup says "Raye est installé",
# "Raye n'est pas encore installé", "Raye n'a pas pu être installé".
# The Store's statuses are feminine because they agree with
# "application" -- that agreement must not be carried over here.
FEMININE_SLIPS = (
    (r"Raye[^.]{0,80}\belle\b", "Raye is masculine in French (Raye est installé)"),
    (r"\bRaye [^.]{0,40}install[eé]e\b", "Raye is masculine: installé, not installée"),
)


# ---------------------------------------------------------------- READERS
def language_block(lang):
    """The words of one language in strings.js, key -> text."""
    src = STRINGS_JS.read_text(encoding="utf-8")
    block = re.search(r"^    %s: \{\n(.*?)^    \}" % lang, src, re.S | re.M)
    assert block, f"strings.js has no {lang} block"
    return dict(re.findall(r'^\s+(\w+): "((?:[^"\\]|\\.)*)"', block.group(1), re.M))


def interface_files():
    out = []
    for d in INTERFACE_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue          # app/* is not written yet
        out += [p for p in sorted(base.rglob("*")) if p.suffix in (".qml", ".js")]
    return out


MARKER = re.compile(r"\b(?:[A-Za-z_]\w*\.)?t\s*\(")
COMPARED = re.compile(r'[!=]==?\s*"[^"]*"')
SLOT = re.compile(r"^\s*(?:readonly\s+)?(?:property\s+string\s+)?("
                  + "|".join(VISIBLE_SLOTS) + r")\s*:\s*(.+?)\s*$")


def without_markers(expr):
    """The expression with every t(...) call and its arguments removed.

    A key is a literal too: S.t(lang, "regionTitle") holds the string
    "regionTitle", and a sweep that cannot tell a key from a sentence
    reports all 115 slots. Measured: 87 false hits before this.
    """
    out, i = [], 0
    while i < len(expr):
        m = MARKER.search(expr, i)
        if not m:
            out.append(expr[i:])
            break
        out.append(expr[i:m.start()])
        depth, j = 0, m.end() - 1
        while j < len(expr):
            if expr[j] == "(":
                depth += 1
            elif expr[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        i = j + 1
    return "".join(out)


def visible_slots():
    """Every assignment to a slot that renders text: (file, line, slot, expr)."""
    found = []
    for path in interface_files():
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            m = SLOT.match(line)
            if m:
                found.append((path, n, m.group(1), m.group(2)))
    return found


def unmarked_literals():
    """Slots showing a literal that never went through t() -- defect (b)."""
    bad = []
    for path, n, slot, expr in visible_slots():
        # a literal being COMPARED is a value looked for, not shown:
        # `S.steps[bar.step] === "disk" ? ...` holds "disk" and shows none.
        rest = COMPARED.sub("", without_markers(expr))
        for lit in re.findall(r'"((?:[^"\\]|\\.)*)"', rest):
            if not re.search(r"[A-Za-zÀ-ÿ]{2}", lit):
                continue      # "• ", ": ", " : " -- punctuation
            if lit in ENGLISH_ON_PURPOSE:
                continue
            bad.append((path.relative_to(ROOT), n, slot, lit))
    return bad


def job_table(path):
    r"""The en/fr table of a job module, lang -> {key: text}.

    Read with ast, not a regex. The notice of rayeencryption holds
    {unlocked} and {key} as format placeholders, so a non-greedy
    `\{(.*?)\}` ends at the first of those and reads one key out of six
    -- a reader that finds a subset and says nothing.
    """
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [k.value for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        if "en" not in keys or "fr" not in keys:
            continue
        out = {}
        for k, v in zip(node.keys, node.values):
            if not (isinstance(k, ast.Constant) and k.value in ("en", "fr")):
                continue
            if isinstance(v, ast.Dict):
                out[k.value] = {kk.value: True for kk in v.keys
                                if isinstance(kk, ast.Constant)}
            else:
                out[k.value] = {"_": True}
        return out
    return {}


def desktop_entries(path):
    """key -> set of language suffixes present ("" for the plain key)."""
    out = {}
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\w+)(?:\[([a-zA-Z_]+)\])?=", line)
        if m and m.group(1) in DESKTOP_KEYS:
            out.setdefault(m.group(1), set()).add(m.group(2) or "")
    return out


# ------------------------------------------------------------------ TESTS
class Guards(unittest.TestCase):
    """What stops this file from passing by having looked at nothing."""

    def test_the_catalogue_was_read(self):
        self.assertTrue(STRINGS_JS.exists(), f"{STRINGS_JS} is missing")
        en = language_block("en")
        self.assertGreaterEqual(
            len(en), FLOORS["catalogue"],
            f"only {len(en)} keys read from strings.js: the reader stopped "
            "matching, or the catalogue lost most of itself")

    def test_the_interface_was_found(self):
        files = interface_files()
        self.assertGreaterEqual(
            len(files), FLOORS["interface_files"],
            f"only {len(files)} interface files found under {INTERFACE_DIRS}: "
            "a renamed folder empties the sweep and every check below "
            "passes while reading nothing")

    def test_the_sweep_sees_the_slots(self):
        slots = visible_slots()
        self.assertGreaterEqual(
            len(slots), FLOORS["visible_slots"],
            f"only {len(slots)} visible slots matched: SLOT stopped matching, "
            "and defect (b) is then green over an empty list")

    def test_the_sweep_can_tell_a_key_from_a_sentence(self):
        """without_markers() is what makes the sweep usable, so prove it.

        Blind it and the sweep reports every t() key as untranslated:
        that is the shape of a sweep whose filter has rotted, and it must
        be loud, not green.
        """
        slots = visible_slots()
        marked = [e for _, _, _, e in slots if MARKER.search(e)]
        self.assertGreaterEqual(len(marked), FLOORS["visible_slots"],
                                "no slot calls t() at all: the marker is gone")
        for expr in marked:
            stripped = without_markers(expr)
            self.assertNotIn("t(", stripped.replace(" ", ""),
                             f"a t() call survived stripping: {expr!r}")

    def test_the_job_tables_were_read(self):
        total = sum(len(t.get("en", {})) for t in map(job_table, JOB_MODULES))
        self.assertGreaterEqual(
            total, FLOORS["job_strings"],
            f"only {total} job strings read from {JOB_MODULES}: the reader "
            "stopped matching and the parity check below says nothing")

    def test_the_desktop_files_were_read(self):
        total = sum(len(desktop_entries(p)) for p in DESKTOP_FILES)
        self.assertGreaterEqual(
            total, FLOORS["desktop_keys"],
            f"only {total} desktop keys read: the reader stopped matching")

    def test_every_remedy_names_a_key_the_catalogue_has(self):
        en = language_block("en")
        for key in NTFS_REMEDIES:
            self.assertIn(key, en,
                          f"NTFS_REMEDIES names {key}, which strings.js has not: "
                          "a renamed key would otherwise be checked against nothing")


class VisibleAndNeverMarked(unittest.TestCase):
    """Defect (b): on screen, and in no catalogue. Nothing else reports it."""

    def test_no_visible_slot_shows_an_unmarked_string(self):
        bad = unmarked_literals()
        self.assertEqual(
            [], bad,
            "these go on the screen without passing through t(), so they can "
            "never be French:\n" + "\n".join(
                f"  {f}:{n}: {slot}: {lit!r}" for f, n, slot, lit in bad))

    def test_the_english_allowance_is_still_the_fallback_notice(self):
        """An allowance must stay tied to the reason it was granted.

        The notice is English because it only ever shows in a language
        Raye has no words for. If it stops being bound to rayeWords, the
        reason is gone and the allowance has to be re-argued.
        """
        src = (BRANDING / "pages/Language.qml").read_text(encoding="utf-8")
        for text in ENGLISH_ON_PURPOSE:
            self.assertIn(text, src,
                          f"{text!r} is allowed to stay English but is no longer "
                          "in Language.qml: drop it from ENGLISH_ON_PURPOSE")
        notice = re.search(r"visible:\s*!\w+\.rayeWords\s*\n\s*text:\s*\"([^\"]+)\"", src)
        self.assertTrue(
            notice,
            "the English notice is no longer shown under !rayeWords. That "
            "boolean was the whole reason it may stay English -- it shows only "
            "to a language Raye has no words for. Re-argue it or translate it.")
        self.assertIn(notice.group(1), ENGLISH_ON_PURPOSE)


class MarkedAndNotFrench(unittest.TestCase):
    """Defect (a), for the three catalogues test_branding.py cannot see."""

    def test_the_job_modules_name_themselves_in_both_languages(self):
        """The job name is what shows while the disk is being written."""
        for path in JOB_MODULES:
            table = job_table(path)
            self.assertIn("en", table, f"{path} has no en table")
            self.assertIn("fr", table, f"{path} has no fr table")
            missing = sorted(set(table["en"]) - set(table["fr"]))
            self.assertEqual([], missing,
                             f"{path} shows these with no French: {missing}")

    def test_every_desktop_key_a_person_reads_has_french(self):
        for path in DESKTOP_FILES:
            entries = desktop_entries(path)
            self.assertTrue(entries, f"{path} names none of {DESKTOP_KEYS}")
            for key, langs in sorted(entries.items()):
                self.assertIn("", langs, f"{path}: {key}[fr] without a plain {key}")
                self.assertIn("fr", langs,
                              f"{path}: {key}= has no {key}[fr]. gettext never "
                              "reads a .desktop; this file carries its own French")


class WindowsRefusals(unittest.TestCase):
    """🚨 The four phrases that stand between someone and a lost Windows."""

    def test_every_refusal_keeps_its_remedy_in_both_languages(self):
        for lang in ("en", "fr"):
            words = language_block(lang)
            for key, steps in sorted(NTFS_REMEDIES.items()):
                text = words[key]
                for step in steps[lang]:
                    self.assertIn(
                        step, text,
                        f"{lang}.{key} no longer tells the person to "
                        f"{step!r}. This is the text that stops a resize on a "
                        f"disk Windows has not finished with; a remedy missing "
                        f"a step sends them to force it.\n  got: {text!r}")

    def test_the_command_is_never_translated(self):
        """chkdsk /f is typed at a prompt, so it must survive word for word."""
        for lang in ("en", "fr"):
            self.assertIn("chkdsk /f", language_block(lang)["ntfsCheck"],
                          f"{lang}.ntfsCheck lost the literal command")


class FrenchAgreement(unittest.TestCase):
    """Raye is a system: masculine. The Store's statuses are not a model."""

    def test_raye_is_masculine_throughout(self):
        slips = []
        for key, text in sorted(language_block("fr").items()):
            for pattern, why in FEMININE_SLIPS:
                if re.search(pattern, text):
                    slips.append(f"  fr.{key}: {why}\n    {text!r}")
        self.assertEqual([], slips, "\n".join(slips))

    def test_the_masculine_form_is_the_one_in_use(self):
        """Prove the rule from the catalogue, not from this file's opinion."""
        fr = language_block("fr")
        masculine = [k for k, v in fr.items() if re.search(r"Raye[^.]{0,30}installé\b", v)]
        self.assertGreaterEqual(
            len(masculine), 2,
            "no French string says 'Raye ... installé' any more: the agreement "
            f"this class enforces is no longer evidenced. found: {masculine}")


if __name__ == "__main__":
    unittest.main()
