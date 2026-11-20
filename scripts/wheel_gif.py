"""GIF fallback for Telegram Bot API: six weighted sectors, exact pointer stop.

Dependency: Pillow (manual smoke only). No network, secrets or user information.
"""
from __future__ import annotations

import io
import math
from pathlib import Path

WEIGHTS = (25, 22, 19, 16, 11, 7)
NAMES = ("CLASSIC", "ELITE", "ROYAL", "EPIC", "MYTHIC", "ETERNAL")
COLORS = ("#8d879d", "#d07171", "#d4a652", "#d96b4a", "#ad74c7", "#64b8c9")


def sector_center(index: int) -> float:
    if type(index) is not int or not 0 <= index < len(WEIGHTS):
        raise ValueError("Invalid rarity index.")
    return (sum(WEIGHTS[:index]) + WEIGHTS[index] / 2) * 3.6


def target_angle(index: int, turns: int = 6) -> float:
    if type(turns) is not int or not 1 <= turns <= 15:
        raise ValueError("Invalid revolution count.")
    return 360.0 * turns + (360.0 - sector_center(index)) % 360.0


def pointer_index(angle: float) -> int:
    # Image rotation uses negative angles to rotate the artwork clockwise.
    unrotated = (360.0 - (angle % 360.0)) % 360.0
    distance = unrotated / 3.6
    count = 0
    for i, weight in enumerate(WEIGHTS):
        count += weight
        if distance < count:
            return i
    return len(WEIGHTS) - 1


def _font(size: int):
    from PIL import ImageFont

    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _base_disk(size: int):
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    painter = ImageDraw.Draw(image)
    cx = cy = size // 2
    radius = int(size * .44)
    painter.ellipse((cx-radius-6, cy-radius-6, cx+radius+6, cy+radius+6),
                    fill="#281a30", outline="#f5d2a2", width=5)
    cursor = 0.0
    for index, weight in enumerate(WEIGHTS):
        a = cursor * math.pi / 180.0
        b = (cursor + weight * 3.6) * math.pi / 180.0
        points = [(cx, cy)]
        samples = max(10, int(weight * .8))
        for j in range(samples + 1):
            angle = a + (b - a) * j / samples
            points.append((cx + radius * math.sin(angle), cy - radius * math.cos(angle)))
        painter.polygon(points, fill=COLORS[index])
        painter.line([points[0], points[1]], fill="#e8caa9", width=2)
        middle = (cursor + weight * 1.8) * math.pi / 180.0
        x = cx + radius * .69 * math.sin(middle)
        y = cy - radius * .69 * math.cos(middle)
        painter.text((x, y - size*.02), NAMES[index], anchor="mm", font=_font(11),
                     fill="#fff7ee", stroke_width=1, stroke_fill="#342131")
        painter.text((x, y + size*.023), str(weight) + "%", anchor="mm", font=_font(12),
                     fill="#fff7ee", stroke_width=1, stroke_fill="#342131")
        cursor += weight * 3.6
    painter.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                    outline="#f6dcba", width=3)
    return image


def _frame(disk, degrees: float):
    from PIL import Image, ImageDraw

    size = disk.width
    background = Image.new("RGBA", (size, size), "#221529")
    rotated = disk.rotate(-degrees, resample=Image.Resampling.BICUBIC)
    background.alpha_composite(rotated)
    painter = ImageDraw.Draw(background)
    c = size // 2
    r = int(size * .092)
    painter.ellipse((c-r, c-r, c+r, c+r), fill="#2b1b34",
                    outline="#f7d7ad", width=4)
    painter.text((c, c), "✦", font=_font(24), anchor="mm", fill="#f5d5af")
    painter.polygon([(c-15, 11), (c+15, 11), (c, 47)], fill="#f9dbac")
    painter.line([(c-15, 11), (c, 47), (c+15, 11)],
                 fill="#6b3e40", width=2)
    return background.convert("RGB")


def render_wheel_gif(index: int, *, size: int = 320, frames: int = 64) -> bytes:
    """Create a short finite animation from a demo-only server-selected index."""
    if size < 220 or size > 600 or frames < 32 or frames > 100:
        raise ValueError("Unsupported GIF format.")
    # Pillow is loaded only in the manual workflow; unit tests on ordinary CI
    # do not need to install it to verify geometry and authentication contracts.
    disk = _base_disk(size)
    final_angle = target_angle(index)
    images = []
    for n in range(frames):
        t = n / (frames - 1)
        # Fast launch, slow landing; final frame lands at the sector center.
        fraction = 1.0 - (1.0 - t) ** 4
        images.append(_frame(disk, final_angle * fraction))
    # Hold the result for a moment. Telegram GIF players may loop the clip.
    images.extend([images[-1].copy() for _ in range(10)])
    output = io.BytesIO()
    images[0].save(output, format="GIF", save_all=True,
                   append_images=images[1:], duration=70, optimize=True)
    result = output.getvalue()
    if len(result) > 8_000_000:
        raise ValueError("Animation exceeded safe demo size limit.")
    return result
