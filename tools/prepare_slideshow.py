#!/usr/bin/env python3
"""Resize and number photos for the HomeView photo frame.

The iPad Air 2 has 2 GB of RAM, so full-size 12-48 MP photos make the
Home Assistant app stutter or reload. This script makes small copies sized
for the photo frame (it is ~684 x 447 CSS px = ~1370 x 900 real pixels):

    python3 tools/prepare_slideshow.py ~/Pictures/Export ./slideshow --limit 80 --shuffle

Output: slideshow/photo001.jpg, photo002.jpg, ... Copy that folder to
/config/www/homeview/slideshow on the Home Assistant server and set
photos.count in homeview/config.yaml to the number printed at the end.

Needs Pillow (pip install pillow). HEIC files also need pillow-heif
(pip install pillow-heif); otherwise export them from Photos as JPEG first.
"""
from __future__ import annotations

import argparse
import pathlib
import random
import sys

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required: pip install pillow")

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
    HEIC = True
except ImportError:
    HEIC = False

EXTS = {".jpg", ".jpeg", ".png", ".webp"} | ({".heic", ".heif"} if HEIC else set())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=pathlib.Path, help="folder with your photos (searched recursively)")
    ap.add_argument("dst", type=pathlib.Path, help="output folder (existing photoNNN.jpg files are replaced)")
    ap.add_argument("--long-edge", type=int, default=1400, help="max long edge in px (default 1400)")
    ap.add_argument("--quality", type=int, default=80, help="JPEG quality (default 80)")
    ap.add_argument("--limit", type=int, default=0, help="use at most N photos (0 = all, max 999)")
    ap.add_argument("--shuffle", action="store_true", help="pick/number photos in random order")
    args = ap.parse_args()

    files = sorted(p for p in args.src.rglob("*") if p.suffix.lower() in EXTS)
    skipped_heic = [] if HEIC else [p for p in args.src.rglob("*") if p.suffix.lower() in (".heic", ".heif")]
    if args.shuffle:
        random.shuffle(files)
    limit = min(args.limit or 999, 999)
    files = files[:limit]
    if not files:
        print("No photos found.", "(HEIC files need: pip install pillow-heif)" if skipped_heic else "")
        return 1

    args.dst.mkdir(parents=True, exist_ok=True)
    for old in args.dst.glob("photo[0-9][0-9][0-9].jpg"):
        old.unlink()

    n = 0
    for src in files:
        try:
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((args.long_edge, args.long_edge), Image.LANCZOS)
                n += 1
                im.save(args.dst / f"photo{n:03d}.jpg", "JPEG", quality=args.quality, optimize=True, progressive=True)
        except Exception as exc:  # unreadable/corrupt file: skip it
            print(f"skip {src.name}: {exc}")

    total = sum(p.stat().st_size for p in args.dst.glob("photo*.jpg"))
    print(f"\nWrote {n} photos ({total / 1e6:.1f} MB) to {args.dst}")
    if skipped_heic:
        print(f"Skipped {len(skipped_heic)} HEIC files (pip install pillow-heif to include them).")
    print(f"Set  photos: count: {n}  in homeview/config.yaml, then rebuild.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
