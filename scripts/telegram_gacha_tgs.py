"""Small Telegram-native TGS vector wheel; no raster frames or GIF/MP4.

The first manual pilot intentionally demonstrates ROYAL only, without rewards.
The artwork is designed as a stable fixed-core rotary animation, not a clone of
Telegram's private dice emojis. Telegram's .TGS rules: 512px, 60fps, <=3s, 64KiB.
"""
from __future__ import annotations

import gzip
import json
import math

FRAME_RATE = 60
FRAMES = 180
SIDES = ('CLASSIC', 'ELITE', 'ROYAL', 'EPIC', 'MYTHIC', 'ETERNAL')
PALETTE = ('#51425d', '#852635', '#b57820', '#9b3826', '#63276f', '#126078')
GOLD = '#efbd7a'
BRIGHT_GOLD = '#ffe2af'
RUBY = '#c81d4d'


def rgba(hex_color: str) -> list[float]:
    return [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]


def _path(vertices: list[tuple[float, float]], color: str, *, stroke: str | None = None, width=1.0):
    n = len(vertices)
    path = {
        'ty': 'sh', 'nm': 'ornament', 'ks': {'a': 0, 'k': {
            'i': [[0, 0]] * n, 'o': [[0, 0]] * n,
            'v': [[round(x, 3), round(y, 3)] for x, y in vertices], 'c': True
        }}
    }
    items = [path, {'ty': 'fl', 'c': {'a': 0, 'k': rgba(color)}, 'o': {'a': 0, 'k': 100}, 'r': 1}]
    if stroke:
        items.append({'ty': 'st', 'c': {'a': 0, 'k': rgba(stroke)}, 'o': {'a': 0, 'k': 100}, 'w': {'a': 0, 'k': width}, 'lc': 2, 'lj': 2})
    return {'ty': 'gr', 'it': items + [{ 'ty': 'tr', 'p': {'a': 0, 'k': [0, 0]}, 'a': {'a': 0, 'k': [0, 0]}, 's': {'a': 0, 'k': [100, 100]}, 'r': {'a': 0, 'k': 0}, 'o': {'a': 0, 'k': 100}, 'sk': {'a': 0, 'k': 0}, 'sa': {'a': 0, 'k': 0}}]}


def _ellipse(cx: float, cy: float, radius: float, color: str, *, stroke=None, width=1.0):
    items = [
        {'ty': 'el', 'p': {'a': 0, 'k': [cx, cy]}, 's': {'a': 0, 'k': [2 * radius, 2 * radius]}},
        {'ty': 'fl', 'c': {'a': 0, 'k': rgba(color)}, 'o': {'a': 0, 'k': 100}, 'r': 1},
    ]
    if stroke:
        items.append({'ty': 'st', 'c': {'a': 0, 'k': rgba(stroke)}, 'o': {'a': 0, 'k': 100}, 'w': {'a': 0, 'k': width}})
    items.append({'ty': 'tr', 'p': {'a': 0, 'k': [0, 0]}, 'a': {'a': 0, 'k': [0, 0]}, 's': {'a': 0, 'k': [100, 100]}, 'r': {'a': 0, 'k': 0}, 'o': {'a': 0, 'k': 100}, 'sk': {'a': 0, 'k': 0}, 'sa': {'a': 0, 'k': 0}})
    return {'ty': 'gr', 'it': items}


def _point(angle: float, radius: float) -> tuple[float, float]:
    a = math.radians(angle)
    return (256 + radius * math.cos(a), 256 + radius * math.sin(a))


def _ring(radius: float, color: str, *, width: float = 3):
    return {'ty': 'gr', 'it': [
        {'ty': 'el', 'p': {'a': 0, 'k': [256, 256]}, 's': {'a': 0, 'k': [2*radius, 2*radius]}},
        {'ty': 'st', 'c': {'a': 0, 'k': rgba(color)}, 'o': {'a': 0, 'k': 100}, 'w': {'a': 0, 'k': width}, 'lc': 2, 'lj': 2},
        {'ty': 'tr', 'p': {'a': 0, 'k': [0, 0]}, 'a': {'a': 0, 'k': [0, 0]}, 's': {'a': 0, 'k': [100, 100]}, 'r': {'a': 0, 'k': 0}, 'o': {'a': 0, 'k': 100}, 'sk': {'a': 0, 'k': 0}, 'sa': {'a': 0, 'k': 0}}
    ]}


def _wedge(angle: float, color: str):
    vertices = [(256, 256)] + [_point(angle - 30 + k * 60 / 16, 187) for k in range(17)]
    return _path(vertices, color, stroke=GOLD, width=2.6)


