# SPDX-License-Identifier: GPL-3.0-or-later
"""The setup illustrations: every name the QML knows has its two
pictures, at the right size, with an alpha channel, and the generator and
the QML module agree on the list. They are flat drawings: no glow, no
sparkles, and violet only for the one thing that matters in each."""
import pathlib
import re
import struct
import zlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ART = ROOT / "art" / "illustrations.py"
PICTURES = ROOT / "assets" / "illustrations"
THEME = ROOT / "qml" / "org" / "raye" / "setup" / "Theme.qml"

BASE = 320          # 1x size of a picture, logical pixels


def generator_names():
    text = ART.read_text(encoding="utf-8")
    block = re.search(r"^NAMES = \(([^)]*)\)", text, re.M | re.S)
    assert block, "art/illustrations.py has no NAMES tuple"
    return re.findall(r'"([a-z]+)"', block.group(1))


def qml_names():
    text = THEME.read_text(encoding="utf-8")
    line = re.search(r"illustrationNames:\s*\[([^\]]*)\]", text)
    assert line, "Theme.qml has no illustrationNames list"
    return re.findall(r'"([a-z]+)"', line.group(1))


def png_header(path):
    """(width, height, colour type) from the IHDR chunk."""
    data = path.read_bytes()[:33]
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    assert data[12:16] == b"IHDR"
    width, height, _depth, colour = struct.unpack(">IIBB", data[16:26])
    return width, height, colour


def test_sixteen_names_and_both_lists_agree():
    names = generator_names()
    assert len(names) == 16
    assert len(set(names)) == 16
    assert names == qml_names()


def test_spec_names_are_all_there():
    wanted = ("language keyboard choose network disk account summary install "
              "done error key privacy look usb").split()
    assert set(wanted) <= set(generator_names())


@pytest.mark.parametrize("name", generator_names())
@pytest.mark.parametrize("suffix,size", [("", BASE), ("@2x", BASE * 2)])
def test_picture(name, suffix, size):
    path = PICTURES / f"{name}{suffix}.png"
    assert path.is_file(), f"missing {path.relative_to(ROOT)}: run python3 art/illustrations.py"
    width, height, colour = png_header(path)
    assert (width, height) == (size, size)
    assert colour == 6, f"{path.name} has no alpha channel"


def test_nothing_extra_in_the_folder():
    expected = {f"{n}{s}.png" for n in generator_names() for s in ("", "@2x")}
    found = {p.name for p in PICTURES.iterdir()}
    assert found == expected


def test_the_drawing_code_has_no_glow_or_sparkles():
    text = ART.read_text(encoding="utf-8")
    for word in ("GaussianBlur", "sparkle", "glow", "halo"):
        assert word not in text, f"art/illustrations.py still draws a {word}"


def rgba_pixels(path):
    """Every pixel of an 8-bit RGBA PNG without filters we cannot undo."""
    data = path.read_bytes()
    pos, idat, width, height = 8, b"", 0, 0
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, colour = struct.unpack(">IIBB", body[:10])
            assert (depth, colour) == (8, 6)
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * 4
    rows, prev = [], bytearray(stride)
    for y in range(height):
        kind = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for x in range(stride):
            a = line[x - 4] if x >= 4 else 0
            b = prev[x]
            c = prev[x - 4] if x >= 4 else 0
            if kind == 1:
                line[x] = (line[x] + a) & 255
            elif kind == 2:
                line[x] = (line[x] + b) & 255
            elif kind == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    out = []
    for row in rows:
        for x in range(0, stride, 4):
            out.append(tuple(row[x:x + 4]))
    return out


@pytest.mark.parametrize("name", generator_names())
def test_violet_is_only_an_accent(name):
    # Drawn pixels, not the faint fills or antialiased edges: a strong violet
    # on more than a quarter of them is the old neon look.
    pixels = [p for p in rgba_pixels(PICTURES / f"{name}.png") if p[3] >= 200]
    assert pixels, f"{name}.png draws nothing"
    violet = [p for p in pixels if p[2] - p[1] > 90 and p[0] - p[1] > 30]
    assert len(violet) / len(pixels) < 0.25, f"{name}.png is {len(violet) / len(pixels):.0%} violet"


@pytest.mark.parametrize("name", generator_names())
def test_no_haze_around_the_lines(name):
    # A glow is a wide band of half-transparent pixels; flat shapes only
    # have them along their edges.
    pixels = rgba_pixels(PICTURES / f"{name}.png")
    hazy = sum(1 for p in pixels if 0 < p[3] < 120)
    drawn = sum(1 for p in pixels if p[3] > 0)
    assert hazy / drawn < 0.35, f"{name}.png is {hazy / drawn:.0%} haze"
