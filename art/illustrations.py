#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The pictures of the Raye setup, one per page: flat line drawings on the
# card, light grey lines, dark grey shapes, and violet for the one thing
# each picture is about. Run it after a change and commit what it writes:
#
#   python3 art/illustrations.py            # writes assets/illustrations/
#   python3 art/illustrations.py out/       # or somewhere else
#
# Each picture comes out twice:
#   <name>.png       320 x 320 (1x)
#   <name>@2x.png    640 x 640 for HiDPI screens
#
# Drawing rules:
#   - one stroke weight for outlines, a thinner one for details
#   - outlines light grey, details mid grey, shapes dark grey
#   - violet on one or two parts only, never on the outlines
#   - no text, so a picture fits any language
#   - keep a 28 px margin

import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

NAMES = (
    "language", "keyboard", "choose", "network", "disk",
    "account", "summary", "install", "done", "error",
    "key", "privacy", "look", "usb", "apps",
)

G = 320                     # design grid
S = 4                       # drawn at 4x, scaled down: free antialiasing
LINE = 3.2                  # outline stroke, grid pixels
THIN = 2.2                  # detail stroke

OUTLINE = (0xd4, 0xd0, 0xdc)        # light grey with a little violet in it
DETAIL = (0x8c, 0x87, 0x98)
SHAPE = (0x2c, 0x2a, 0x33, 255)     # a shape's body, over the card
SHAPE_DEEP = (0x22, 0x20, 0x28, 255)
ACCENT = (0x7b, 0x3c, 0xff, 255)    # the Raye accent
ACCENT_LINE = (0xa6, 0x82, 0xff)    # the accent where it is a line, lifted to read on grey
WHITE = (0xf6, 0xf4, 0xfa, 255)
AMBER = (0xe0, 0xa4, 0x58, 255)
INK = (0x12, 0x10, 0x18, 255)


def px(v):
    return round(v * S)


def erode(mask, width):
    """The shape shrunk by one stroke (two half-width passes)."""
    size = int(width * S) | 1
    return mask.filter(ImageFilter.MinFilter(size)).filter(ImageFilter.MinFilter(size))


def outline(mask, width):
    """The edge of a filled shape, one stroke wide, drawn inside it."""
    return ImageChops.subtract(mask, erode(mask, width))


