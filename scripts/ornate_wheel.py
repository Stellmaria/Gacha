"""Ornate six-rarity roulette demo, transparent background and fixed top pointer.

The source of the bundled default is a vector recreation of the visual reference.
If all six user-supplied GIFs are later checked into assets/roulette/original_gifs/,
the original assets take priority and the renderer is not used.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

from scripts.wheel_gif import NAMES

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


# Exact hashes of the user-approved animations, not regenerated substitutes.
ORIGINAL_SHA256 = {
    'gacha_classic.gif': '1568f16b5312dd7e5d907a549e33f02b38ac67b70da55017d3afd3a56b028e69',
    'gacha_elite.gif': 'ff586776a7ac15034dbcce5ad244c9e9e50a03238e5b0260561c53ddf7ceef8e',
    'gacha_royal.gif': 'b4aec0f6b53ea77196ff46c5561fc4bcc9c206239bef37f11105b4227a033c5c',
    'gacha_epic.gif': 'b84086327c34830dff102a268ab049fe94440e65b6fa8c7a2b56da2cd7358ba1',
    'gacha_mythic.gif': 'cb15204926d6830e7f41be262f8f3d4466a655e6503373ae886d2690216efe66',
    'gacha_eternal.gif': '530600e3f72f52e85d315608891c94374fcd0ead956e2abe5cb6e8c1b80d988c',
}


def original_gifs_complete() -> bool:
    return all((ORIGINAL_DIR / name).is_file() for name in FILE_NAMES)


def render_ornate_gif(index: int, *, size: int = 450, frames: int = 64) -> tuple[bytes, float]:
    """Return the original user-approved GIF bytes. Never silently render SVG art."""
    art_target_angle(index)
    if (size, frames) != (450, 64):
        raise ValueError("Original assets are fixed at 450x450 and 64 frames.")
    path = ORIGINAL_DIR / FILE_NAMES[index]
    data = path.read_bytes()  # fail closed: no wrong visual if an asset is missing
    if not data.startswith(b"GIF89a") or len(data) >= 8_000_000:
        raise ValueError("Approved GIF is invalid or exceeds demo size cap.")
    if hashlib.sha256(data).hexdigest() != ORIGINAL_SHA256[path.name]:
        raise ValueError("GIF differs from the approved original asset.")
    from PIL import Image
    with Image.open(io.BytesIO(data)) as gif:
        if gif.format != "GIF" or gif.size != (450, 450) or gif.n_frames != 64:
            raise ValueError("Approved GIF geometry/frame count is invalid.")
        duration_ms = 0
        for n in range(gif.n_frames):
            gif.seek(n)
            duration_ms += gif.info.get("duration", 0)
        for n in (0, gif.n_frames - 1):
            gif.seek(n)
            if gif.convert("RGBA").getpixel((0, 0))[3] != 0:
                raise ValueError("Approved GIF must have a transparent background.")
    duration = duration_ms / 1000
    if not 5.5 <= duration <= 6.5:
        raise ValueError("Approved GIF duration is outside the expected window.")
    return data, duration
