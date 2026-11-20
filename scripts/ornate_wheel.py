"""Ornate six-rarity roulette demo, transparent background and fixed top pointer.

The source of the bundled default is a vector recreation of the visual reference.
If all six user-supplied GIFs are later checked into assets/roulette/original_gifs/,
the original assets take priority and the renderer is not used.
"""
from __future__ import annotations

import io
import math
from pathlib import Path

from scripts.wheel_gif import NAMES, WEIGHTS

ART_CENTERS = (330, 30, 90, 150, 210, 270)
SOURCE = Path(__file__).resolve().parents[1] / "assets" / "roulette" / "ornate-wheel.svg"
ORIGINAL_DIR = SOURCE.parent / "original_gifs"
SPIN_MS = 5940
REVEAL_DELAY_SECONDS = 7.5
FILE_NAMES = tuple(f"gacha_{name.lower()}.gif" for name in NAMES)


def art_target_angle(index: int, turns: int = 6) -> float:
    if type(index) is not int or not 0 <= index < 6 or not 1 <= turns <= 12:
        raise ValueError("Invalid rarity index / revolution count.")
    return 360.0 * turns + ((360.0 - ART_CENTERS[index]) % 360.0)


def art_index_at_pointer(angle: float) -> int:
    top = (360.0 - angle % 360) % 360
    distances = [abs((top - center + 180) % 360 - 180) for center in ART_CENTERS]
    return distances.index(min(distances))


def _index_frame(frame):
    """Reserve palette index 0 for transparent pixels in every GIF frame."""
    from PIL import Image
    rgb = frame.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT,
                                         dither=Image.Dither.NONE)
    colors = rgb.getpalette()[:765]
    pal = Image.frombytes("P", frame.size, bytes(
        0 if alpha < 100 else min(255, idx + 1)
        for idx, alpha in zip(rgb.tobytes(), frame.getchannel("A").tobytes())
    ))
    pal.putpalette([0, 0, 0] + colors)
    pal.info["transparency"] = 0
    return pal


def _pointer(frame):
    from PIL import ImageDraw
    side = frame.width
    scale = side / 450
    cx = side // 2
    draw = ImageDraw.Draw(frame)
    pts = [(cx - 16 * scale, 10 * scale), (cx + 16 * scale, 10 * scale),
           (cx, 58 * scale)]
    draw.polygon(pts, fill="#f8d5a7")
    draw.line(pts + [pts[0]], fill="#704451", width=max(1, int(2 * scale)))
    gem = [(cx, 16 * scale), (cx + 8 * scale, 24 * scale),
           (cx, 42 * scale), (cx - 8 * scale, 24 * scale)]
    draw.polygon(gem, fill="#b41a42")
    draw.line(gem + [gem[0]], fill="#ffe8ca", width=max(1, int(2 * scale)))
    draw.ellipse((cx-2*scale, 21*scale, cx+2*scale, 25*scale), fill="#fff8df")


def original_gifs_complete() -> bool:
    return all((ORIGINAL_DIR / name).is_file() for name in FILE_NAMES)


def render_ornate_gif(index: int, *, size: int = 360, frames: int = 64) -> tuple[bytes, float]:
    """Return GIF bytes and playback duration, never the winning rarity in a caption."""
    art_target_angle(index)
    if not 220 <= size <= 600 or not 32 <= frames <= 90:
        raise ValueError("Unsupported animation dimensions.")
    from PIL import Image
    if original_gifs_complete():
        file = ORIGINAL_DIR / FILE_NAMES[index]
        data = file.read_bytes()
        with Image.open(io.BytesIO(data)) as gif:
            if gif.format != "GIF" or gif.n_frames < 32:
                raise ValueError("Original rarity GIF is invalid.")
            duration = sum(
                gif.seek(n) or gif.info.get("duration", 0) for n in range(gif.n_frames)
            ) / 1000
        if not 4 <= duration <= 12 or len(data) > 8_000_000:
            raise ValueError("Original GIF failed safety limits.")
        return data, duration

    import cairosvg
    image_data = cairosvg.svg2png(bytestring=SOURCE.read_bytes(), output_width=size, output_height=size)
    disk = Image.open(io.BytesIO(image_data)).convert("RGBA")
    all_frames = []
    end_angle = art_target_angle(index)
    for n in range(frames):
        t = n / (frames - 1)
        fraction = 1.0 - (1.0 - t) ** 4
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.alpha_composite(disk.rotate(-end_angle * fraction,
                                         resample=Image.Resampling.BICUBIC))
        _pointer(canvas)
        all_frames.append(_index_frame(canvas))
    # Exactly 5.94 sec for 64 frames (63 x 80ms + 900ms final hold).
    regular = (SPIN_MS - 900) // (frames - 1)
    timings = [regular] * (frames - 1)
    timings.append(SPIN_MS - regular * (frames - 1))
    result = io.BytesIO()
    all_frames[0].save(result, format="GIF", save_all=True, append_images=all_frames[1:],
                       duration=timings, loop=0, transparency=0, disposal=2, optimize=False)
    data = result.getvalue()
    if not data.startswith(b"GIF89a") or len(data) > 8_000_000:
        raise ValueError("Generated GIF exceeds Telegram demo safety limits.")
    return data, sum(timings) / 1000