class Sketch:
    """Four layers on the 4x canvas: flat shapes, grey details, outlines,
    and a top layer for violet lines and small white marks."""

    def __init__(self):
        size = (G * S, G * S)
        self.fill = Image.new("RGBA", size, (0, 0, 0, 0))
        self.detail = Image.new("L", size, 0)
        self.main = Image.new("L", size, 0)
        self.accent = Image.new("L", size, 0)
        self.top = Image.new("RGBA", size, (0, 0, 0, 0))

    def _draw(self, layer):
        return ImageDraw.Draw({"main": self.main, "detail": self.detail, "accent": self.accent,
                               "fill": self.fill, "top": self.top}[layer])

    @staticmethod
    def _ink(layer, colour):
        return 255 if layer in ("main", "detail", "accent") else colour

    def stroke(self, points, width=LINE, layer="main", colour=WHITE, closed=False):
        """A polyline with round joints and round ends."""
        pts = [(px(x), px(y)) for x, y in points]
        if closed:
            pts.append(pts[0])
        d = self._draw(layer)
        ink = self._ink(layer, colour)
        d.line(pts, fill=ink, width=px(width), joint="curve")
        r = width * S / 2
        for x, y in (pts if not closed else pts[:1]):
            d.ellipse((x - r, y - r, x + r, y + r), fill=ink)

    def rrect(self, box, radius, width=LINE, layer="main", fill=None, colour=WHITE):
        x0, y0, x1, y1 = box
        d = self._draw(layer)
        if fill is not None:
            ImageDraw.Draw(self.fill).rounded_rectangle(
                (px(x0), px(y0), px(x1), px(y1)), radius=px(radius), fill=fill)
        if width:
            d.rounded_rectangle((px(x0), px(y0), px(x1), px(y1)), radius=px(radius),
                                outline=self._ink(layer, colour), width=px(width))

    def circle(self, cx, cy, r, width=LINE, layer="main", fill=None, colour=WHITE):
        box = (px(cx - r), px(cy - r), px(cx + r), px(cy + r))
        if fill is not None:
            ImageDraw.Draw(self.fill).ellipse(box, fill=fill)
        if width:
            self._draw(layer).ellipse(box, outline=self._ink(layer, colour), width=px(width))

    def dot(self, cx, cy, r, layer="top", colour=WHITE):
        box = (px(cx - r), px(cy - r), px(cx + r), px(cy + r))
        self._draw(layer).ellipse(box, fill=self._ink(layer, colour))

    def arc(self, cx, cy, r, start, end, width=LINE, layer="main", colour=WHITE):
        """Angles in degrees, clockwise from 3 o'clock, like Pillow."""
        box = (px(cx - r), px(cy - r), px(cx + r), px(cy + r))
        d = self._draw(layer)
        ink = self._ink(layer, colour)
        d.arc(box, start, end, fill=ink, width=px(width))
        # round ends
        rr = width * S / 2
        mid = (r - width / 2) * S
        for a in (start, end):
            t = math.radians(a)
            x, y = px(cx) + mid * math.cos(t), px(cy) + mid * math.sin(t)
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=ink)

    def crescent(self, cx, cy, r, cx2, cy2, r2, width=LINE, layer="main", fill=None):
        """A moon: the disc (cx, cy, r) less the disc (cx2, cy2, r2)."""
        size = (G * S, G * S)
        disc = Image.new("L", size, 0)
        ImageDraw.Draw(disc).ellipse((px(cx - r), px(cy - r), px(cx + r), px(cy + r)), fill=255)
        bite = Image.new("L", size, 0)
        ImageDraw.Draw(bite).ellipse((px(cx2 - r2), px(cy2 - r2), px(cx2 + r2), px(cy2 + r2)), fill=255)
        moon = ImageChops.subtract(disc, bite)
        if fill is not None:
            self.fill.paste(Image.new("RGBA", size, fill), mask=moon)
        {"main": self.main, "accent": self.accent, "detail": self.detail}[layer].paste(255, mask=outline(moon, width))

    def erase(self, cx, cy, r):
        """Clear the lines under a badge, so it sits in front of them."""
        box = (px(cx - r), px(cy - r), px(cx + r), px(cy + r))
        for layer in (self.main, self.detail, self.accent):
            ImageDraw.Draw(layer).ellipse(box, fill=0)

    def polygon_fill(self, points, colour):
        ImageDraw.Draw(self.fill).polygon([(px(x), px(y)) for x, y in points], fill=colour)

    def eye(self, cx, cy, a, b, line=LINE):
        """The Raye eye, flat: an almond outline, a violet iris, a dark
        pupil and one small white highlight."""
        r = (a * a + b * b) / (2 * b)
        size = (G * S, G * S)
        m1 = Image.new("L", size, 0)
        m2 = Image.new("L", size, 0)
        ImageDraw.Draw(m1).ellipse((px(cx - r), px(cy - b + r - r), px(cx + r), px(cy - b + r + r)), fill=255)
        ImageDraw.Draw(m2).ellipse((px(cx - r), px(cy + b - r - r), px(cx + r), px(cy + b - r + r)), fill=255)
        outer = ImageChops.multiply(m1, m2)
        inner = erode(outer, line)
        self.main.paste(255, mask=ImageChops.subtract(outer, inner))
        inside = Image.new("RGBA", size, (0, 0, 0, 0))
        di = ImageDraw.Draw(inside)
        di.rectangle((0, 0) + size, fill=INK)
        ir = b * 0.74
        di.ellipse((px(cx - ir), px(cy - ir), px(cx + ir), px(cy + ir)), fill=ACCENT)
        pr = b * 0.32
        di.ellipse((px(cx - pr), px(cy - pr), px(cx + pr), px(cy + pr)), fill=INK)
        hr = b * 0.11
        hx, hy = cx - b * 0.18, cy - b * 0.18
        di.ellipse((px(hx - hr), px(hy - hr), px(hx + hr), px(hy + hr)), fill=WHITE)
        inside.putalpha(ImageChops.multiply(inside.getchannel("A"), inner))
        self.top.alpha_composite(inside)

    # --- output ---------------------------------------------------------

    def lines(self):
        size = (G * S, G * S)
        out = self.fill.copy()
        for mask, colour in ((self.detail, DETAIL), (self.main, OUTLINE), (self.accent, ACCENT_LINE)):
            layer = Image.new("RGBA", size, colour + (0,))
            layer.putalpha(mask)
            out.alpha_composite(layer)
        out.alpha_composite(self.top)
        return out


# --- the pictures ---------------------------------------------------------