def _star(angle: float, color: str):
    x, y = _point(angle, 120)
    vertices = [(x, y - 25), (x + 5, y - 5), (x + 24, y), (x + 5, y + 5),
                (x, y + 25), (x - 5, y + 5), (x - 24, y), (x - 5, y - 5)]
    return _path(vertices, color, stroke=GOLD, width=1.2)


def _layer(name, shapes, *, rotation=0, index=1):
    return {
        'ddd': 0, 'ind': index, 'ty': 4, 'nm': name,
        'sr': 1, 'ks': {
            'o': {'a': 0, 'k': 100},
            'r': rotation if isinstance(rotation, dict) else {'a': 0, 'k': rotation},
            'p': {'a': 0, 'k': [256, 256, 0]},
            'a': {'a': 0, 'k': [256, 256, 0]},
            's': {'a': 0, 'k': [100, 100, 100]},
        }, 'ao': 0, 'shapes': list(reversed(shapes)), 'ip': 0, 'op': FRAMES, 'st': 0, 'bm': 0
    }


def _spin_keyframes(final_degrees: float, *, launch: bool):
    if launch:
        points = [(0, 0), (40, 45), (90, 150), (140, 290), (179, 360)]
    else:
        # 3 full clockwise turns; initial and final 270deg avoid replay snap,
        # with the gold ROYAL sector under the 12 o'clock pointer at rest.
        points = [(0, 270), (30, 550), (68, 900), (110, 1160), (146, 1320), (168, final_degrees), (179, final_degrees)]
    keys = []
    for i, (frame, value) in enumerate(points):
        item = {'t': frame, 's': [value]}
        if i + 1 < len(points):
            item.update({'e': [points[i + 1][1]],
                         'i': {'x': [0.7], 'y': [1]}, 'o': {'x': [0.25], 'y': [0]}})
        keys.append(item)
    return {'a': 1, 'k': keys}


def make_tgs(*, launch: bool = False) -> bytes:
    angles = (-120, -60, 0, 60, 120, 180)
    spinning = [_ellipse(256, 256, 192, '#24121e', stroke=BRIGHT_GOLD, width=4)]
    for index, angle in enumerate(angles):
        spinning.append(_wedge(angle, PALETTE[index]))
        spinning.append(_star(angle, BRIGHT_GOLD if index == 2 else GOLD))
    for r, color in ((190, GOLD), (183, '#7b352b'), (176, BRIGHT_GOLD)):
        spinning.append(_ring(r, color, width=3.6 if r == 190 else 1.4))
    for a in range(0, 360, 30):
        if a % 60 == 0:
            x, y = _point(a, 183)
            spinning.append(_path([(x, y-5), (x+5, y), (x, y+5), (x-5, y)], RUBY, stroke=GOLD))
    fixed = [
        _ellipse(256, 256, 41, '#1c0b11', stroke=GOLD, width=6),
        _ellipse(256, 256, 34, '#772039', stroke=BRIGHT_GOLD, width=3),
        _path([(256, 225), (282, 256), (256, 286), (230, 256)], RUBY, stroke=BRIGHT_GOLD, width=2),
        _path([(256, 228), (273, 256), (256, 262)], '#fe648c'),
        _path([(256, 228), (239, 256), (256, 262)], '#a21639'),
        _ellipse(252, 244, 4, '#fff3d3'),
        # The 12 o'clock crown + long pointer are separate from the spinning layer.
        _path([(256, 18), (277, 45), (256, 78), (235, 45)], '#c62449', stroke=BRIGHT_GOLD, width=5),
        _path([(246, 62), (256, 126), (266, 62)], GOLD, stroke=BRIGHT_GOLD, width=1.5),
        _path([(256, 85), (256, 126), (261, 87)], '#fff1bf'),
        _path([(256, 22), (263, 44), (256, 59)], '#ff7195'),
    ]
    doc = {
        'v': '5.5.2', 'fr': FRAME_RATE, 'ip': 0, 'op': FRAMES,
        'w': 512, 'h': 512, 'nm': 'Velvet Gacha startup' if launch else 'Velvet Gacha Royal demo',
        'ddd': 0, 'assets': [],
        'layers': [
            _layer('stationary ruby and top pointer', fixed, index=1),
            _layer('geometrically rotating six-color wheel', spinning,
                   rotation=_spin_keyframes(1350, launch=launch), index=2),
        ]
    }
    raw = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    tgs = gzip.compress(raw, compresslevel=9, mtime=0)
    if len(tgs) > 65536:
        raise ValueError('TGS exceeds Telegram 64KiB limit')
    return tgs


if __name__ == '__main__':
    for start in (True, False):
        data = make_tgs(launch=start)
        print('start' if start else 'Royal', len(data), 'bytes')
