# SPDX-License-Identifier: GPL-3.0-or-later
"""Setup says root and sudo, never administrator.

One exception: ntfsCheck tells people what to do in Windows, and there
the command prompt really is "Run as administrator".
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
OLD = re.compile(r"administrat|\badmin\b", re.I)
COMMENT = re.compile(r"^\s*(#|//|\*|/\*)")
WINDOWS_WORDS = ("ntfsCheck:",)


def shown_lines():
    for folder in ("app", "etc", "qml", "usr"):
        for path in sorted((REPO / folder).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if OLD.search(line) and not COMMENT.match(line):
                    yield f"{path.relative_to(REPO)}:{number}", line


def test_no_administrator_in_setup():
    bad = [where for where, line in shown_lines() if not any(w in line for w in WINDOWS_WORDS)]
    assert bad == []


def test_windows_advice_keeps_the_windows_word():
    found = [line for _, line in shown_lines() if "ntfsCheck:" in line]
    assert len(found) == 2