def language(k):
    cx, cy, r = 124, 178, 76
    k.circle(cx, cy, r, fill=SHAPE)
    k.stroke([(cx, cy - r), (cx, cy + r)], width=THIN, layer="detail")
    w = r * 0.45
    k._draw("detail").ellipse((px(cx - w), px(cy - r), px(cx + w), px(cy + r)),
                              outline=255, width=px(THIN))
    for dy in (-r * 0.45, r * 0.45):
        half = (r * r - dy * dy) ** 0.5
        k.stroke([(cx - half, cy + dy), (cx + half, cy + dy)], width=THIN, layer="detail")
    k.stroke([(cx - r, cy), (cx + r, cy)], width=THIN, layer="detail")
    k.circle(cx, cy, r, width=LINE)
    # a speech bubble in front, in the accent
    k.rrect((180, 62, 280, 120), 14, width=0, fill=ACCENT)
    k.polygon_fill([(198, 118), (192, 138), (220, 118)], ACCENT)
    for i in range(3):
        k.dot(208 + i * 22, 91, 4.6)
    k.rrect((214, 146, 282, 186), 12, width=THIN, layer="detail", fill=SHAPE_DEEP)
    k.stroke([(230, 166), (266, 166)], width=THIN, layer="detail")


def keyboard(k):
    x0, y0, x1, y1 = 44, 118, 276, 232
    k.rrect((x0, y0, x1, y1), 14, fill=SHAPE)
    rows = [(132, 10), (158, 10), (184, 9)]
    lit = (1, 4)
    for ri, (y, count) in enumerate(rows):
        off = 8 * ri
        key_w = (x1 - x0 - 28 - off - (count - 1) * 5) / count
        for i in range(count):
            kx = x0 + 14 + off / 2 + i * (key_w + 5)
            box = (kx, y, kx + key_w, y + 20)
            if (ri, i) == lit:
                k.rrect(box, 4, width=0, fill=ACCENT)
            else:
                k.rrect(box, 4, width=THIN, layer="detail")
    k.rrect((96, 210, 224, 222), 4, width=THIN, layer="detail")
    # the test field above, with its cursor
    k.rrect((92, 66, 228, 96), 8, width=THIN, layer="detail", fill=SHAPE_DEEP)
    k.stroke([(112, 74), (112, 88)], width=THIN, layer="accent")


def choose(k):
    # behind: "try" (a window with a play mark), in front: "install" with the eye
    k.rrect((150, 70, 282, 176), 12, width=THIN, layer="detail", fill=SHAPE_DEEP)
    k.stroke([(204, 106), (204, 140), (232, 123)], width=THIN, layer="detail", closed=True)
    k.rrect((40, 128, 190, 248), 14, fill=SHAPE)
    k.eye(115, 184, 46, 22)
    k.stroke([(80, 226), (150, 226)], width=THIN, layer="detail")


def network(k):
    cx, cy = 150, 206
    for i, r in enumerate((40, 74, 108)):
        k.arc(cx, cy, r, 225, 315, width=LINE if i < 2 else THIN,
              layer="main" if i < 2 else "detail")
    k.dot(cx, cy, 10, layer="fill", colour=ACCENT)
    # a small clock: the time zone comes with the network
    k.circle(244, 90, 28, width=THIN, layer="detail", fill=SHAPE)
    k.stroke([(244, 74), (244, 90), (256, 98)], width=THIN, layer="detail")


def disk(k):
    x0, x1 = 84, 236
    for i, y in enumerate((88, 140, 192)):
        k.rrect((x0, y, x1, y + 44), 10, width=LINE if i == 1 else THIN,
                layer="main" if i == 1 else "detail", fill=SHAPE)
        k.stroke([(x0 + 20, y + 22), (x0 + 70, y + 22)], width=THIN, layer="detail")
        if i == 1:
            k.dot(x1 - 22, y + 22, 5.5, layer="fill", colour=ACCENT)
        else:
            k.dot(x1 - 22, y + 22, 3.5, layer="detail")


def account(k):
    cx, cy = 160, 160
    k.circle(cx, cy, 92, fill=SHAPE)
    k.circle(cx, cy, 92, width=THIN, layer="detail")
    k.circle(cx, cy - 24, 28, width=0, fill=ACCENT)
    k.arc(cx, cy + 68, 54, 205, 335)


def summary(k):
    k.rrect((76, 54, 244, 266), 14, fill=SHAPE)
    k.rrect((126, 44, 194, 66), 8, width=THIN, layer="detail", fill=SHAPE_DEEP)
    for i in range(4):
        y = 98 + i * 40
        if i < 3:
            k.circle(106, y, 11, width=0, fill=ACCENT)
            k.stroke([(101, y), (105, y + 5), (112, y - 5)], width=THIN, layer="top")
        else:
            k.circle(106, y, 11, width=THIN, layer="detail")
        k.stroke([(130, y), (214 - (i % 2) * 28, y)], width=THIN, layer="detail")


def install(k):
    # a screen with the eye, the bar filling under it
    k.rrect((48, 66, 272, 202), 12, fill=SHAPE)
    k.eye(160, 124, 54, 26)
    k.rrect((96, 174, 224, 182), 4, width=0, fill=SHAPE_DEEP)
    k.rrect((96, 174, 186, 182), 4, width=0, fill=ACCENT)
    k.stroke([(132, 202), (126, 234), (194, 234), (188, 202)], width=THIN, layer="detail")
    k.stroke([(106, 244), (214, 244)], width=LINE)


