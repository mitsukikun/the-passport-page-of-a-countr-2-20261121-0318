#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Draws an invented passport spread for the Republic of Veskar: a data
page with a portrait and machine-readable zone, and a facing page with
a compass emblem, stamps and a signature. Pure standard library
(zlib + struct for the PNG); no network. Writes a 1024x1024 PNG to
/output/entry.png.
"""

import os
import struct
import zlib

W = 1024
H = 1024

# 5x7 bitmap font: each glyph is 7 rows of 5 bits.
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
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("01110", "10001", "00001", "00110", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def blend(self, x, y, c, a):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            for k in range(3):
                self.px[i + k] = int(self.px[i + k] * (1 - a) + c[k] * a)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.set(x, y, c)

    def vgrad_rect(self, x0, y0, x1, y1, c0, c1):
        for y in range(y0, y1):
            t = (y - y0) / max(1, y1 - y0 - 1)
            self.rect(x0, y, x1, y + 1, lerp(c0, c1, t))

    def disc(self, cx, cy, r, c, alpha=1.0):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    if alpha >= 1.0:
                        self.set(x, y, c)
                    else:
                        self.blend(x, y, c, alpha)

    def ellipse(self, cx, cy, rx, ry, c, alpha=1.0):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    if alpha >= 1.0:
                        self.set(x, y, c)
                    else:
                        self.blend(x, y, c, alpha)

    def hline(self, x0, x1, y, c, alpha=1.0):
        for x in range(x0, x1 + 1):
            if alpha >= 1.0:
                self.set(x, y, c)
            else:
                self.blend(x, y, c, alpha)

    def vline(self, x, y0, y1, c, alpha=1.0):
        for y in range(y0, y1 + 1):
            if alpha >= 1.0:
                self.set(x, y, c)
            else:
                self.blend(x, y, c, alpha)

    def line(self, x0, y0, x1, y1, c, width=1):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            t = i / steps
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            for dy in range(width):
                for dx in range(width):
                    self.set(x + dx, y + dy, c)

    def text(self, s, x, y, scale, c):
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                for col in range(5):
                    if glyph[row][col] == "1":
                        self.rect(x + col * scale, y + row * scale,
                                  x + (col + 1) * scale, y + (row + 1) * scale, c)
            x += 6 * scale

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale

    def text_centred_on(self, s, cx, y, scale, c):
        self.text(s, cx - self.text_width(s, scale) // 2, y, scale, c)


PAPER = (242, 232, 213)
NAVY = (28, 42, 84)
GOLD = (176, 138, 66)
TEAL = (16, 96, 110)
RED = (178, 44, 44)


def draw():
    cv = Canvas(W, H)
    cv.rect(0, 0, W, H, PAPER)
    # Outer gold double border.
    for t in range(3):
        cv.rect(10 + t, 10 + t, W - 10 - t, 13 + t, GOLD)
        cv.rect(10 + t, H - 13 - t, W - 10 - t, H - 10 - t, GOLD)
        cv.rect(10 + t, 10 + t, 13 + t, H - 10 - t, GOLD)
        cv.rect(W - 13 - t, 10 + t, W - 10 - t, H - 10 - t, GOLD)
    # Spine between the two pages.
    cv.vline(511, 24, H - 24, GOLD)
    cv.vline(513, 24, H - 24, GOLD)

    # ---- Left page: data page ----
    cv.rect(48, 48, 492, 118, NAVY)
    cv.text_centred_on("REPUBLIC OF VESKAR", 270, 76, 3, (240, 228, 196))
    cv.text_centred_on("PASSPORT", 270, 148, 9, NAVY)
    cv.text_centred_on("PASSEPORT", 270, 232, 4, (90, 80, 60))

    # Photo box with a simple portrait silhouette.
    cv.rect(80, 290, 252, 482, NAVY)
    cv.vgrad_rect(84, 294, 248, 478, (52, 130, 150), (24, 70, 100))
    cv.ellipse(166, 452, 58, 26, (28, 42, 84))        # shoulders
    cv.rect(158, 398, 174, 430, (216, 180, 142))      # neck
    cv.disc(166, 352, 36, (60, 44, 32))               # hair
    cv.disc(166, 370, 32, (216, 180, 142))            # head

    # Data fields.
    fields = [
        ("SURNAME", "VOSS"),
        ("GIVEN NAMES", "ALARA"),
        ("NATIONALITY", "VESKARIAN"),
        ("DATE OF BIRTH", "12 MAR 2001"),
        ("SEX", "F"),
        ("PASSPORT NO.", "VK 0042719"),
    ]
    y = 296
    for label, value in fields:
        cv.text(label, 280, y, 2, (120, 100, 70))
        cv.text(value, 280, y + 16, 3, NAVY)
        cv.hline(280, 478, y + 40, GOLD)
        y += 56
    # Machine-readable zone.
    cv.text("P<VKAVOSS<<ALARA<<<<<<<<<<<<<<", 60, 700, 2, NAVY)
    cv.text("VK0042719<7VES0103121F3103122<<<<<<04", 60, 728, 2, NAVY)
    cv.hline(48, 492, 676, GOLD)

    # ---- Right page: emblem page ----
    # Compass emblem: gold ring, navy star, VK monogram.
    cv.disc(754, 330, 122, GOLD)
    cv.disc(754, 330, 110, PAPER)
    cv.disc(754, 330, 104, NAVY)
    cv.disc(754, 330, 92, PAPER)
    for ang in range(8):
        import math
        a = math.radians(ang * 45)
        cv.line(754, 330, 754 + int(88 * math.cos(a)), 330 + int(88 * math.sin(a)),
                GOLD, 3)
    cv.disc(754, 330, 46, NAVY)
    cv.disc(754, 330, 38, PAPER)
    cv.text_centred_on("VK", 754, 312, 6, NAVY)
    cv.text_centred_on("VESKAR", 754, 486, 7, NAVY)
    cv.text_centred_on("THE BEARER OF THIS PASSPORT", 754, 556, 2, NAVY)
    cv.text_centred_on("IS UNDER THE PROTECTION OF", 754, 584, 2, NAVY)
    cv.text_centred_on("THE REPUBLIC OF VESKAR", 754, 612, 2, NAVY)

    # Red round stamp.
    cv.disc(872, 770, 66, RED)
    cv.disc(872, 770, 58, PAPER)
    cv.disc(872, 770, 52, RED)
    cv.disc(872, 770, 46, PAPER)
    cv.text_centred_on("VESKAR", 872, 750, 2, RED)
    cv.text_centred_on("2149", 872, 778, 2, RED)

    # Teal rectangular entry stamp.
    cv.rect(556, 700, 766, 802, TEAL)
    cv.rect(562, 706, 760, 796, PAPER)
    cv.text_centred_on("ADMITTED", 661, 722, 4, TEAL)
    cv.text_centred_on("PORT OF AURELIA", 661, 762, 2, TEAL)

    # Signature squiggle.
    import math
    for x in range(600, 780):
        y = 890 + int(8 * math.sin((x - 600) / 28.0))
        cv.set(x, y, NAVY)
        cv.set(x, y + 1, NAVY)
    cv.hline(600, 780, 906, NAVY)
    cv.text_centred_on("SIGNATURE", 690, 916, 2, (120, 100, 70))
    return cv


def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        row = bytearray(cv.px[y * cv.w * 3:(y + 1) * cv.w * 3])
        filt = bytearray(len(row))
        for i, b in enumerate(row):
            left = row[i - 3] if i >= 3 else 0
            filt[i] = (b - left) & 0xFF
        raw.append(1)
        raw.extend(filt)
    data = zlib.compress(bytes(raw), 9)

    def chunk(kind, payload):
        c = struct.pack(">I", len(payload)) + kind + payload
        return c + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", data)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    os.makedirs("/output", exist_ok=True)
    write_png(draw(), "/output/entry.png")


if __name__ == "__main__":
    main()
