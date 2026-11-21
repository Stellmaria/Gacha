#!/usr/bin/env python3
"""Manual-only six-outcome Velvet Wheel test in a normal Telegram private chat.

The original user-approved MP4 bytes are never modified. The preferred UX
replaces the initial cover photo with the selected animation *in the same
Telegram message*. Only HTTP 400 on the replacement allows a one-time
sendAnimation fallback; ambiguous network failures always stop.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.telegram_inline_smoke import DemoError, _read_response, api
from scripts.telegram_preflight import ProbeFailure, check_bot
from scripts.telegram_royal_mp4_smoke import send_media as send_approved_cover
from scripts.telegram_widget_smoke import WEIGHTS, choose_rarity

ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR = ROOT / 'wheel'
SOURCE_HASHES = MEDIA_DIR / 'checks/original_sha256.json'
ANIMATION_MANIFEST = MEDIA_DIR / 'animation_manifest.json'
COMMAND = '/wheel6'
CALLBACK = 'gacha:wheel6:spin:v1'
POLL_SECONDS = 90
REVEAL_DELAY_SECONDS = 12.0
OUTCOMES = ('Classic', 'Elite', 'Royal', 'Epic', 'Mythic', 'Eternal')
COVER_CAPTION = ('✦ VELVET · КОЛЕСО СУДЬБЫ ✦\n\n'
                 'Classic 25% · Elite 22% · Royal 19%\n'
                 'Epic 16% · Mythic 11% · Eternal 7%\n\n'
                 'Пробная крутка. Карты и попытки не начисляются.')
SPINNING_CAPTION = ('✦ Колесо вращается…\n'
                    'Velvet Gacha · визуальный тест без начислений')


class MediaReplacementRejected(DemoError):
    """Telegram definitively rejected the edit; a separate send is permitted."""


def caption_for(name: str) -> str:
    if name not in OUTCOMES:
        raise ValueError('Unknown rarity')
    return f'✦ ВЫПАЛО: {name.upper()} ✦\nКолесо судьбы сделало выбор.\n\nДЕМО · Карта не выдана, попытка не списана.'


def choose_outcome(roll: int) -> str:
    return OUTCOMES[choose_rarity(roll)]


def _expected_hashes() -> dict[str, str]:
    return json.loads(SOURCE_HASHES.read_text(encoding='utf-8'))


def verify_original_assets() -> None:
    """Verify all six distinct originals, manifest rotation and fixed cover."""
    hashes = _expected_hashes()
    manifest = json.loads(ANIMATION_MANIFEST.read_text(encoding='utf-8'))
    if len(WEIGHTS) != len(OUTCOMES) or sum(WEIGHTS) != 100:
        raise DemoError('Wheel probability contract mismatch.')
    records = manifest.get('outcomes')
    if not isinstance(records, list) or len(records) != len(OUTCOMES):
        raise DemoError('Wheel asset manifest is incomplete.')
    if tuple(item.get('name') for item in records) != OUTCOMES:
        raise DemoError('Wheel outcome order was modified.')
    names = ['source/master.png'] + [f'videos/{name}.mp4' for name in OUTCOMES]
    for name in names:
        data = (MEDIA_DIR / name).read_bytes()
        sha = hashes.get(name)
        if not isinstance(sha, str) or hashlib.sha256(data).hexdigest() != sha:
            raise DemoError('Approved media checksum does not match.')
        if name.endswith('.png'):
            if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) > 10_000_000:
                raise DemoError('Approved cover is invalid or too large.')
        elif data[4:8] != b'ftyp' or len(data) > 50_000_000:
            raise DemoError('Approved MP4 is invalid or too large.')
    for index, record in enumerate(records):
        if record.get('video') != f'videos/{OUTCOMES[index]}.mp4':
            raise DemoError('MP4 path mismatch.')
        if (record.get('source_center_degrees', -1) +
                record.get('clockwise_rotation_degrees', -1)) % 360 != 270:
            raise DemoError('Wheel stopping geometry mismatch.')


def video_bytes(name: str) -> bytes:
    if name not in OUTCOMES:
        raise DemoError('Unknown wheel result.')
    path = f'videos/{name}.mp4'
    data = (MEDIA_DIR / path).read_bytes()
    if (hashlib.sha256(data).hexdigest() != _expected_hashes().get(path)
            or data[4:8] != b'ftyp' or len(data) > 50_000_000):
        raise DemoError('Approved MP4 changed after verification.')
    return data


def select_owner(updates: list[dict], now: int) -> tuple[int, int]:
    owners: set[tuple[int, int]] = set()
    for update in updates:
        message = update.get('message')
        if not isinstance(message, dict) or message.get('text') != COMMAND:
            continue
        chat, sender = message.get('chat'), message.get('from')
        date = message.get('date')
        if (type(date) is int and 0 <= now - date <= 300 and
            isinstance(chat, dict) and isinstance(sender, dict) and
            chat.get('type') == 'private' and type(chat.get('id')) is int and
            chat['id'] == sender.get('id') and sender.get('is_bot') is False):
            owners.add((chat['id'], sender['id']))
    if len(owners) != 1:
        raise DemoError('Exactly one fresh private /wheel6 sender is required.')
    return next(iter(owners))


def matches_callback(update: dict, chat_id: int, user_id: int, message_id: int) -> bool:
    query = update.get('callback_query')
    if not isinstance(query, dict) or query.get('data') != CALLBACK:
        return False
    sender, message = query.get('from'), query.get('message')
    if not isinstance(sender, dict) or not isinstance(message, dict):
        return False
    chat = message.get('chat')
    return bool(isinstance(query.get('id'), str) and query['id'] and
                isinstance(chat, dict) and chat.get('type') == 'private' and
                chat.get('id') == chat_id == user_id == sender.get('id') and
                message.get('message_id') == message_id)


def _multipart(token: str, method: str, fields: dict[str, object], blob: bytes,
               *, filename: str, upload_field: str = 'wheel_mp4') -> dict:
    """Two whitelisted Bot API methods only; no token/identity in logs."""
    if method not in ('sendAnimation', 'editMessageMedia'):
        raise DemoError('Forbidden wheel multipart method.')
    if blob[4:8] != b'ftyp' or len(blob) > 50_000_000:
        raise DemoError('Refusing invalid or oversized MP4 upload.')
    boundary = 'wheel_' + secrets.token_hex(12)
    parts = []
    for key, value in fields.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="' +
                      key + '"\r\n\r\n' + str(value) + '\r\n').encode('utf-8'))
    parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="' +
                  upload_field + '"; filename="' + filename +
                  '"\r\nContent-Type: video/mp4\r\n\r\n').encode('utf-8'))
    parts.extend((blob, ('\r\n--' + boundary + '--\r\n').encode('ascii')))
    req = Request('https://api.telegram.org/bot' + token + '/' + method,
                  data=b''.join(parts), method='POST',
                  headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    if method == 'editMessageMedia':
        # A *confirmed* HTTP 400 permits an isolated sendAnimation fallback;
        # exceptions with ambiguous transport status must NEVER trigger it.
        try:
            with urlopen(req, timeout=55) as response:
                result = json.load(response)
        except HTTPError as exc:
            if exc.code == 400:
                raise MediaReplacementRejected('Telegram rejected media replacement (HTTP 400).') from None
            raise DemoError(f'Telegram media update failed (HTTP {exc.code}).') from None
        except Exception:
            raise DemoError('Media replacement transport failed; no fallback to avoid duplicates.') from None
        if not isinstance(result, dict) or result.get('ok') is not True:
            raise DemoError('Media replacement response invalid; no fallback.')
        response_value = result.get('result')
    else:
        response_value = _read_response(req, timeout=55)
    if not isinstance(response_value, dict) or type(response_value.get('message_id')) is not int:
        raise DemoError('Telegram did not acknowledge the animation message.')
    if not isinstance(response_value.get('animation'), dict):
        raise DemoError('Telegram did not return an animation in the media message.')
    return response_value


def edit_to_animation(token: str, chat_id: int, cover_mid: int, name: str, data: bytes) -> dict:
    return _multipart(token, 'editMessageMedia', {
        'chat_id': chat_id, 'message_id': cover_mid,
        'media': {'type': 'animation', 'media': 'attach://wheel_mp4',
                  'caption': SPINNING_CAPTION, 'duration': 11, 'width': 720, 'height': 960},
        'reply_markup': {'inline_keyboard': []},
    }, data, filename=f'{name.lower()}-wheel.mp4')


def send_animation_fallback(token: str, chat_id: int, name: str, data: bytes) -> dict:
    return _multipart(token, 'sendAnimation', {
        'chat_id': chat_id, 'caption': SPINNING_CAPTION,
        'duration': 11, 'width': 720, 'height': 960,
    }, data, filename=f'{name.lower()}-wheel.mp4')


def edit_result_caption(token: str, chat_id: int, message_id: int, name: str) -> dict:
    payload = {'chat_id': chat_id, 'message_id': message_id, 'caption': caption_for(name)}
    req = Request('https://api.telegram.org/bot' + token + '/editMessageCaption',
                  method='POST', data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                  headers={'Content-Type': 'application/json'})
    result = _read_response(req)
    if not isinstance(result, dict) or result.get('message_id') != message_id:
        raise DemoError('Telegram did not acknowledge the updated result caption.')
    return result


def deliver_spin(token: str, chat_id: int, cover_mid: int, name: str,
                 *, sleeper=time.sleep) -> tuple[int, bool]:
    """One selected media, delayed caption reveal in same media message."""
    data = video_bytes(name)
    try:
        edited = edit_to_animation(token, chat_id, cover_mid, name, data)
        if edited['message_id'] != cover_mid:
            raise DemoError('Telegram media edit changed the message ID unexpectedly.')
        media_mid, fallback = cover_mid, False
    except MediaReplacementRejected:
        sent = send_animation_fallback(token, chat_id, name, data)
        media_mid, fallback = sent['message_id'], True
    sleeper(REVEAL_DELAY_SECONDS)
    edit_result_caption(token, chat_id, media_mid, name)
    return media_mid, fallback


def run() -> None:
    token = os.environ.get('GACHA_BOT_TOKEN', '')
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]{10,}', token):
        raise DemoError('GACHA_BOT_TOKEN secret is missing or malformed.')
    verify_original_assets()
    try:
        check_bot(token, 'production')
    except ProbeFailure:
        raise DemoError('Telegram getMe preflight failed.') from None
    updates = api(token, 'getUpdates', {
        'timeout': 0, 'limit': 100, 'allowed_updates': ['message', 'callback_query']})
    if not isinstance(updates, list):
        raise DemoError('Invalid Telegram updates response.')
    chat_id, user_id = select_owner(updates, int(time.time()))
    offset = max((u['update_id'] for u in updates if type(u.get('update_id')) is int), default=-1) + 1
    if offset <= 0:
        raise DemoError('No Telegram update offset.')
    api(token, 'getUpdates', {'offset': offset, 'timeout': 0,
                              'allowed_updates': ['message', 'callback_query']})
    cover = (MEDIA_DIR / 'source/master.png').read_bytes()
    cover_response = send_approved_cover(token, chat_id, 'sendPhoto', cover, COVER_CAPTION,
                                         reply_markup={'inline_keyboard': [[{
                                             'text': '✦ Крутить колесо', 'callback_data': CALLBACK
                                         }]]})
    cover_mid = cover_response['message_id']
    print('WHEEL6: approved cover and one button delivered; waiting for authorized click.')
    deadline = time.monotonic() + POLL_SECONDS
    while time.monotonic() < deadline:
        remaining = max(1, int(deadline - time.monotonic()))
        batch = api(token, 'getUpdates', {
            'offset': offset, 'timeout': min(8, remaining),
            'limit': 50, 'allowed_updates': ['message', 'callback_query']})
        if not isinstance(batch, list):
            raise DemoError('Unexpected Telegram callback response.')
        for update in batch:
            if type(update.get('update_id')) is int:
                offset = max(offset, update['update_id'] + 1)
            if not matches_callback(update, chat_id, user_id, cover_mid):
                continue
            api(token, 'answerCallbackQuery', {
                'callback_query_id': update['callback_query']['id'],
                'text': 'Колесо запускается…', 'show_alert': False,
            })
            # Immediate lock before CPU/media I/O. No further callbacks are processed.
            api(token, 'editMessageReplyMarkup', {
                'chat_id': chat_id, 'message_id': cover_mid,
                'reply_markup': {'inline_keyboard': []},
            })
            name = choose_outcome(secrets.randbelow(100))
            _, fallback = deliver_spin(token, chat_id, cover_mid, name)
            print('WHEEL6 SUCCESS: one original outcome delivered; ' +
                  ('separate animation fallback used.' if fallback else 'single-message media edit used.'))
            return
    raise DemoError('Wheel button was not clicked within 90 seconds.')


def main() -> int:
    try:
        run()
        return 0
    except DemoError as exc:
        print('WHEEL6 FAILED: ' + str(exc), file=sys.stderr)
        return 1
    except Exception:
        print('WHEEL6 FAILED: unexpected error; private details suppressed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
