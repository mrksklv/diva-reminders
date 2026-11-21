"""Build emoji_palette.json: which emoji are "generally" each basic color.

Renders every emoji with Apple Color Emoji (macOS only), classifies each opaque
pixel into one of the basic colors, and keeps an emoji for a color when at least
THRESHOLD of its pixels are that color. The emoji list and categories come from
Unicode's emoji-test.txt; japanese badges, zodiac, religious signs, media buttons and clock faces are skipped.

    pip install pillow
    python scripts/build_emoji_palette.py
"""

import colorsys
import json
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/System/Library/Fonts/Apple Color Emoji.ttc"
OUTPUT = Path(__file__).resolve().parent.parent / "emoji_palette.json"
THRESHOLD = 0.5  # share of an emoji's visible pixels that must be the color
COLORS = ("red", "orange", "yellow", "green", "blue", "purple", "pink", "brown", "black", "white")

EMOJI_TEST_URL = "https://unicode.org/Public/emoji/16.0/emoji-test.txt"
SKIP_GROUPS = {"Flags", "Component"}
# japanese/letter badges (🈶 🉐 🆓 🅰️), keycaps (🔟), zodiac (♊), religion (☸️), media buttons (🔂 ⏩)
SKIP_SUBGROUPS = {"alphanum", "keycap", "zodiac", "religion", "av-symbol"}
CLOCK_FACES = {chr(cp) for cp in range(0x1F550, 0x1F568)}  # 🕐 ... 🕧
SKIP_EMOJI = CLOCK_FACES | {"🚼", "✳️", "❇️", "💹"}
SKIN_TONES = {chr(cp) for cp in range(0x1F3FB, 0x1F400)}
# people in ZWJ sequences (professions, families, gendered variants) are mostly skin color
PEOPLE = {"\U0001F466", "\U0001F467", "\U0001F468", "\U0001F469", "\U0001F9D1", "\U0001F9D2", "\u2640", "\u2642"}


def classify(r: int, g: int, b: int) -> str | None:
    """Return the basic color of one pixel, or None for grays and in-between tones."""
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue = h * 360
    if v < 0.22:
        return "black"
    if s < 0.15:
        return "white" if v > 0.85 else None  # mid grays don't count for any color
    if s < 0.3 and v < 0.5:
        return None  # muddy dark grays
    if (hue < 45 or hue >= 345) and v < 0.6 and s > 0.3:
        return "brown"  # dark red-orange
    if hue < 12 or hue >= 345:
        return "pink" if s < 0.45 and v > 0.8 else "red"
    if hue < 40:
        return "orange"
    if hue < 68:
        return "yellow"
    if hue < 165:
        return "green"
    if hue < 255:
        return "blue"
    if hue < 310:
        return "purple"
    return "pink"


def candidates() -> list[str]:
    """Fully qualified emoji from emoji-test.txt, minus skipped categories and skin tones."""
    with urllib.request.urlopen(EMOJI_TEST_URL) as response:
        lines = response.read().decode("utf-8").splitlines()

    result = []
    group = subgroup = ""
    for line in lines:
        if line.startswith("# group:"):
            group = line.split(":", 1)[1].strip()
        elif line.startswith("# subgroup:"):
            subgroup = line.split(":", 1)[1].strip()
        elif "; fully-qualified" in line:
            char = line.split("#", 1)[1].split()[0]
            if char in SKIP_EMOJI:
                continue
            if group in SKIP_GROUPS or subgroup in SKIP_SUBGROUPS:
                continue
            chars = set(char)
            if SKIN_TONES & chars or ("\u200d" in char and PEOPLE & chars):
                continue
            result.append(char)
    return result


def color_shares(char: str, font: ImageFont.FreeTypeFont) -> dict[str, float] | None:
    """Render an emoji and return the share of its visible pixels in each color."""
    image = Image.new("RGBA", (540, 180), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((0, 0), char, font=font, embedded_color=True)
    box = image.getbbox()
    if not box:
        return None  # not in this font
    if box[2] > 180:
        return None  # drawn as several glyphs (ZWJ sequence Pillow can't combine)
    image = image.crop((0, 0, 180, 180)).resize((48, 48), Image.Resampling.LANCZOS)
    counts = dict.fromkeys(COLORS, 0)
    visible = 0
    for r, g, b, a in image.get_flattened_data():
        if a < 200:
            continue
        visible += 1
        color = classify(r, g, b)
        if color:
            counts[color] += 1
    if not visible:
        return None
    return {color: count / visible for color, count in counts.items()}


def main() -> None:
    font = ImageFont.truetype(FONT_PATH, 160)
    palette: dict[str, list[tuple[str, float]]] = {color: [] for color in COLORS}
    for char in candidates():
        shares = color_shares(char, font)
        if not shares:
            continue
        for color, share in shares.items():
            if share >= THRESHOLD:
                palette[color].append((char, round(share, 3)))
    for color in COLORS:
        palette[color].sort(key=lambda item: -item[1])
    OUTPUT.write_text(json.dumps(palette, ensure_ascii=False, indent=1), encoding="utf-8")
    for color in COLORS:
        print(f"{color}: {len(palette[color])}")


if __name__ == "__main__":
    main()
