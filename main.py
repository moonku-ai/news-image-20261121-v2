"""news-image-20261121 v2 — "The Day the World Judged".

A pure-Python-stdlib program that draws one 1024x1024 poster summing up
Saturday 21 November 2026's world news and writes it to /output/entry.png.

Everything is drawn in code: a hand-written PNG encoder (zlib), a 5x7
bitmap font, and a small shape rasterizer. No generated image, no network,
no third-party dependency, fully deterministic (two runs = identical bytes).

News (verified 21 Nov 2026, browser.news + corroborating front pages):
- ICJ finds Myanmar committed genocide against the Rohingya — the first
  time any international court has found a state guilty of genocide.
  Reported on the 21 Nov front pages.
- AI market meltdown: Nasdaq -5.28%, S&P -3.7%, Dow -950, Nvidia -14%,
  $4tn wiped out in a week (Friday 20 Nov close, reported Sat 21 Nov).
- Kyiv under fire overnight 19-20 Nov: 400+ drones, 110+ missiles;
  bridges hit, power cut; missiles land in Poland.
- Shenzhen: Trump, Xi and Putin sign a joint peace declaration (Thu).
- COP31 in Antalya runs past deadline, deadlocked over fossil fuels.
"""
import hashlib
import math
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# Palette (ui-ux-pro-max: Hero-Centric + Swiss/Minimalism; breaking red +
# link blue; gold for the justice hero).
NAVY = (11, 21, 38)
PANEL = (19, 35, 60)
CREAM = (245, 239, 224)
GOLD = (232, 169, 61)
RED = (220, 38, 38)
RED_PANEL = (143, 29, 29)
STEEL = (30, 58, 95)
TEAL = (15, 46, 42)
MUTED = (159, 176, 195)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# ---------------------------------------------------------------- font ----
# 5x7 bitmap font. Each glyph is 7 rows of 5 bits ('1' = ink).
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "\u00b7": ("00000", "00000", "00000", "01100", "01100", "00000", "00000"),
}

ADVANCE = 6  # glyph columns (5) + 1 gap, in font units


def text_width(text, scale):
    """Pixel width of text at the given scale."""
    return len(text) * ADVANCE * scale


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines, each fitting max_width."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_width(trial, scale) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                # Hard-split one over-long word.
                while text_width(word, scale) > max_width:
                    cut = max_width // (ADVANCE * scale)
                    lines.append(word[:cut])
                    word = word[cut:]
                cur = word
        if cur:
            lines.append(cur)
    return lines


