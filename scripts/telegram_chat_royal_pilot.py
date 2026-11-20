#!/usr/bin/env python3
"""Explicit MANUAL, single-user Telegram chat UX pilot. No GIF, MP4, grants or database.

A separate workflow permits testing this independent alternative without changing
existing six-outcome GIF smoke or setting up another bot. The first visual pilot
is intentionally fixed to ROYAL: it does not claim to run random gacha odds.
"""
from __future__ import annotations

import io
import json
import os
import re
import secrets
import sys
import time
from pathlib import Path
from urllib.request import Request

from scripts.telegram_inline_smoke import DemoError, _read_response, api
from scripts.telegram_preflight import ProbeFailure, check_bot
from scripts.telegram_widget_smoke import choose_owner
from scripts.telegram_gacha_tgs import make_tgs

CALLBACK = 'gacha:pilot:royal:v1'
POLL_SECONDS = 80
INTRO_SECONDS = 3.1
OUTCOME_SECONDS = 3.4
BOT_URL = 'https://api.telegram.org/bot'

INTRO_CAPTION = ('Ежедневная рулетка · визуальный тест\n\n'
                 'Шесть редкостей: Classic · Elite · Royal · Epic · Mythic · Eternal\n'
                 'ДЕМО: первый просмотр — Royal. Карты и попытки не начисляются.')
SPINUP_CAPTION = 'Рубин пробуждается…\nДЕМО: без начислений.'
SPINNING_CAPTION = 'Колесо вращается…\nСудьба делает выбор. ДЕМО: без начислений.'
FINAL_CAPTION = 'Колесо остановилось.\nРезультат раскрывается ниже.'
REWARD_CAPTION = 'ДЕМО · ROYAL\nМакет карточки без персонажа. Никаких настоящих наград или списаний.'


def multipart_request(token: str, method: str, chat_id: int, field: str,
                      filename: str, mime: str, raw: bytes,
                      *, caption: str | None = None, reply_markup: dict | None = None):
    """One whitelisted upload; token and chat identity are not logged."""
    if method not in ('sendPhoto', 'sendSticker') or field not in ('photo', 'sticker'):
        raise DemoError('Media method not permitted for the chat pilot.')
    if method == 'sendPhoto' and (field != 'photo' or not raw.startswith(b'\xff\xd8') or len(raw) > 5_000_000):
        raise DemoError('Only small JPEG photo uploads are allowed.')
    if method == 'sendSticker' and (field != 'sticker' or not raw.startswith(b'\x1f\x8b') or len(raw) > 65536):
        raise DemoError('Only small TGS sticker uploads are allowed.')
    boundary = 'gacha_' + secrets.token_hex(12)
    parts = []
    values = {'chat_id': str(chat_id)}
    if caption is not None:
        values['caption'] = caption
    if reply_markup is not None:
        values['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
    for name, value in values.items():
        parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="' + name + '"\r\n\r\n' + value + '\r\n').encode('utf-8'))
    parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="' + field + '"; filename="' + filename + '"\r\nContent-Type: ' + mime + '\r\n\r\n').encode('utf-8'))
    parts += [raw, ('\r\n--' + boundary + '--\r\n').encode('ascii')]
    req = Request(BOT_URL + token + '/' + method, method='POST', data=b''.join(parts),
                  headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    result = _read_response(req, timeout=20)
    if not isinstance(result, dict) or type(result.get('message_id')) is not int:
        raise DemoError('Telegram did not acknowledge the media message.')
    return result


def send_sticker(token: str, chat_id: int, *, start: bool):
    data = make_tgs(launch=start)
    return multipart_request(token, 'sendSticker', chat_id, 'sticker',
                             'gacha-launch.tgs' if start else 'gacha-royal.tgs',
                             'application/x-tgsticker', data)


def cover_photo() -> bytes:
    """Still frame from the original owner-approved wheel, never regenerate anatomy.

    This temporary 1:1 preview is limited to this manual pilot. The full
    portrait composition can be added when the owner's PNG is committed.
    """
    from PIL import Image, ImageDraw
    source = Path(__file__).resolve().parents[1] / 'assets/roulette/original_gifs/gacha_classic.gif'
    with Image.open(source) as frames:
        frames.seek(0)
        wheel = frames.convert('RGBA')
    image = Image.new('RGB', (512, 512), '#130b13')
    image.paste(wheel.resize((476, 476), Image.Resampling.LANCZOS), (18, 18),
                wheel.resize((476, 476), Image.Resampling.LANCZOS))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 4, 508, 508), radius=23, outline='#bd754f', width=3)
    out = io.BytesIO()
    image.save(out, format='JPEG', quality=87, optimize=True)
    return out.getvalue()


def demo_reward_photo() -> bytes:
    """Honest placeholder card, explicitly no fictional character/grant."""
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (540, 760), '#160c17')
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((16, 16, 524, 744), radius=31, outline='#d79b62', width=5)
    d.rounded_rectangle((32, 32, 508, 728), radius=24, outline='#703b49', width=2)
    d.ellipse((130, 130, 410, 410), fill='#3d1427', outline='#e1ac78', width=9)
    d.polygon([(270, 166), (368, 270), (270, 377), (172, 270)], fill='#ab1e48', outline='#f1c99b')
    d.polygon([(270, 182), (299, 263), (270, 299), (238, 263)], fill='#f975a0')
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', 52)
        small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    except OSError:
        font = small = ImageFont.load_default()
    d.text((270, 485), 'ROYAL', font=font, anchor='mm', fill='#f4d6b5')
    d.text((270, 552), 'VISUAL DEMO', font=small, anchor='mm', fill='#d49a91')
    d.text((270, 598), 'NO REWARDS', font=small, anchor='mm', fill='#b4867e')
    out = io.BytesIO()
    image.save(out, format='JPEG', quality=87, optimize=True)
    return out.getvalue()