def done(k):
    cx, cy = 160, 160
    k.circle(cx, cy, 92, fill=SHAPE)
    k.circle(cx, cy, 92, width=THIN, layer="detail")
    k.stroke([(122, 162), (148, 188), (200, 134)], width=LINE + 2.4, layer="accent")


def error(k):
    # gentle: a screen with a wavy line and a small warning mark
    k.rrect((52, 70, 268, 206), 12, fill=SHAPE)
    pts = []
    for i in range(41):
        x = 84 + i * 3.8
        pts.append((x, 138 + 14 * math.sin(i / 40 * math.pi * 3)))
    k.stroke(pts, width=THIN, layer="detail")
    k.stroke([(136, 206), (130, 236), (190, 236), (184, 206)], width=THIN, layer="detail")
    k.erase(236, 210, 34 + LINE * 1.5)
    k.circle(236, 210, 32, width=0, fill=AMBER)
    k.stroke([(236, 194), (236, 212)], width=LINE + 0.8, layer="fill", colour=INK)
    k.dot(236, 225, 3.6, layer="fill", colour=INK)


def key(k):
    # a key, and the recovery digits as dashes under it
    k.circle(108, 140, 44, fill=SHAPE)
    k.circle(108, 140, 15, width=THIN, layer="detail")
    k.stroke([(148, 158), (248, 200)])
    k.stroke([(220, 188), (210, 210)])
    k.stroke([(240, 196), (232, 216)])
    for i in range(4):
        k.stroke([(60 + i * 46, 252), (88 + i * 46, 252)], width=THIN,
                 layer="accent" if i == 0 else "detail")


def privacy(k):
    cx = 160
    pts = [(cx, 50), (244, 82), (238, 170), (cx, 260), (82, 170), (76, 82)]
    k.polygon_fill(pts, SHAPE)
    k.stroke(pts, closed=True)
    # a closed eye: Raye looks away
    k.arc(cx, 126, 48, 25, 155, layer="accent")
    for dx in (-30, 0, 30):
        k.stroke([(cx + dx * 1.15, 172 + abs(dx) * -0.25), (cx + dx * 1.4, 186 + abs(dx) * -0.2)],
                 width=THIN, layer="detail")


def look(k):
    # two windows, night in front, day behind; a moon and a sun
    k.rrect((136, 58, 280, 170), 12, width=THIN, layer="detail", fill=(0x46, 0x43, 0x4f, 255))
    k.circle(240, 102, 15, width=0, fill=(0xe8, 0xe4, 0xee, 255))
    k.rrect((40, 120, 206, 250), 12, fill=SHAPE_DEEP)
    k.crescent(118, 186, 28, 132, 174, 24, width=THIN, layer="accent", fill=ACCENT)
    k.stroke([(62, 142), (110, 142)], width=THIN, layer="detail")


def usb(k):
    # the stick, and an arrow: take it out
    k.rrect((112, 128, 208, 254), 14, fill=SHAPE)
    k.rrect((128, 78, 192, 128), 6, width=THIN, layer="detail", fill=SHAPE_DEEP)
    k.rrect((142, 94, 154, 106), 2, width=THIN, layer="detail")
    k.rrect((166, 94, 178, 106), 2, width=THIN, layer="detail")
    k.dot(160, 222, 5, layer="fill", colour=ACCENT)
    k.stroke([(252, 196), (252, 94)], width=LINE, layer="accent")
    k.stroke([(234, 112), (252, 94), (270, 112)], width=LINE, layer="accent")


def apps(k):
    size, gap = 54, 14
    x0 = 160 - (3 * size + 2 * gap) / 2
    y0 = x0 + 4
    for r in range(3):
        for c in range(3):
            x, y = x0 + c * (size + gap), y0 + r * (size + gap)
            if (r, c) == (1, 1):
                k.rrect((x, y, x + size, y + size), 12, fill=SHAPE)
                k.eye(x + size / 2, y + size / 2, 20, 10, line=THIN)
            else:
                k.rrect((x, y, x + size, y + size), 12, width=THIN, layer="detail",
                        fill=SHAPE if (r + c) % 2 == 0 else SHAPE_DEEP)


def write(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        sk = Sketch()
        globals()[name](sk)
        big = sk.lines()
        big.resize((G * 2, G * 2), Image.LANCZOS).save(out_dir / f"{name}@2x.png", optimize=True)
        big.resize((G, G), Image.LANCZOS).save(out_dir / f"{name}.png", optimize=True)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent.parent
    write(Path(sys.argv[1]) if len(sys.argv) > 1 else here / "assets" / "illustrations")
