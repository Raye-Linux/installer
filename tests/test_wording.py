# SPDX-License-Identifier: GPL-3.0-or-later
"""What Setup says, read the way a person reads it: American English in the
English table, and none of the stiff lines people pointed at."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
STRINGS = ROOT / "etc/calamares/branding/raye/strings.js"
INTERFACE = [p for d in ("etc/calamares/branding/raye", "qml/org/raye/setup", "app/firstrun")
             for p in (ROOT / d).rglob("*") if p.suffix in (".qml", ".js")]


def table(lang):
    # the words object is plain JSON once its keys are quoted
    text = STRINGS.read_text(encoding="utf-8")
    block = text[text.index("var words = ") + len("var words = "):text.index("\n}\n") + 2]
    block = re.sub(r"^(\s+)([A-Za-z]+):", r'\1"\2":', block, flags=re.M)
    return json.loads(block)[lang]


def test_lines_people_found_stiff_are_gone():
    english = " ".join(table("en").values())
    for line in ("Look at the disks again", "Encrypt the Raye system"):
        assert line not in english


def test_english_is_american():
    english = " ".join(table("en").values()).lower()
    for word in ("licence", "colour", "cancelled", "recognise", "favourite", "centre"):
        assert word not in english, word


def test_no_sparkle_characters_on_screen():
    for path in INTERFACE:
        text = path.read_text(encoding="utf-8")
        for mark in ("✦", "✧", "✨", "★"):
            assert mark not in text, f"{path.relative_to(ROOT)} draws {mark}"


def test_every_field_label_exists_in_both_languages():
    en, fr = table("en"), table("fr")
    for key in ("diskPassLabel", "diskPassAgainLabel", "fullName", "password", "confirmPassword", "hint"):
        assert en.get(key) and fr.get(key), key
        assert en[key] != fr[key], key
