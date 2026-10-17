"""Regenerate every derived brand image from ``assets/logo-master.png``.

    python tools/build_brand_assets.py

The master is a square logo on a solid dark background: an emblem (the
field-line cube) above a "VectorMachine" wordmark.  The parts are found
automatically, so a redrawn master with the same layout needs no changes.

Outputs
- ``src/ui/assets/icon-<size>.png`` and ``app.ico``: the emblem on a rounded
  dark tile, for the window/taskbar icon (and the packaged .exe later).
- ``src/ui/assets/logo-tile.png``: the full logo on a rounded tile, for the
  About dialog and the PDF report header.
- ``assets/readme-logo-dark.png``: the full logo with a transparent
  background, for GitHub's dark theme.
- ``assets/readme-logo-light.png``: the rounded tile, for GitHub's light
  theme, where the white wordmark and axes would otherwise vanish.
- ``assets/social-preview.png``: a 1280x640 card for the repository's
  social preview (uploaded by hand under Settings > Social preview).
"""

from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "assets" / "logo-master.png"
UI_ASSETS = ROOT / "src" / "ui" / "assets"
REPO_ASSETS = ROOT / "assets"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
TAGLINE = "Symbolic divergence & curl, with 3D vector-field visualization"
# A pixel is "content" if it differs from the background by more than this
# (sum of absolute RGB differences).
CONTENT_THRESHOLD = 60


def _content_mask(image, background):
    pixels = np.asarray(image.convert("RGB"), dtype=np.int16)
    return np.abs(pixels - np.array(background, dtype=np.int16)).sum(axis=2) > CONTENT_THRESHOLD


def _bbox(mask, rows=slice(None)):
    sub = mask[rows]
    ys, xs = np.nonzero(sub)
    top = (rows.start or 0) + ys.min()
    return xs.min(), top, xs.max() + 1, (rows.start or 0) + ys.max() + 1


def find_parts(image, background):
    """Return the (emblem, wordmark) bounding boxes."""
    mask = _content_mask(image, background)
    rows = np.nonzero(mask.any(axis=1))[0]
    # The widest band of empty rows inside the content separates the two.
    gaps = np.diff(rows)
    split = rows[np.argmax(gaps)] + 1
    emblem = _bbox(mask, slice(0, split))
    wordmark = _bbox(mask, slice(split, None))
    return emblem, wordmark


def square_crop(image, box, pad_ratio):
    left, top, right, bottom = box
    cx, cy = (left + right) / 2, (top + bottom) / 2
    half = max(right - left, bottom - top) / 2 * (1 + pad_ratio)
    return image.crop((round(cx - half), round(cy - half), round(cx + half), round(cy + half)))


def rounded(image, radius_ratio=0.18):
    """Give ``image`` rounded, transparent corners."""
    image = image.convert("RGBA")
    scale = 4  # draw the mask large and downsample, for smooth edges
    w, h = image.size
    mask = Image.new("L", (w * scale, h * scale), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, w * scale - 1, h * scale - 1), radius=int(min(w, h) * radius_ratio * scale), fill=255
    )
    image.putalpha(mask.resize((w, h), Image.LANCZOS))
    return image


# Per-channel difference from the background (out of 255) treated as noise.
# The master's "solid" background varies by a few levels.
NOISE_TOLERANCE = 6


def colour_to_alpha(image, background):
    """Remove a dark background, keeping glows and anti-aliasing (like GIMP's
    "Colour to Alpha"): each pixel becomes the most transparent colour that,
    composited over ``background``, reproduces it.

    Only pixels *brighter* than the background count as content.  With a
    near-black background, the usual "darker than background" term divides
    by a tiny value and turns faint noise into a visible haze.
    """
    rgb = np.asarray(image.convert("RGB"), dtype=np.float64) / 255.0
    bg = np.array(background, dtype=np.float64) / 255.0
    tolerance = NOISE_TOLERANCE / 255.0
    above = np.maximum(rgb - bg - tolerance, 0.0) / np.maximum(1.0 - bg - tolerance, 1e-6)
    alpha = np.clip(above.max(axis=2), 0.0, 1.0)
    safe = np.where(alpha > 0, alpha, 1.0)[..., None]
    colour = np.clip(bg + (rgb - bg) / safe, 0.0, 1.0)
    rgba = np.dstack([colour, alpha]) * 255.0
    return Image.fromarray(rgba.round().astype(np.uint8), "RGBA")


