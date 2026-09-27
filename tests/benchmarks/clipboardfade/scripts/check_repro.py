#!/usr/bin/env python3
"""Pixel verdict for the MultiEffect mask bug reproduction.

Expected on an affected stack (invisible maskSource grabbed as an empty
texture): row 1 renders, row 3 is empty, row 4 (inverted) renders.
Any other combination means the environment does NOT reproduce the bug.
"""
import sys

from PIL import Image

ROWS = {"1_plain": (10, 54), "2_nomask": (65, 109),
        "3_mask": (120, 164), "4_inverted": (175, 219)}


def reds(im, y0, y1, x0=225, x1=605):
    px = im.load()
    w, h = im.size
    n = 0
    for y in range(y0, min(y1, h)):
        for x in range(x0, min(x1, w)):
            r, g, b = px[x, y]
            if r > 150 and g < 100 and b < 100:
                n += 1
    return n


def main():
    im = Image.open(sys.argv[1]).convert("RGB")
    counts = {k: reds(im, y0, y1) for k, (y0, y1) in ROWS.items()}
    for k, v in counts.items():
        print(f"{k}: {v}")
    reproduced = counts["1_plain"] > 100 and counts["2_nomask"] > 100 \
        and counts["3_mask"] == 0 and counts["4_inverted"] > 100
    print("VERDICT:", "BUG-REPRODUCED" if reproduced
          else "bug NOT reproduced (mask renders or controls missing)")


if __name__ == "__main__":
    main()