def matches_pilot_callback(update: dict, chat_id: int, user_id: int, message_id: int) -> bool:
    q = update.get('callback_query')
    if not isinstance(q, dict) or q.get('data') != CALLBACK or not isinstance(q.get('id'), str) or not q['id']:
        return False
    sender, message = q.get('from'), q.get('message')
    if not isinstance(sender, dict) or not isinstance(message, dict) or not isinstance(message.get('chat'), dict):
        return False
    return (sender.get('id') == user_id == chat_id == message['chat'].get('id')
            and message['chat'].get('type') == 'private' and message.get('message_id') == message_id)


def edit_caption(token: str, chat_id: int, mid: int, caption: str) -> None:
    if caption not in (SPINUP_CAPTION, SPINNING_CAPTION, FINAL_CAPTION):
        raise DemoError('Unsafe caption stage.')
    req = Request(BOT_URL + token + '/editMessageCaption', method='POST',
                  data=json.dumps({'chat_id': chat_id, 'message_id': mid, 'caption': caption}, ensure_ascii=False).encode('utf-8'),
                  headers={'Content-Type': 'application/json'})
    result = _read_response(req)
    if result is not True and not isinstance(result, dict):
        raise DemoError('Telegram did not acknowledge caption update.')


def deliver_royal_sequence(token: str, chat_id: int, cover_mid: int, *, sleeper=time.sleep):
    """Order: launch sticker -> result sticker -> server reveal -> placeholder card."""
    edit_caption(token, chat_id, cover_mid, SPINUP_CAPTION)
    send_sticker(token, chat_id, start=True)
    sleeper(INTRO_SECONDS)
    edit_caption(token, chat_id, cover_mid, SPINNING_CAPTION)
    send_sticker(token, chat_id, start=False)
    sleeper(OUTCOME_SECONDS)
    edit_caption(token, chat_id, cover_mid, FINAL_CAPTION)
    msg = api(token, 'sendMessage', {
        'chat_id': chat_id,
        'text': 'Выпала редкость: ROYAL\nТолько визуальный тест: карт и списаний нет.'
    })
    if not isinstance(msg, dict) or type(msg.get('message_id')) is not int:
        raise DemoError('Telegram did not acknowledge the result text.')
    multipart_request(token, 'sendPhoto', chat_id, 'photo', 'royal-demo.jpg',
                      'image/jpeg', demo_reward_photo(), caption=REWARD_CAPTION)


def run() -> None:
    token = os.environ.get('GACHA_BOT_TOKEN', '')
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]{10,}', token):
        raise DemoError('GACHA_BOT_TOKEN missing or malformed.')
    try:
        check_bot(token, 'production')
    except ProbeFailure:
        raise DemoError('Telegram getMe failed for the ordinary test-purpose bot.') from None

    updates = api(token, 'getUpdates', {
        'timeout': 0, 'limit': 100, 'allowed_updates': ['message', 'callback_query']
    })
    if not isinstance(updates, list):
        raise DemoError('Invalid Telegram updates response.')
    try:
        chat_id, user_id = choose_owner(updates, int(time.time()))
    except Exception:
        raise DemoError('Send exactly one fresh /wheel from an authorized private chat.') from None
    offset = max((u.get('update_id') for u in updates if type(u.get('update_id')) is int), default=-1) + 1
    if offset <= 0:
        raise DemoError('Missing Telegram update offset.')
    api(token, 'getUpdates', {'offset': offset, 'timeout': 0,
                              'allowed_updates': ['message', 'callback_query']})
    cover = multipart_request(token, 'sendPhoto', chat_id, 'photo', 'gacha-idle.jpg',
                              'image/jpeg', cover_photo(), caption=INTRO_CAPTION,
                              reply_markup={'inline_keyboard': [[{
                                  'text': '✦ Крутить (Royal · демо)', 'callback_data': CALLBACK
                              }]]})
    cover_mid = cover['message_id']
    print('Royal-only visual demo sent. Awaiting one button press within 80s.')
    until = time.monotonic() + POLL_SECONDS
    while time.monotonic() < until:
        remaining = max(1, int(until - time.monotonic()))
        batch = api(token, 'getUpdates', {
            'offset': offset, 'timeout': min(8, remaining), 'limit': 50,
            'allowed_updates': ['message', 'callback_query']
        })
        if not isinstance(batch, list):
            raise DemoError('Invalid Telegram callback batch.')
        for item in batch:
            if type(item.get('update_id')) is int:
                offset = max(offset, item['update_id'] + 1)
            if not matches_pilot_callback(item, chat_id, user_id, cover_mid):
                continue
            q = item['callback_query']
            api(token, 'answerCallbackQuery', {
                'callback_query_id': q['id'], 'text': 'Запускаю демонстрацию…', 'show_alert': False
            })
            api(token, 'editMessageReplyMarkup', {
                'chat_id': chat_id, 'message_id': cover_mid, 'reply_markup': {'inline_keyboard': []}
            })
            deliver_royal_sequence(token, chat_id, cover_mid)
            print('ROYAL CHAT PILOT SUCCESS: two TGS sticker stages plus separate reveal/card.')
            return
    raise DemoError('No eligible button press within the 80 second manual test window.')


def main() -> int:
    try:
        run()
        return 0
    except DemoError as error:
        print('ROYAL CHAT PILOT FAILED: ' + str(error), file=sys.stderr)
        return 1
    except Exception:
        print('ROYAL CHAT PILOT FAILED: internal error; details suppressed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