def _font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / name), size)


def _save(image, path, palette=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if palette:
        # 256 colours (alpha kept) look identical here at a fraction of the size.
        image = image.quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    image.save(path, optimize=True)
    print(f"{path.relative_to(ROOT)}  {image.size[0]}x{image.size[1]}  {path.stat().st_size // 1024} KB")


def build():
    master = Image.open(MASTER).convert("RGB")
    background = master.getpixel((8, 8))
    emblem_box, wordmark_box = find_parts(master, background)
    full_box = (
        min(emblem_box[0], wordmark_box[0]), emblem_box[1],
        max(emblem_box[2], wordmark_box[2]), wordmark_box[3],
    )

    # Icons: just the emblem (the wordmark is unreadable at icon sizes).
    # The square around a tall emblem can reach into the wordmark below it,
    # so blank the wordmark out first.
    emblem_only = master.copy()
    ImageDraw.Draw(emblem_only).rectangle((0, wordmark_box[1], master.width, master.height), fill=background)
    emblem = square_crop(emblem_only, emblem_box, pad_ratio=0.12)
    for size in ICON_SIZES:
        _save(rounded(emblem.resize((size, size), Image.LANCZOS), 0.2), UI_ASSETS / f"icon-{size}.png")
    ico_path = UI_ASSETS / "app.ico"
    rounded(emblem.resize((256, 256), Image.LANCZOS), 0.2).save(
        ico_path, sizes=[(s, s) for s in ICON_SIZES]
    )
    print(f"{ico_path.relative_to(ROOT)}  sizes {ICON_SIZES}  {ico_path.stat().st_size // 1024} KB")

    # The full logo on a rounded tile, and transparent.
    full = square_crop(master, full_box, pad_ratio=0.14)
    _save(rounded(full.resize((512, 512), Image.LANCZOS)), UI_ASSETS / "logo-tile.png", palette=True)
    _save(rounded(full.resize((560, 560), Image.LANCZOS)), REPO_ASSETS / "readme-logo-light.png", palette=True)
    margin = round(0.04 * (full_box[2] - full_box[0]))  # keep arrow tips off the edge
    padded = (full_box[0] - margin, full_box[1] - margin, full_box[2] + margin, full_box[3] + margin)
    transparent = colour_to_alpha(master.crop(padded), background)
    transparent.thumbnail((560, 560), Image.LANCZOS)
    _save(transparent, REPO_ASSETS / "readme-logo-dark.png", palette=True)

    # Social preview: emblem on the left, wordmark and tagline on the right.
    card = Image.new("RGB", (1280, 640), background)
    emblem_art = colour_to_alpha(master.crop(emblem_box), background)
    emblem_art.thumbnail((440, 440), Image.LANCZOS)
    card.paste(emblem_art, (90, (640 - emblem_art.height) // 2), emblem_art)
    wordmark_art = colour_to_alpha(master.crop(wordmark_box), background)
    wordmark_art.thumbnail((640, 150), Image.LANCZOS)
    text_left = 590
    card.paste(wordmark_art, (text_left, 210), wordmark_art)
    draw = ImageDraw.Draw(card)
    words, lines, line = TAGLINE.split(), [], ""
    font = _font(30)
    for word in words:  # wrap the tagline to the right-hand column
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) > 1280 - text_left - 70:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    y = 210 + wordmark_art.height + 36
    for text in lines:
        draw.text((text_left + 6, y), text, font=font, fill=(200, 208, 220))
        y += 42
    _save(card, REPO_ASSETS / "social-preview.png", palette=True)


if __name__ == "__main__":
    build()
