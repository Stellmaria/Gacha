"""Render the restricted vector subset used by our Telegram TGS wheel.

TGS is rendered back-to-front by Telegram/Lottie. A file can be valid JSON,
yet its background may occlude all segments. This independent still-frame
preview makes such a mistake visible and testable without Telegram tokens.
"""
from __future__ import annotations
import gzip
import json
import math
from io import BytesIO


def _rgb(color):
    return tuple(round(255 * value) for value in color)


def _spin_point(point, deg, *, origin=256):
    x, y = point
    angle = math.radians(deg)
    dx, dy = x - origin, y - origin
    return (origin + dx * math.cos(angle) - dy * math.sin(angle),
            origin + dx * math.sin(angle) + dy * math.cos(angle))


def render_frame(tgs: bytes, frame: int):
    from PIL import Image, ImageDraw
    if not 0 <= frame < 180:
        raise ValueError('Frame index outside Telegram TGS duration')
    doc = json.loads(gzip.decompress(tgs))
    image = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Lottie arrays of layers and groups are drawn in reverse painter order.
    for layer in reversed(doc['layers']):
        rotation = layer['ks']['r']
        degrees = rotation['k'] if rotation['a'] == 0 else _at(rotation['k'], frame)
        for group in reversed(layer['shapes']):
            elements = {it['ty']: it for it in group['it'] if it['ty'] in ('sh', 'el', 'fl', 'st')}
            fill = elements.get('fl')
            stroke = elements.get('st')
            fill_color = _rgb(fill['c']['k']) if fill else None
            stroke_color = _rgb(stroke['c']['k']) if stroke else None
            width = round(stroke['w']['k']) if stroke else 0
            if 'sh' in elements:
                vertices = [_spin_point(point, degrees) for point in elements['sh']['ks']['k']['v']]
                if fill_color:
                    draw.polygon(vertices, fill=fill_color)
                if stroke_color:
                    draw.line(vertices + vertices[:1], fill=stroke_color, width=width, joint='curve')
            elif 'el' in elements:
                el = elements['el']
                cx, cy = _spin_point(el['p']['k'], degrees)
                half_w, half_h = (v / 2 for v in el['s']['k'])
                draw.ellipse((cx - half_w, cy - half_h, cx + half_w, cy + half_h),
                             fill=fill_color, outline=stroke_color, width=width)
    return image


def _at(frames, t):
    for i, current in enumerate(frames[:-1]):
        next_frame = frames[i+1]
        if current['t'] <= t < next_frame['t']:
            alpha = (t - current['t']) / (next_frame['t'] - current['t'])
            return current['s'][0] * (1-alpha) + next_frame['s'][0] * alpha
    return frames[-1]['s'][0]


def assert_visible_sectors_and_core(tgs: bytes):
    from scripts.telegram_gacha_tgs import PALETTE, rgba
    # First frame of startup TGS: six distinct colored wedges must actually
    # be visible, not covered by the filled background circle.
    image = render_frame(tgs, 0)
    angles = (-120, -60, 0, 60, 120, 180)
    for angle, color in zip(angles, PALETTE):
        x, y = _spin_point((256+95, 256), angle)
        observed = image.getpixel((round(x), round(y)))[:3]
        expected = tuple(round(n * 255) for n in rgba(color))
        if observed != expected:
            raise AssertionError(f'Invisible or wrongly overpainted segment at {angle}: {observed}, expected {expected}')
    ruby_color = image.getpixel((256, 256))
    if ruby_color[0] < 120 or ruby_color[3] == 0:
        raise AssertionError(f'Ruby not drawn above the fixed gold mounting: {ruby_color}')
    if image.getpixel((0,0))[3] != 0:
        raise AssertionError('Sticker transparent corner lost')
    return image


if __name__ == '__main__':
    from scripts.telegram_gacha_tgs import make_tgs
    import sys
    image = assert_visible_sectors_and_core(make_tgs(launch=True))
    if len(sys.argv) == 2:
        image.save(sys.argv[1])
    print('TGS visual surface check PASSED: six sector colors, ruby center, transparency')