# -------------------------------------------------------------- canvas ----
class Canvas:
    """An RGB raster canvas with a tiny shape/text rasterizer."""

    def __init__(self, width, height, bg=BLACK):
        self.w = width
        self.h = height
        self.buf = bytearray(bg * (width * height))

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def pixel(self, x, y):
        o = self._off(x, y)
        return (self.buf[o], self.buf[o + 1], self.buf[o + 2])

    def set_pixel(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.buf[o:o + 3] = bytes(color)

    def fill_rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            o = self._off(x0, yy)
            self.buf[o:o + len(row)] = row

    def hline(self, x, y, w, color, thick=1):
        self.fill_rect(x, y - thick // 2, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.fill_rect(x - thick // 2, y, thick, h, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        """Bresenham line with round-ish thick stamps."""
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        r = max(1, thick // 2)
        while True:
            self.fill_circle(x0, y0, r, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def fill_circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else -1
            if dx >= 0:
                self.fill_rect(cx - dx, yy, 2 * dx + 1, 1, color)

    def ring(self, cx, cy, r, color, thick=1):
        steps = max(24, int(6.28 * r))
        for i in range(steps):
            a = 6.283185307179586 * i / steps
            x = int(cx + r * _cos(a))
            y = int(cy + r * _sin(a))
            self.fill_circle(x, y, max(1, thick // 2), color)

    def fill_triangle(self, p0, p1, p2, color):
        xs = sorted([p0, p1, p2], key=lambda p: p[1])
        (x0, y0), (x1, y1), (x2, y2) = xs
        for y in range(y0, y2 + 1):
            if y < y1:
                xa = _lerp(x0, x1, y, y0, y1)
                xb = _lerp(x0, x2, y, y0, y2)
            else:
                xa = _lerp(x1, x2, y, y1, y2)
                xb = _lerp(x0, x2, y, y0, y2)
            lo, hi = (xa, xb) if xa <= xb else (xb, xa)
            self.fill_rect(int(lo), y, int(hi) - int(lo) + 1, 1, color)

    def draw_text(self, x, y, text, scale, color):
        cx = x
        for ch in text:
            glyph = FONT.get(ch)
            if glyph is None:
                raise ValueError(f"no glyph for {ch!r}")
            for row_i, row in enumerate(glyph):
                for col_i, bit in enumerate(row):
                    if bit == "1":
                        self.fill_rect(
                            cx + col_i * scale, y + row_i * scale,
                            scale, scale, color,
                        )
            cx += ADVANCE * scale
        return cx

    def text_block(self, x, y, text, scale, color, max_width, leading=None):
        """Wrapped text block; returns the y just below the last line."""
        if leading is None:
            leading = 7 * scale + 6
        yy = y
        for line in wrap_text(text, scale, max_width):
            self.draw_text(x, yy, line, scale, color)
            yy += leading
        return yy


def _cos(a):
    return math.cos(a)


def _sin(a):
    return math.sin(a)


def _lerp(x0, x1, y, y0, y1):
    if y1 == y0:
        return x0
    return x0 + (x1 - x0) * (y - y0) / (y1 - y0)


# ----------------------------------------------------------- PNG encode ---
def _chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    return out + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)


def encode_png(width, height, rgb):
    """Encode raw RGB bytes as a PNG (filter 0 per row, zlib level 9)."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


# ------------------------------------------------------------ pictograms --
def draw_scales(c, cx, top, h, color, thick=5):
    """Scales of justice: post, crossbar, two hanging pans."""
    mid = top + h // 2
    c.vline(cx, top + 8, h - 16, color, thick)
    c.fill_circle(cx, top, 7, color)
    c.hline(cx - 62, top + 16, 124, color, thick)
    c.fill_circle(cx - 62, top + 16, 5, color)
    c.fill_circle(cx + 62, top + 16, 5, color)
    for sx in (cx - 62, cx + 62):
        c.line(sx, top + 16, sx - 26, mid + 6, color, 3)
        c.line(sx, top + 16, sx + 26, mid + 6, color, 3)
        c.fill_triangle((sx - 30, mid + 6), (sx + 30, mid + 6),
                        (sx, mid + 42), color)
    c.hline(cx - 46, top + h - 6, 92, color, thick)


def draw_chart(c, x, y, w, h, color, thick=6):
    """Plunging market chart with an arrowhead at the end."""
    pts = [
        (x, y + int(h * 0.12)),
        (x + int(w * 0.22), y + int(h * 0.22)),
        (x + int(w * 0.38), y + int(h * 0.18)),
        (x + int(w * 0.55), y + int(h * 0.52)),
        (x + int(w * 0.72), y + int(h * 0.62)),
        (x + int(w * 0.88), y + int(h * 0.92)),
        (x + w, y + h),
    ]
    for a, b in zip(pts, pts[1:]):
        c.line(a[0], a[1], b[0], b[1], color, thick)
    ex, ey = pts[-1]
    c.fill_triangle((ex, ey), (ex - 16, ey - 4), (ex - 4, ey - 18), color)


def draw_burst(c, cx, cy, r, color, thick=4):
    """Starburst: radiating spikes around a core."""
    import math

    for i in range(12):
        a = 2 * math.pi * i / 12
        x1 = int(cx + (r * 0.55) * math.cos(a))
        y1 = int(cy + (r * 0.55) * math.sin(a))
        x2 = int(cx + r * math.cos(a))
        y2 = int(cy + r * math.sin(a))
        c.line(x1, y1, x2, y2, color, thick)
    c.fill_circle(cx, cy, int(r * 0.34), color)
    c.ring(cx, cy, int(r * 0.72), color, 3)


def draw_three_circles(c, cx, cy, r, colors):
    """Three overlapping rings (three leaders, one declaration)."""
    offs = [(-r // 2, -r // 4), (r // 2, -r // 4), (0, r // 2)]
    for (dx, dy), col in zip(offs, colors):
        c.ring(cx + dx, cy + dy, r // 2, col, 4)


def draw_globe(c, cx, cy, r, color):
    """Wireframe globe: outline, meridian ellipse, parallels."""
    import math

    c.ring(cx, cy, r, color, 4)
    for fy in (-0.5, 0.0, 0.5):
        yy = int(cy + fy * r)
        half = int((r * r - (yy - cy) ** 2) ** 0.5)
        c.hline(cx - half, yy, 2 * half, color, 3)
    # vertical meridian: an ellipse drawn point by point
    for i in range(65):
        t = i / 64.0
        ang = 2 * math.pi * t
        xx = int(cx + (r * 0.45) * math.cos(ang))
        yy = int(cy + r * math.sin(ang))
        c.fill_circle(xx, yy, 2, color)


# ---------------------------------------------------------------- layout ---
def layout_plan():
    """The poster's content plan (also the test's source of truth)."""
    return {
        "masthead": "SATURDAY 21 NOVEMBER 2026",
        "stories": [
            {
                "kicker": "THE HAGUE \u00b7 THE WORLD COURT",
                "headline": "MYANMAR GUILTY OF GENOCIDE",
                "dateline": "ROHINGYA CASE - REPORTED SAT 21 NOV",
                "body": "FIRST TIME ANY INTERNATIONAL COURT HAS FOUND A "
                        "STATE GUILTY OF GENOCIDE.",
            },
            {
                "kicker": "WALL STREET \u00b7 FRIDAY'S CLOSE",
                "headline": "AI BUBBLE BURSTS",
                "dateline": "FRI 20 NOV CLOSE",
                "body": "S&P -3.7% \u00b7 DOW -950 \u00b7 NVIDIA -14% \u00b7 "
                        "$4TN WIPED OUT IN A WEEK",
            },
            {
                "kicker": "UKRAINE",
                "headline": "KYIV UNDER FIRE",
                "dateline": "OVERNIGHT 19-20 NOV",
                "body": "BRIDGES HIT, POWER CUT - MISSILES LAND IN "
                        "POLAND",
            },
            {
                "kicker": "SHENZHEN",
                "headline": "PEACE DECLARATION",
                "dateline": "THURSDAY 19 NOV",
                "body": "TRUMP, XI AND PUTIN SIGN A JOINT DECLARATION - "
                        "SILENT ON UKRAINE",
            },
            {
                "kicker": "ANTALYA \u00b7 COP31",
                "headline": "CLIMATE DEADLOCK",
                "dateline": "OVERTIME SAT 21 NOV",
                "body": "TALKS RUN PAST DEADLINE AS FOSSIL FUELS ARE CUT "
                        "FROM THE DRAFT",
            },
        ],
        "ticker": "FBI CRIME DATABASE HACKED \u00b7 PERU SHAKEN BY 6.9 "
                  "QUAKE \u00b7 ANTHROPIC'S $81.3BN DEBUT, BIGGEST IPO EVER "
                  "\u00b7 GEN Z PROTESTS IN 25 EUROPEAN STATES \u00b7 UK-EU "
                  "SIGN POST-BREXIT DEALS",
        "footer": "SOURCES: REUTERS \u00b7 AP \u00b7 WSJ \u00b7 NYT \u00b7 UN "
                  "NEWS \u00b7 ICJ \u00b7 DRAWN IN CODE",
    }


def render_poster():
    plan = layout_plan()
    c = Canvas(W, H, NAVY)

    # ---- masthead ----
    date_w = text_width(plan["masthead"], 4)
    c.draw_text((W - date_w) // 2, 26, plan["masthead"], 4, CREAM)
    tag = "THE WORLD IN ONE IMAGE"
    tag_w = text_width(tag, 2)
    c.draw_text((W - tag_w) // 2, 62, tag, 2, GOLD)
    c.hline(28, 96, W - 56, RED, 4)

    # ---- hero: ICJ verdict ----
    hero = plan["stories"][0]
    c.fill_rect(28, 112, W - 56, 328, PANEL)
    c.fill_rect(28, 112, 10, 328, GOLD)
    draw_scales(c, 150, 190, 190, GOLD)
    c.draw_text(286, 140, hero["kicker"], 3, GOLD)
    c.draw_text(286, 176, "MYANMAR GUILTY", 8, CREAM)
    c.draw_text(286, 248, "OF GENOCIDE", 8, CREAM)
    c.text_block(286, 336, hero["body"], 3, MUTED, 710)
    c.draw_text(286, 402, hero["dateline"], 2, GOLD)

    # ---- middle row: markets + Kyiv ----
    mkt, kyiv = plan["stories"][1], plan["stories"][2]
    # markets (left, red)
    c.fill_rect(28, 456, 472, 224, RED_PANEL)
    c.draw_text(48, 476, mkt["kicker"], 2, CREAM)
    c.draw_text(48, 504, mkt["headline"], 4, CREAM)
    c.draw_text(48, 540, "-5.28%", 9, WHITE)
    c.draw_text(48, 612, "NASDAQ", 3, GOLD)
    c.text_block(48, 634, mkt["body"], 2, CREAM, 432)
    draw_chart(c, 412, 466, 80, 72, CREAM, 5)
    # Kyiv (right, steel blue)
    c.fill_rect(524, 456, 472, 224, STEEL)
    c.draw_text(544, 476, kyiv["kicker"], 2, CREAM)
    c.draw_text(544, 504, kyiv["headline"], 4, CREAM)
    c.draw_text(544, 540, "400+ DRONES", 5, WHITE)
    c.draw_text(544, 590, "110 MISSILES", 5, WHITE)
    c.text_block(544, 640, kyiv["body"], 2, CREAM, 432)
    draw_burst(c, 940, 545, 30, GOLD)

    # ---- bottom row: Shenzhen + COP31 ----
    shz, cop = plan["stories"][3], plan["stories"][4]
    # Shenzhen (left)
    c.fill_rect(28, 696, 472, 200, PANEL)
    c.draw_text(48, 716, shz["kicker"], 2, GOLD)
    c.draw_text(48, 744, shz["headline"], 4, CREAM)
    c.text_block(48, 792, shz["body"], 2, MUTED, 360)
    draw_three_circles(c, 448, 845, 32, (RED, GOLD, (96, 165, 250)))
    c.draw_text(48, 868, shz["dateline"], 2, GOLD)
    # COP31 (right)
    c.fill_rect(524, 696, 472, 200, TEAL)
    c.draw_text(544, 716, cop["kicker"], 2, GOLD)
    c.draw_text(544, 744, cop["headline"], 4, CREAM)
    c.text_block(544, 792, cop["body"], 2, CREAM, 360)
    draw_globe(c, 940, 835, 34, (120, 220, 190))
    c.draw_text(544, 868, cop["dateline"], 2, GOLD)

    # ---- ticker ----
    c.hline(28, 908, W - 56, GOLD, 3)
    c.fill_rect(28, 922, 118, 34, RED)
    c.draw_text(38, 930, "ALSO", 2, WHITE)
    c.text_block(158, 924, plan["ticker"], 2, CREAM, 838)

    # ---- footer ----
    foot_w = text_width(plan["footer"], 2)
    c.draw_text((W - foot_w) // 2, 978, plan["footer"], 2, MUTED)

    return encode_png(W, H, bytes(c.buf))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    png = render_poster()
    target = os.path.join(out_dir, "entry.png")
    tmp = os.path.join(out_dir, f".entry.{os.getpid()}.tmp")
    with open(tmp, "wb") as fh:
        fh.write(png)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, 0o644)
    os.replace(tmp, target)
    print(f"wrote {target} ({len(png)} bytes, "
          f"sha256={hashlib.sha256(png).hexdigest()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
